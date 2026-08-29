# MongoDB model

The `telemetry` database contains two collections.

`telemetry` stores complete telemetry packets as flexible documents.

`alerts` stores generated mission alerts.

Example packet:

```json
{
  "satellite_id": "SAT-001",
  "sensor_id": "TEMP-001",
  "timestamp": "2026-08-12T10:00:00Z",
  "temperature_c": 42.1,
  "voltage_v": 28.2,
  "battery_pct": 94,
  "cpu_pct": 37,
  "signal_dbm": -58.2,
  "status": "nominal"
}
```
