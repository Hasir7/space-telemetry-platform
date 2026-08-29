variable "subscription_id" {
  description = "Azure subscription containing the existing platform."
  type        = string
}

variable "resource_group_name" {
  description = "Existing resource group to import."
  type        = string
  default     = "space-telemetry-rg"
}

variable "location" {
  description = "Primary Container Apps region."
  type        = string
  default     = "South India"
}

variable "acr_name" {
  description = "Existing Azure Container Registry name."
  type        = string
  default     = "spacetelemetryacr"
}

variable "log_analytics_workspace_name" {
  description = "Existing Log Analytics workspace name."
  type        = string
  default     = "workspace-spacetelemetryrg7F2M"
}

variable "container_apps_environment_name" {
  description = "Existing Container Apps environment name."
  type        = string
  default     = "space-telemetry-env"
}

variable "container_app_names" {
  description = "Existing secret-bearing Container Apps read as data sources."
  type        = set(string)
  default = [
    "space-telemetry-api",
    "space-telemetry-ingestion",
    "space-telemetry-alert",
  ]
}
