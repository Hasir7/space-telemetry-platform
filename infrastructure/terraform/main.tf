resource "azurerm_resource_group" "platform" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_container_registry" "platform" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.platform.name
  location            = azurerm_resource_group.platform.location
  sku                 = "Basic"
  admin_enabled       = false
}

resource "azurerm_log_analytics_workspace" "platform" {
  name                = var.log_analytics_workspace_name
  resource_group_name = azurerm_resource_group.platform.name
  location            = azurerm_resource_group.platform.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "platform" {
  name                       = var.container_apps_environment_name
  resource_group_name        = azurerm_resource_group.platform.name
  location                   = azurerm_resource_group.platform.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.platform.id
}

# Container Apps contain production secret values. Reading them as data sources
# keeps those values out of configuration and avoids replacing live revisions.
data "azurerm_container_app" "services" {
  for_each = var.container_app_names

  name                = each.value
  resource_group_name = azurerm_resource_group.platform.name
}

resource "azurerm_role_assignment" "acr_pull" {
  for_each = data.azurerm_container_app.services

  scope                = azurerm_container_registry.platform.id
  role_definition_name = "AcrPull"
  principal_id         = each.value.identity[0].principal_id
}
