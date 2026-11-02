terraform {
  required_version = ">= 1.13.2, < 2.0.0"
  # Always init with an absolute, fresh, owner-private backend path.
  backend "local" {}
  required_providers {
    google = { source = "hashicorp/google", version = "8.9.0" }
  }
}

provider "google" {
  project               = var.project_id
  billing_project       = var.project_id
  user_project_override = true
  region                = "northamerica-northeast1"
  zone                  = "northamerica-northeast1-a"
}

locals {
  name   = "netclaw-r03-${var.run_id}"
  labels = { roadmap = "r03", spec = "172", owner = "netclaw-lab", expires = formatdate("YYYY-MM-DD", var.expires_at) }
  note   = "Isolated unreleased R03 qualification; STOP ${var.expires_at}; separate reviewed teardown required"
}

resource "google_compute_network" "r03" {
  name                    = local.name
  description             = local.note
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "r03" {
  name                     = local.name
  network                  = google_compute_network.r03.id
  ip_cidr_range            = "10.172.0.0/28"
  private_ip_google_access = true
}

resource "google_service_account" "border" {
  account_id   = local.name
  display_name = "R03 control-only Border"
  description  = local.note
}

resource "google_secret_manager_secret" "operator" {
  secret_id = "${local.name}-operator"
  labels    = local.labels
  replication {
    auto {}
  }
}

# No version payload, provider/device key, project-wide IAM or R01 reference.
resource "google_secret_manager_secret_iam_member" "operator" {
  secret_id = google_secret_manager_secret.operator.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.border.email}"
}

resource "google_compute_address" "r03" {
  name         = local.name
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"
  labels       = local.labels
}

resource "google_compute_firewall" "iap" {
  name                    = "${local.name}-iap"
  network                 = google_compute_network.r03.id
  direction               = "INGRESS"
  source_ranges           = ["35.235.240.0/20"]
  target_service_accounts = [google_service_account.border.email]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

# Second exact reviewed plan only, after offline provisioning and host guard proof.
resource "google_compute_firewall" "https" {
  count                   = var.network_activated ? 1 : 0
  name                    = "${local.name}-https"
  network                 = google_compute_network.r03.id
  direction               = "INGRESS"
  source_ranges           = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.border.email]
  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
}

resource "google_compute_firewall" "in2n" {
  count                   = var.network_activated ? 1 : 0
  name                    = "${local.name}-in2n"
  network                 = google_compute_network.r03.id
  direction               = "INGRESS"
  source_ranges           = var.member_cidrs
  target_service_accounts = [google_service_account.border.email]
  allow {
    protocol = "tcp"
    ports    = ["42102"]
  }
}

resource "google_compute_firewall" "private_egress" {
  name                    = "${local.name}-deny-private"
  network                 = google_compute_network.r03.id
  direction               = "EGRESS"
  priority                = 100
  destination_ranges      = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10"]
  target_service_accounts = [google_service_account.border.email]
  deny { protocol = "all" }
}

resource "google_compute_firewall" "web_egress" {
  count                   = var.network_activated ? 1 : 0
  name                    = "${local.name}-web-egress"
  network                 = google_compute_network.r03.id
  direction               = "EGRESS"
  priority                = 200
  destination_ranges      = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.border.email]
  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
}

resource "google_compute_firewall" "deny_egress" {
  name                    = "${local.name}-deny-egress"
  network                 = google_compute_network.r03.id
  direction               = "EGRESS"
  priority                = 65534
  destination_ranges      = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.border.email]
  deny { protocol = "all" }
}

resource "google_compute_instance" "border" {
  name           = local.name
  description    = local.note
  machine_type   = "e2-small"
  labels         = local.labels
  can_ip_forward = false
  boot_disk {
    auto_delete = true
    initialize_params {
      image  = var.image_self_link
      size   = 20
      type   = "pd-standard"
      labels = local.labels
    }
  }
  network_interface {
    subnetwork = google_compute_subnetwork.r03.id
    network_ip = "10.172.0.2"
    access_config {
      nat_ip       = google_compute_address.r03.address
      network_tier = "PREMIUM"
    }
  }
  service_account {
    email  = google_service_account.border.email
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
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
    serial-port-enable     = "FALSE"
    netclaw-roadmap        = "R03"
    netclaw-expires        = var.expires_at
    netclaw-runtime-secret = google_secret_manager_secret.operator.id
  }
  # Deliberately no install/download/startup script. IAP transfers an exact frozen
  # packet while Internet egress and public application ingress remain closed.
  lifecycle {
    precondition {
      condition     = timecmp(var.expires_at, var.window_started_at) > 0 && timecmp(var.expires_at, timeadd(var.window_started_at, "48h")) <= 0
      error_message = "R03 has one fixed qualification window no longer than 48 hours."
    }
    precondition {
      condition     = timecmp(var.expires_at, timestamp()) > 0 && timecmp(var.expires_at, timeadd(timestamp(), "48h")) <= 0
      error_message = "The absolute stop time must still be future and at most 48 hours from apply."
    }
  }
}

output "address" { value = google_compute_address.r03.address }
output "instance" { value = google_compute_instance.border.name }
output "runtime_secret" { value = google_secret_manager_secret.operator.id }
output "service_account" { value = google_service_account.border.email }
output "expires_at" { value = var.expires_at }
output "network_activated" { value = var.network_activated }
