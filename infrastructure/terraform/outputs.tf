output "resource_group_id" {
  value = azurerm_resource_group.platform.id
}

output "acr_login_server" {
  value = azurerm_container_registry.platform.login_server
}

output "container_apps_environment_id" {
  value = azurerm_container_app_environment.platform.id
}

output "container_app_fqdns" {
  value = {
    for name, app in data.azurerm_container_app.services :
    name => app.ingress[0].fqdn
  }
}
