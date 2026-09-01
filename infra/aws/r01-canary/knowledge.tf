variable "knowledge_enabled" {
  type        = bool
  description = "Enable the governed Knowledge/RAG runtime only for explicitly configured release stages."
  default     = false
}

variable "knowledge_embedding_mode" {
  type        = string
  description = "Exact embedding implementation identity selected for the governed Knowledge runtime."
  default     = "verification_hash_v1"
  validation {
    condition = contains([
      "verification_hash_v1",
      "multilingual_e5_small_qint8_v1"
    ], var.knowledge_embedding_mode)
    error_message = "Knowledge embedding mode must be an implemented, explicitly allowlisted adapter."
  }
}

variable "knowledge_principal_id" {
  type        = string
  description = "Server-side service principal for the bounded Knowledge runtime."
  default     = ""
}

variable "knowledge_tenant_id" {
  type        = string
  description = "Server-side tenant boundary for the bounded Knowledge canary."
  default     = ""
}

variable "knowledge_project_id" {
  type        = string
  description = "Server-side project boundary for the bounded Knowledge canary."
  default     = ""
}

variable "knowledge_classifications" {
  type        = list(string)
  description = "Explicit allowed classifications for the bounded Knowledge canary."
  default     = []
}

variable "knowledge_purposes" {
  type        = list(string)
  description = "Explicit allowed purposes for the bounded Knowledge canary."
  default     = []
}

variable "knowledge_residencies" {
  type        = list(string)
  description = "Explicit allowed residencies for the bounded Knowledge canary."
  default     = []
}

check "knowledge_runtime_configuration" {
  assert {
    condition = !var.knowledge_enabled || (
      length(trimspace(var.knowledge_principal_id)) > 0 &&
      length(trimspace(var.knowledge_tenant_id)) > 0 &&
      length(trimspace(var.knowledge_project_id)) > 0 &&
      length(var.knowledge_classifications) > 0 &&
      length(var.knowledge_purposes) > 0 &&
      length(var.knowledge_residencies) > 0 &&
      alltrue([for value in concat(var.knowledge_classifications, var.knowledge_purposes, var.knowledge_residencies) : length(trimspace(value)) > 0]) &&
      (
        var.release_state != "PRODUCTION" ||
        var.knowledge_embedding_mode == "multilingual_e5_small_qint8_v1"
      )
    )
    error_message = "Knowledge requires complete server-side policy; PRODUCTION additionally requires the pinned multilingual E5 provider."
  }
}

locals {
  knowledge_runtime_environment = var.knowledge_enabled ? concat([
    { name = "ILAIOS_KNOWLEDGE_PRINCIPAL_ID", value = var.knowledge_principal_id },
    { name = "ILAIOS_KNOWLEDGE_TENANT_ID", value = var.knowledge_tenant_id },
    { name = "ILAIOS_KNOWLEDGE_PROJECT_ID", value = var.knowledge_project_id },
    { name = "ILAIOS_KNOWLEDGE_CLASSIFICATIONS", value = join(",", var.knowledge_classifications) },
    { name = "ILAIOS_KNOWLEDGE_PURPOSES", value = join(",", var.knowledge_purposes) },
    { name = "ILAIOS_KNOWLEDGE_RESIDENCIES", value = join(",", var.knowledge_residencies) },
    { name = "ILAIOS_KNOWLEDGE_EMBEDDING_MODE", value = var.knowledge_embedding_mode }
    ], var.knowledge_embedding_mode == "multilingual_e5_small_qint8_v1" ? [
    { name = "ILAIOS_KNOWLEDGE_STARTUP_SELFTEST_REQUIRED", value = "true" }
  ] : []) : []

  runtime_environment = concat([
    { name = "ILAIOS_HOST", value = "0.0.0.0" },
    { name = "ILAIOS_PORT", value = "8080" },
    { name = "ILAIOS_STATE_ROOT", value = "/var/lib/ilaios" },
    { name = "ILAIOS_READY_FILE", value = "/var/lib/ilaios/ready.json" },
    { name = "ILAIOS_RELEASE_STATE", value = var.release_state },
    { name = "ILAIOS_HARD_CAP_MINOR", value = "100" },
    { name = "PYTHONDONTWRITEBYTECODE", value = "1" }
  ], local.knowledge_runtime_environment)
}
