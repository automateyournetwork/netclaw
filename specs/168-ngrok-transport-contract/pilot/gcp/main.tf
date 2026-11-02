terraform {
  required_version = ">= 1.13.2, < 2.0.0"
  # Set path using init -backend-config=path=ABSOLUTE_PRIVATE_PATH.
  backend "local" {}
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "8.9.0"
    }
  }
}

provider "google" {
  project = var.project_id
  # User OAuth credentials require an explicit quota project for budget creation.
  billing_project       = var.project_id
  user_project_override = true
  region  = "northamerica-northeast1"
  zone    = "northamerica-northeast1-a"
}

locals {
  name   = "netclaw-r01-20261101"
  labels = { roadmap = "r01", spec = "168", expires = var.expiry_date }
  note   = "Spec168/R01 transport qualification only; expires ${var.expiry_date}"
}

data "google_project" "selected" { project_id = var.project_id }

resource "google_compute_network" "pilot" {
  name                    = local.name
  description             = local.note
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "pilot" {
  name                     = local.name
  description              = local.note
  network                  = google_compute_network.pilot.id
  ip_cidr_range            = "10.168.0.0/28"
  private_ip_google_access = true
}

resource "google_service_account" "border" {
  account_id   = "netclaw-r01-20261101"
  display_name = "R01 transport-only Border"
  description  = local.note
}

resource "google_secret_manager_secret" "runtime" {
  secret_id = "netclaw-r01-20261101-runtime"
  labels    = local.labels
  replication {
    auto {}
  }
}

# No secret payload in IaC/state. A separately reviewed command adds the new
# pilot-only material after creation. The VM has access to this secret only.
resource "google_secret_manager_secret_iam_member" "runtime" {
  secret_id = google_secret_manager_secret.runtime.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.border.email}"
}

resource "google_compute_address" "pilot" {
  for_each     = toset(["primary", "relocation"])
  name         = "${local.name}-${each.key}"
  description  = local.note
  address_type = "EXTERNAL"
  network_tier = "PREMIUM"
  labels       = local.labels
}

resource "google_compute_firewall" "admin" {
  name                    = "${local.name}-iap"
  description             = local.note
  network                 = google_compute_network.pilot.id
  direction               = "INGRESS"
  source_ranges           = ["35.235.240.0/20"]
  target_service_accounts = [google_service_account.border.email]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

resource "google_compute_firewall" "transport" {
  name                    = "${local.name}-transport"
  description             = local.note
  network                 = google_compute_network.pilot.id
  direction               = "INGRESS"
  source_ranges           = var.client_cidrs
  target_service_accounts = [google_service_account.border.email]
  allow {
    protocol = "tcp"
    ports    = ["42101", "42102"]
  }
}

resource "google_compute_firewall" "public_lab_hud" {
  count                   = var.public_lab_hud ? 1 : 0
  name                    = "${local.name}-public-lab-hud"
  description             = "${local.note}; owner-approved full open HTTPS lab HUD"
  network                 = google_compute_network.pilot.id
  direction               = "INGRESS"
  source_ranges           = ["0.0.0.0/0"]
  target_service_accounts = [google_service_account.border.email]
  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
}

resource "google_compute_instance" "border" {
  name           = local.name
  description    = local.note
  machine_type   = "e2-small"
  labels         = local.labels
  can_ip_forward = false
  boot_disk {
    initialize_params {
      image  = var.image_self_link
      size   = 20
      type   = "pd-standard"
      labels = local.labels
    }
  }
  network_interface {
    subnetwork = google_compute_subnetwork.pilot.id
    network_ip = "10.168.0.2"
    access_config {
      nat_ip       = google_compute_address.pilot[var.use_relocation_address ? "relocation" : "primary"].address
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
    termination_time            = "${var.expiry_date}T00:00:00Z"
  }
  metadata = {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
    serial-port-enable     = "FALSE"
    netclaw-roadmap        = "R01"
    netclaw-expires        = var.expiry_date
    netclaw-runtime-secret = google_secret_manager_secret.runtime.id
  }
  metadata_startup_script = file("${path.module}/prepare-host.sh")
}

resource "google_billing_budget" "pilot" {
  billing_account = var.billing_account_id
  display_name    = "R01 pilot cost alert (expires ${var.expiry_date})"
  budget_filter {
    projects               = ["projects/${data.google_project.selected.number}"]
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
    calendar_period        = "MONTH"
  }
  amount {
    specified_amount {
      currency_code = var.billing_currency
      units         = "50"
    }
  }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.9 }
  threshold_rules { threshold_percent = 1.0 }
  # Default billing-role alert recipients; no Pub/Sub or external channel.
}

output "addresses" { value = { for key, address in google_compute_address.pilot : key => address.address } }
output "instance" { value = google_compute_instance.border.name }
output "runtime_secret" { value = google_secret_manager_secret.runtime.id }
