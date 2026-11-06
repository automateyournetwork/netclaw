variable "project_id" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "An explicit existing project is required."
  }
}
variable "project_number" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{6,20}$", var.project_number))
    error_message = "Use the observed numeric project identifier for budget coverage."
  }
}
variable "run_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{8}-[a-z0-9]{4,6}$", var.run_id))
    error_message = "Use a fresh YYYYMMDD-suffix run ID."
  }
}
variable "zone" {
  type    = string
  default = "northamerica-northeast1-b"
  validation {
    condition     = can(regex("^northamerica-northeast1-[abc]$", var.zone))
    error_message = "R06 is scoped to Montréal."
  }
}
variable "image_self_link" {
  type = string
  validation {
    condition     = can(regex("^https://www.googleapis.com/compute/v1/projects/ubuntu-os-cloud/global/images/ubuntu-2404-[a-z0-9-]+$", var.image_self_link))
    error_message = "Pin an observed Ubuntu24.04 AMD64 image."
  }
}
variable "window_started_at" { type = string }
variable "expires_at" { type = string }
variable "network_activated" {
  type    = bool
  default = false
}

variable "local_public_cidr" {
  type = string
  validation {
    condition     = can(cidrnetmask(var.local_public_cidr)) && can(regex("/32$", var.local_public_cidr))
    error_message = "Use the freshly observed local public IPv4 /32; no broad mobile or peer ingress."
  }
}
