terraform {
  required_version = ">= 1.13.2, < 2.0.0"
  backend "local" {}
  required_providers { google = { source = "hashicorp/google", version = "8.9.0" } }
}
provider "google" {
  project               = var.project_id
  billing_project       = var.project_id
  user_project_override = true
  region                = "northamerica-northeast1"
  zone                  = var.zone
}
locals {
  name   = "netclaw-r05-${var.run_id}"
  labels = { roadmap = "r05", spec = "176", owner = "netclaw-lab", expires = formatdate("YYYY-MM-DD", var.expires_at) }
  note   = "R05 isolated Ollama member; STOP ${var.expires_at}; remove disk/IP after evidence export"
}
resource "google_compute_network" "r05" {
  name                    = local.name
  description             = local.note
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}
resource "google_compute_subnetwork" "member" {
  name                     = "${local.name}-member"
  description              = local.note
  network                  = google_compute_network.r05.id
  ip_cidr_range            = "10.176.1.0/28"
  private_ip_google_access = false
}
resource "google_service_account" "member" {
  account_id   = "r05-${var.run_id}-member"
  display_name = "R05 Ollama member ${var.run_id}"
  description  = local.note
}
resource "google_compute_address" "member" {
  name         = "${local.name}-member"
  description  = local.note
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"
  labels       = local.labels
}
resource "google_compute_firewall" "iap" {
  name                    = "${local.name}-iap"
  description             = local.note
  network                 = google_compute_network.r05.id
  direction               = "INGRESS"
  source_ranges           = ["35.235.240.0/20"]
  target_service_accounts = [google_service_account.member.email]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
resource "google_compute_firewall" "private_egress" {
  name                    = "${local.name}-deny-private"
  description             = local.note
  network                 = google_compute_network.r05.id
  direction               = "EGRESS"
  priority                = 100
  destination_ranges      = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10"]
  target_service_accounts = [google_service_account.member.email]
  deny { protocol = "all" }
}
resource "google_compute_firewall" "deny_egress" {
  name                    = "${local.name}-deny-egress"
  description             = local.note
  network                 = google_compute_network.r05.id
  direction               = "EGRESS"
  priority                = 65534
  destination_ranges      = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.member.email]
  deny { protocol = "all" }
}
resource "google_compute_firewall" "border_dial" {
  count                   = var.network_activated ? 1 : 0
  name                    = "${local.name}-border-dial"
  description             = local.note
  network                 = google_compute_network.r05.id
  direction               = "EGRESS"
  priority                = 150
  destination_ranges      = ["${var.border_ipv4}/32"]
  target_service_accounts = [google_service_account.member.email]
  allow {
    protocol = "tcp"
    ports    = [tostring(var.border_port)]
  }
}
# This rule belongs to the R05 state; it never edits the existing Border rule.
resource "google_compute_firewall" "border_member" {
  count                   = var.network_activated ? 1 : 0
  name                    = "${local.name}-border-member"
  description             = local.note
  network                 = var.border_network
  direction               = "INGRESS"
  priority                = 1000
  source_ranges           = ["${google_compute_address.member.address}/32"]
  target_service_accounts = [var.border_service_account]
  allow {
    protocol = "tcp"
    ports    = [tostring(var.border_port)]
  }
}
resource "google_compute_instance" "member" {
  name           = "${local.name}-member"
  description    = local.note
  machine_type   = "e2-standard-2"
  labels         = merge(local.labels, { role = "member" })
  can_ip_forward = false
  boot_disk {
    auto_delete = true
    initialize_params {
      image  = var.image_self_link
      size   = 40
      type   = "pd-standard"
      labels = local.labels
    }
  }
  network_interface {
    subnetwork = google_compute_subnetwork.member.id
    network_ip = "10.176.1.2"
    access_config {
      nat_ip       = google_compute_address.member.address
      network_tier = "PREMIUM"
    }
  }
  service_account {
    email  = google_service_account.member.email
    scopes = []
  }
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }
  scheduling {
    provisioning_model          = "STANDARD"
    automatic_restart           = false
    instance_termination_action = "STOP"
    termination_time            = var.expires_at
  }
  metadata = {
    enable-oslogin  = "TRUE", block-project-ssh-keys = "TRUE", serial-port-enable = "FALSE"
    netclaw-roadmap = "R05", netclaw-role = "member", netclaw-expires = var.expires_at
  }
  lifecycle {
    precondition {
      condition     = timecmp(var.expires_at, var.window_started_at) > 0 && timecmp(var.expires_at, "2026-12-01T00:00:00Z") <= 0
      error_message = "R05 must have a finite future window ending no later than the retained pilot lifetime."
    }
    precondition {
      condition     = timecmp(var.expires_at, timestamp()) > 0
      error_message = "Spent or expired plans cannot activate a member."
    }
  }
}
output "member" { value = { instance = google_compute_instance.member.name, address = google_compute_address.member.address, service_account = google_service_account.member.email, expires_at = var.expires_at } }
output "network_activated" { value = var.network_activated }
