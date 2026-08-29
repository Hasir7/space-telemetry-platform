# Terraform

This directory models the non-secret Azure foundation in an import-friendly
form. It must not be applied to the existing deployment before imports are
complete and `terraform plan` has been reviewed.

## Modeled resources

- Resource group
- Basic ACR with the admin account disabled
- Log Analytics workspace with 30-day retention
- Consumption Container Apps environment
- Existing API, ingestion, and alert apps as read-only data sources
- Per-app `AcrPull` assignments scoped to ACR

The Container Apps are data sources because their live definitions contain
secret references and revision details. Cosmos DB for MongoDB, Cosmos DB for
Apache Cassandra, Azure Managed Redis, Static Web Apps, and Neo4j Aura are
documented external services and are intentionally not managed here. This
prevents an incomplete first import from resizing or replacing working data.

## Initialize and import

```bash
cp terraform.tfvars.example terraform.tfvars
terraform init

terraform import azurerm_resource_group.platform \
  /subscriptions/<subscription-id>/resourceGroups/space-telemetry-rg

terraform import azurerm_container_registry.platform \
  /subscriptions/<subscription-id>/resourceGroups/space-telemetry-rg/providers/Microsoft.ContainerRegistry/registries/spacetelemetryacr

terraform import azurerm_log_analytics_workspace.platform \
  /subscriptions/<subscription-id>/resourceGroups/space-telemetry-rg/providers/Microsoft.OperationalInsights/workspaces/workspace-spacetelemetryrg7F2M

terraform import azurerm_container_app_environment.platform \
  /subscriptions/<subscription-id>/resourceGroups/space-telemetry-rg/providers/Microsoft.App/managedEnvironments/space-telemetry-env
```

Import each existing role assignment using its assignment resource ID before
applying. Then run `terraform plan` and review every proposed action. This
repository deliberately does not run `terraform apply` against production.

Never put connection strings, access keys, passwords, deployment tokens, or
real production values in `terraform.tfvars`.
