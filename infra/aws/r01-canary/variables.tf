variable "aws_region" {
  type    = string
  default = "eu-central-1"
  validation {
    condition     = var.aws_region == "eu-central-1"
    error_message = "RELEASE.R01/R02 is bounded to eu-central-1."
  }
}

variable "enable_canary" {
  type        = bool
  description = "Fail-closed deployment switch; preparation default is false."
  default     = false
}

variable "release_state" {
  type        = string
  description = "Machine-defined staged release state for the existing bounded runtime."
  default     = "CANARY"
  validation {
    condition     = contains(["CANARY", "LIMITED"], var.release_state)
    error_message = "release_state must be CANARY or LIMITED."
  }
}

variable "desired_count" {
  type        = number
  description = "Bounded ECS task count: CANARY=1, LIMITED=2."
  default     = 1
  validation {
    condition = (
      (var.release_state == "CANARY" && var.desired_count == 1) ||
      (var.release_state == "LIMITED" && var.desired_count == 2)
    )
    error_message = "CANARY requires desired_count=1; LIMITED requires desired_count=2."
  }
}

variable "canary_ipv4_cidrs" {
  type        = list(string)
  description = "Explicitly approved bounded source allowlist retained across CANARY and LIMITED."
  default     = []
  validation {
    condition = !var.enable_canary || (
      length(var.canary_ipv4_cidrs) == 1 &&
      alltrue([for cidr in var.canary_ipv4_cidrs : can(regex("^[0-9.]+/32$", cidr))])
    )
    error_message = "Activation requires exactly one explicitly approved IPv4 /32; R02 LIMITED must not broaden network exposure."
  }
}

variable "image_digest" {
  type        = string
  description = "Immutable ECR digest approved for staged release after live scan and managed-signing verification."
  default     = ""
  validation {
    condition     = !var.enable_canary || can(regex("^sha256:[0-9a-f]{64}$", var.image_digest))
    error_message = "Staged deployment requires an immutable sha256 image digest."
  }
}

variable "certificate_arn" {
  type        = string
  description = "Validated eu-central-1 ACM certificate for canary.ilaios.com."
  default     = ""
  validation {
    condition     = !var.enable_canary || can(regex("^arn:aws:acm:eu-central-1:101180464425:certificate/", var.certificate_arn))
    error_message = "Activation requires the bounded ACM certificate ARN."
  }
}

variable "control_plane_secret_arn" {
  type        = string
  description = "Approved Secrets Manager bearer-token secret ARN."
  default     = ""
  validation {
    condition     = !var.enable_canary || can(regex("^arn:aws:secretsmanager:eu-central-1:101180464425:secret:", var.control_plane_secret_arn))
    error_message = "Activation requires the bounded secret ARN."
  }
}
