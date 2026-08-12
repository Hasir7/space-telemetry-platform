# Space Tech NoSQL Telemetry Platform

Starter repository for the Space Tech NoSQL Cloud DataStore capstone.

## Services
- API: REST endpoints for telemetry, health, alerts and dependencies
- Ingestion: validates and routes telemetry
- Alert: threshold-based alert evaluation
- Telemetry generator: built into the ingestion service

## NoSQL roles
- MongoDB: telemetry documents and alerts
- Redis: live health/cache and alert stream
- Cassandra: historical time-series telemetry
- Neo4j: satellite/component dependency graph

## Local quick start

```bash
cp .env.example .env
docker compose up --build
```

API: http://localhost:8000/docs  
Ingestion: http://localhost:8001/docs  
Alert: http://localhost:8002/docs  
Neo4j: http://localhost:7474

Generate telemetry:

```bash
curl -X POST "http://localhost:8001/generate?satellite_id=SAT-001&count=5"
```

Check:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/satellites/SAT-001/telemetry
curl http://localhost:8000/api/v1/satellites/SAT-001/health
curl http://localhost:8000/api/v1/alerts
```

## Cloud phase

The repository is designed for the next phase: Terraform + Azure Container Registry + Azure Container Apps + Key Vault + Azure Monitor + GitHub Actions OIDC.

Do not commit `.env`, credentials, client secrets, database passwords, or Terraform state.
