variable "project_id" { type = string }
variable "billing_account_id" { type = string }
variable "billing_currency" { type = string }
variable "image_self_link" {
  type = string
  validation {
    condition     = can(regex("^https://www.googleapis.com/compute/v1/projects/ubuntu-os-cloud/global/images/ubuntu-2404-", var.image_self_link))
    error_message = "Pin the observed Ubuntu24.04 image self-link; do not use a moving family."
  }
}
variable "expiry_date" {
  type = string
  validation {
    condition     = can(formatdate("YYYY-MM-DD", "${var.expiry_date}T23:59:00Z"))
    error_message = "Use a reviewed YYYY-MM-DD expiry date."
  }
}
variable "client_cidrs" {
  type = list(string)
  validation {
    condition = length(var.client_cidrs) > 0 && alltrue([
      for cidr in var.client_cidrs : can(cidrnetmask(cidr)) && can(regex("/32$", cidr))
    ])
    error_message = "R01 pilot accepts explicit reviewed IPv4 /32 clients only; no broad Internet ingress."
  }
}
variable "use_relocation_address" {
  type    = bool
  default = false
}
variable "public_lab_hud" {
  description = "Explicit owner opt-in for the R01 full HTTPS lab HUD and HTTP redirect; no login."
  type        = bool
  default     = false
}
