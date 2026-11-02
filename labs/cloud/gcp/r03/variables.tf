variable "project_id" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "An explicit existing GCP project ID is required."
  }
}
variable "run_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{8}-[a-z0-9]{4,8}$", var.run_id))
    error_message = "A fresh reviewed YYYYMMDD-suffix identifier is required."
  }
}
variable "image_self_link" {
  type = string
  validation {
    condition     = can(regex("^https://www.googleapis.com/compute/v1/projects/ubuntu-os-cloud/global/images/ubuntu-2404-[a-z0-9-]+$", var.image_self_link))
    error_message = "Pin an observed Ubuntu24.04 image; moving image families are refused."
  }
}
variable "window_started_at" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", var.window_started_at)) && can(formatdate("YYYY-MM-DD", var.window_started_at))
    error_message = "Use the reviewed fixed UTC qualification-window start."
  }
}
variable "expires_at" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", var.expires_at)) && can(formatdate("YYYY-MM-DD", var.expires_at))
    error_message = "Use a fixed UTC stop timestamp, never a sliding duration."
  }
}
variable "member_cidrs" {
  type = list(string)
  validation {
    condition = length(var.member_cidrs) > 0 && length(var.member_cidrs) <= 4 && length(toset(var.member_cidrs)) == length(var.member_cidrs) && alltrue([
      for cidr in var.member_cidrs : can(cidrnetmask(cidr)) && can(regex("/32$", cidr))
    ])
    error_message = "Review one to four unique IPv4 /32 member source addresses."
  }
}
variable "network_activated" {
  type        = bool
  default     = false
  description = "Separate reviewed activation plan, only after host egress guard and frozen services are independently verified."
}
