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
  name   = "netclaw-r06-${var.run_id}"
  labels = { roadmap = "r06", spec = "177", owner = "netclaw-lab", expires = formatdate("YYYY-MM-DD", var.expires_at) }
  note   = "Isolated unreleased R06 qualification; STOP ${var.expires_at}; teardown removes residual charges"
  roles = {
    a = { subnet = "10.177.0.0/28", address = "10.177.0.2", machine = "e2-standard-2", disk = 40 }
    b = { subnet = "10.177.1.0/28", address = "10.177.1.2", machine = "e2-standard-2", disk = 40 }
  }

}
resource "google_compute_network" "role" {
  for_each                = local.roles
  name                    = "${local.name}-${each.key}"
  description             = local.note
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}
resource "google_compute_subnetwork" "role" {
  for_each                 = local.roles
  name                     = "${local.name}-${each.key}"
  description              = local.note
  network                  = google_compute_network.role[each.key].id
  ip_cidr_range            = each.value.subnet
  private_ip_google_access = true
}
resource "google_service_account" "role" {
  for_each     = local.roles
  account_id   = "r06-${var.run_id}-${each.key}"
  display_name = "R06 ${each.key} ${var.run_id}"
  description  = local.note
}
resource "google_secret_manager_secret" "role" {
  for_each  = var.network_activated ? local.roles : {}
  secret_id = "${local.name}-${each.key}"
  labels    = local.labels
  replication {
    auto {}
  }
}
resource "google_secret_manager_secret_iam_member" "role" {
  for_each  = var.network_activated ? local.roles : {}
  secret_id = google_secret_manager_secret.role[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.role[each.key].email}"
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
  for_each                = local.roles
  name                    = "${local.name}-${each.key}-iap"
  description             = local.note
  network                 = google_compute_network.role[each.key].id
  direction               = "INGRESS"
  source_ranges           = ["35.235.240.0/20"]
  target_service_accounts = [google_service_account.role[each.key].email]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
resource "google_compute_firewall" "private_egress" {
  for_each                = local.roles
  name                    = "${local.name}-${each.key}-deny-private"
  description             = local.note
  network                 = google_compute_network.role[each.key].id
  direction               = "EGRESS"
  priority                = 100
  destination_ranges      = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10"]
  target_service_accounts = [google_service_account.role[each.key].email]
  deny { protocol = "all" }
}
resource "google_compute_firewall" "deny_egress" {
  for_each                = local.roles
  name                    = "${local.name}-${each.key}-deny-egress"
  description             = local.note
  network                 = google_compute_network.role[each.key].id
  direction               = "EGRESS"
  priority                = 65534
  destination_ranges      = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.role[each.key].email]
  deny { protocol = "all" }
}
resource "google_compute_firewall" "https" {
  for_each                = var.network_activated ? local.roles : {}
  name                    = "${local.name}-${each.key}-https"
  description             = local.note
  network                 = google_compute_network.role[each.key].id
  direction               = "INGRESS"
  source_ranges           = [var.local_public_cidr]
  target_service_accounts = [google_service_account.role[each.key].email]
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
}
resource "google_compute_firewall" "acme" {
  for_each                = var.network_activated ? local.roles : {}
  name                    = "${local.name}-${each.key}-acme"
  description             = local.note
  network                 = google_compute_network.role[each.key].id
  direction               = "INGRESS"
  source_ranges           = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.role[each.key].email]
  allow {
    protocol = "tcp"
    ports    = ["80"]
  }
}
resource "google_compute_firewall" "en2n" {
  for_each                = var.network_activated ? local.roles : {}
  name                    = "${local.name}-${each.key}-en2n"
  description             = local.note
  network                 = google_compute_network.role[each.key].id
  direction               = "INGRESS"
  source_ranges           = [var.local_public_cidr, "${google_compute_address.role[each.key == "a" ? "b" : "a"].address}/32"]
  target_service_accounts = [google_service_account.role[each.key].email]
  allow {
    protocol = "tcp"
    ports    = ["42101"]
  }
}
resource "google_compute_firewall" "web_egress" {
  for_each                = var.network_activated ? local.roles : {}
  name                    = "${local.name}-${each.key}-web-egress"
  description             = local.note
  network                 = google_compute_network.role[each.key].id
  direction               = "EGRESS"
  priority                = 200
  destination_ranges      = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.role[each.key].email]
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
}
resource "google_compute_firewall" "peer_dial" {
  for_each                = var.network_activated ? local.roles : {}
  name                    = "${local.name}-${each.key}-peer-dial"
  description             = local.note
  network                 = google_compute_network.role[each.key].id
  direction               = "EGRESS"
  priority                = 150
  destination_ranges      = ["${google_compute_address.role[each.key == "a" ? "b" : "a"].address}/32"]
  target_service_accounts = [google_service_account.role[each.key].email]
  allow {
    protocol = "tcp"
    ports    = ["42101"]
  }
}
# Host policy denies metadata to ordinary gateway applications, including DNS.
# This exact public resolver is separately admitted; all traffic remains metered.
resource "google_compute_firewall" "dns" {
  for_each                = var.network_activated ? local.roles : {}
  name                    = "${local.name}-${each.key}-dns"
  description             = local.note
  network                 = google_compute_network.role[each.key].id
  direction               = "EGRESS"
  priority                = 150
  destination_ranges      = ["8.8.8.8/32"]
  target_service_accounts = [google_service_account.role[each.key].email]
  allow {
    protocol = "udp"
    ports    = ["53"]
  }
  allow {
    protocol = "tcp"
    ports    = ["53"]
  }
}
resource "google_compute_firewall" "mobile" {
  for_each                = var.network_activated ? local.roles : {}
  name                    = "${local.name}-${each.key}-mobile"
  description             = local.note
  network                 = google_compute_network.role[each.key].id
  direction               = "INGRESS"
  source_ranges           = [var.local_public_cidr]
  target_service_accounts = [google_service_account.role[each.key].email]
  allow {
    protocol = "tcp"
    ports    = ["8443"]
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
    netclaw-roadmap = "R06", netclaw-role = each.key, netclaw-expires = var.expires_at
  }
  lifecycle {
    precondition {
      condition     = timecmp(var.expires_at, var.window_started_at) > 0 && timecmp(var.expires_at, timeadd(var.window_started_at, "48h")) <= 0
      error_message = "One fixed R06 qualification window cannot exceed48h."
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
