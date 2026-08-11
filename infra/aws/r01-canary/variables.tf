variable "aws_region" {
  type    = string
  default = "eu-central-1"
  validation {
    condition     = var.aws_region == "eu-central-1"
    error_message = "RELEASE.R01 is bounded to eu-central-1."
  }
}

variable "enable_canary" {
  type        = bool
  description = "Fail-closed promotion switch; preparation default is false."
  default     = false
}

variable "canary_ipv4_cidrs" {
  type        = list(string)
  description = "Explicitly approved bounded Canary allowlist."
  default     = []
  validation {
    condition     = !var.enable_canary || length(var.canary_ipv4_cidrs) > 0
    error_message = "Canary activation requires a non-empty approved allowlist."
  }
}

variable "image_digest" {
  type        = string
  description = "Immutable ECR digest approved for RELEASE.R01 canary."
  default     = ""
  validation {
    condition = !var.enable_canary || (
      can(regex("^sha256:[0-9a-f]{64}$", var.image_digest)) &&
      var.image_digest == "sha256:0b540cee1e9b7a8f6bf6573eb3a0b15b5e5dd374b693c2738f78c0670121428f"
    )
    error_message = "RELEASE.R01 canary requires the security-scanned and AWS-managed-signed canonical image digest."
  }
}

variable "certificate_arn" {
  type        = string
  description = "Validated eu-central-1 ACM certificate for canary.ilaios.com."
  default     = ""
  validation {
    condition     = !var.enable_canary || can(regex("^arn:aws:acm:eu-central-1:101180464425:certificate/", var.certificate_arn))
    error_message = "Canary activation requires the bounded ACM certificate ARN."
  }
}

variable "control_plane_secret_arn" {
  type        = string
  description = "Approved Secrets Manager bearer-token secret ARN."
  default     = ""
  validation {
    condition     = !var.enable_canary || can(regex("^arn:aws:secretsmanager:eu-central-1:101180464425:secret:", var.control_plane_secret_arn))
    error_message = "Canary activation requires the bounded secret ARN."
  }
}
