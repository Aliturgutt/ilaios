variable "knowledge_enabled" {
  type        = bool
  description = "Enable the bounded Knowledge/RAG runtime only for explicitly configured staged evidence exercises."
  default     = false
}

variable "knowledge_embedding_mode" {
  type        = string
  description = "Embedding implementation identity. Only the bounded verification adapter is currently implemented."
  default     = "verification_hash_v1"
  validation {
    condition     = var.knowledge_embedding_mode == "verification_hash_v1"
    error_message = "Only verification_hash_v1 is implemented; production requires a separately certified provider."
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
      var.release_state != "PRODUCTION" &&
      length(trimspace(var.knowledge_principal_id)) > 0 &&
      length(trimspace(var.knowledge_tenant_id)) > 0 &&
      length(trimspace(var.knowledge_project_id)) > 0 &&
      length(var.knowledge_classifications) > 0 &&
      length(var.knowledge_purposes) > 0 &&
      length(var.knowledge_residencies) > 0 &&
      alltrue([for value in concat(var.knowledge_classifications, var.knowledge_purposes, var.knowledge_residencies) : length(trimspace(value)) > 0])
    )
    error_message = "Knowledge canary requires complete server-side policy and is forbidden in PRODUCTION while only the verification embedding adapter exists."
  }
}

locals {
  knowledge_runtime_environment = var.knowledge_enabled ? [
    { name = "ILAIOS_KNOWLEDGE_PRINCIPAL_ID", value = var.knowledge_principal_id },
    { name = "ILAIOS_KNOWLEDGE_TENANT_ID", value = var.knowledge_tenant_id },
    { name = "ILAIOS_KNOWLEDGE_PROJECT_ID", value = var.knowledge_project_id },
    { name = "ILAIOS_KNOWLEDGE_CLASSIFICATIONS", value = join(",", var.knowledge_classifications) },
    { name = "ILAIOS_KNOWLEDGE_PURPOSES", value = join(",", var.knowledge_purposes) },
    { name = "ILAIOS_KNOWLEDGE_RESIDENCIES", value = join(",", var.knowledge_residencies) },
    { name = "ILAIOS_KNOWLEDGE_EMBEDDING_MODE", value = var.knowledge_embedding_mode }
  ] : []

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
