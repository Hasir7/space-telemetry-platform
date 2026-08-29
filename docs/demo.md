# Production demo checklist

1. Open <https://red-pebble-048b99600.7.azurestaticapps.net>.
2. Check API and ingestion `/health` endpoints.
3. Generate `SAT-001` telemetry through `POST /generate` on ingestion.
4. Refresh the dashboard and show current health plus telemetry history.
5. Call the dependency endpoint and explain the Neo4j
   `Satellite-HAS_SENSOR-Sensor` relationship.
6. Set a demo health value above 80°C and evaluate the critical
   `HIGH_TEMPERATURE` alert.
7. Set a demo battery value below 20% and verify `LOW_BATTERY`.
8. Show `/api/v1/alerts` and explain the bounded Redis `mission-alerts` stream.
9. Show Healthy Container App revisions and Log Analytics logs.
10. Explain cost controls: Mongo free tier, Cassandra serverless, Redis B0,
    AuraDB Free, Static Web Apps Free, and scale-to-zero Container Apps.

Do not display Azure keys, Container App secret values, Aura credentials, or
downloaded credential files during the demo.
