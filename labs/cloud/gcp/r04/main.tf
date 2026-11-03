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
  name   = "netclaw-r04-${var.run_id}"
  labels = { roadmap = "r04", spec = "173", owner = "netclaw-lab", expires = formatdate("YYYY-MM-DD", var.expires_at) }
  note   = "Isolated unreleased R04 qualification; STOP ${var.expires_at}; teardown removes residual charges"
  roles = {
    border = { subnet = "10.173.0.0/28", address = "10.173.0.2", machine = "e2-small", disk = 20 }
    member = { subnet = "10.173.1.0/28", address = "10.173.1.2", machine = "e2-standard-2", disk = 40 }
  }
  secrets = { operator = "border", netbox = "member", guard = "member" }
}
resource "google_compute_network" "r04" {
  name                    = local.name
  description             = local.note
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}
resource "google_compute_subnetwork" "role" {
  for_each                 = local.roles
  name                     = "${local.name}-${each.key}"
  description              = local.note
  network                  = google_compute_network.r04.id
  ip_cidr_range            = each.value.subnet
  private_ip_google_access = true
}
resource "google_service_account" "role" {
  for_each     = local.roles
  account_id   = "r04-${var.run_id}-${each.key}"
  display_name = "R04 ${each.key} ${var.run_id}"
  description  = local.note
}
resource "google_secret_manager_secret" "role" {
  for_each  = local.secrets
  secret_id = "${local.name}-${each.key}"
  labels    = local.labels
  replication {
    auto {}
  }
}
resource "google_secret_manager_secret_iam_member" "role" {
  for_each  = local.secrets
  secret_id = google_secret_manager_secret.role[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.role[each.value].email}"
}
resource "google_compute_address" "role" {
  for_each     = local.roles
  name         = "${local.name}-${each.key}"
  description  = local.note
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"
  labels       = local.labels
}
resource "google_compute_firewall" "iap" {
  name                    = "${local.name}-iap"
  description             = local.note
  network                 = google_compute_network.r04.id
  direction               = "INGRESS"
  source_ranges           = ["35.235.240.0/20"]
  target_service_accounts = [for sa in google_service_account.role : sa.email]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
resource "google_compute_firewall" "private_egress" {
  name                    = "${local.name}-deny-private"
  description             = local.note
  network                 = google_compute_network.r04.id
  direction               = "EGRESS"
  priority                = 100
  destination_ranges      = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10"]
  target_service_accounts = [for sa in google_service_account.role : sa.email]
  deny { protocol = "all" }
}
resource "google_compute_firewall" "deny_egress" {
  name                    = "${local.name}-deny-egress"
  description             = local.note
  network                 = google_compute_network.r04.id
  direction               = "EGRESS"
  priority                = 65534
  destination_ranges      = ["0.0.0.0/0"]
  target_service_accounts = [for sa in google_service_account.role : sa.email]
  deny { protocol = "all" }
}
resource "google_compute_firewall" "https" {
  count                   = var.network_activated ? 1 : 0
  name                    = "${local.name}-https"
  description             = local.note
  network                 = google_compute_network.r04.id
  direction               = "INGRESS"
  source_ranges           = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.role["border"].email]
  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
}
resource "google_compute_firewall" "in2n" {
  count                   = var.network_activated ? 1 : 0
  name                    = "${local.name}-in2n"
  description             = local.note
  network                 = google_compute_network.r04.id
  direction               = "INGRESS"
  source_ranges           = ["${google_compute_address.role["member"].address}/32"]
  target_service_accounts = [google_service_account.role["border"].email]
  allow {
    protocol = "tcp"
    ports    = ["42102"]
  }
}
resource "google_compute_firewall" "web_egress" {
  for_each                = var.network_activated ? local.roles : {}
  name                    = "${local.name}-${each.key}-web-egress"
  description             = local.note
  network                 = google_compute_network.r04.id
  direction               = "EGRESS"
  priority                = 200
  destination_ranges      = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.role[each.key].email]
  allow {
    protocol = "tcp"
    ports    = each.key == "border" ? ["80", "443"] : ["443"]
  }
}
resource "google_compute_firewall" "member_dial" {
  count                   = var.network_activated ? 1 : 0
  name                    = "${local.name}-member-dial"
  description             = local.note
  network                 = google_compute_network.r04.id
  direction               = "EGRESS"
  priority                = 150
  destination_ranges      = ["${google_compute_address.role["border"].address}/32"]
  target_service_accounts = [google_service_account.role["member"].email]
  allow {
    protocol = "tcp"
    ports    = ["42102"]
  }
}
# Metadata is denied to member applications/containers, including its DNS IP.
# This exact public resolver is separately admitted; all traffic remains metered.
resource "google_compute_firewall" "member_dns" {
  count                   = var.network_activated ? 1 : 0
  name                    = "${local.name}-member-dns"
  description             = local.note
  network                 = google_compute_network.r04.id
  direction               = "EGRESS"
  priority                = 150
  destination_ranges      = ["8.8.8.8/32"]
  target_service_accounts = [google_service_account.role["member"].email]
  allow {
    protocol = "udp"
    ports    = ["53"]
  }
  allow {
    protocol = "tcp"
    ports    = ["53"]
  }
}
resource "google_compute_instance" "role" {
  for_each       = local.roles
  name           = "${local.name}-${each.key}"
  description    = local.note
  machine_type   = each.value.machine
  labels         = merge(local.labels, { role = each.key })
  can_ip_forward = false
  boot_disk {
    auto_delete = true
    initialize_params {
      image  = var.image_self_link
      size   = each.value.disk
      type   = "pd-standard"
      labels = local.labels
    }
  }
  network_interface {
    subnetwork = google_compute_subnetwork.role[each.key].id
    network_ip = each.value.address
    access_config {
      nat_ip       = google_compute_address.role[each.key].address
      network_tier = "PREMIUM"
    }
  }
  service_account {
    email  = google_service_account.role[each.key].email
    scopes = ["cloud-platform"]
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
    netclaw-roadmap = "R04", netclaw-role = each.key, netclaw-expires = var.expires_at
  }
  lifecycle {
    precondition {
      condition     = timecmp(var.expires_at, var.window_started_at) > 0 && timecmp(var.expires_at, timeadd(var.window_started_at, "48h")) <= 0
      error_message = "One fixed R04 qualification window cannot exceed48h."
    }
    precondition {
      condition     = timecmp(var.expires_at, timestamp()) > 0 && timecmp(var.expires_at, timeadd(timestamp(), "48h")) <= 0
      error_message = "The absolute stop time must remain future and within48h."
    }
  }
}
output "roles" { value = { for role, vm in google_compute_instance.role : role => { instance = vm.name, address = google_compute_address.role[role].address, service_account = google_service_account.role[role].email } } }
output "secrets" { value = { for name, secret in google_secret_manager_secret.role : name => secret.id } }
output "project_number" { value = var.project_number }
output "expires_at" { value = var.expires_at }
output "network_activated" { value = var.network_activated }
