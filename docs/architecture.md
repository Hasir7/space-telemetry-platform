# Architecture

Telemetry enters the ingestion service, is validated, then routed according to access pattern:

- MongoDB: flexible telemetry documents/audit history
- Redis: current health state, cache and alert stream
- Cassandra: high-volume historical time-series
- Neo4j: dependency/fault relationships

The API provides read endpoints and the alert service evaluates thresholds.

Future Azure phase:
Azure Container Registry, Container Apps, Key Vault, Azure Monitor/Application Insights, Terraform and GitHub Actions OIDC.
