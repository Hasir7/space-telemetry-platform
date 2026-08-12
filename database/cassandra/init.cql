CREATE KEYSPACE IF NOT EXISTS telemetry
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE telemetry;

CREATE TABLE IF NOT EXISTS telemetry_by_satellite (
    satellite_id text,
    timestamp timestamp,
    sensor_id text,
    temperature_c double,
    voltage_v double,
    battery_pct double,
    cpu_pct double,
    signal_dbm double,
    status text,
    PRIMARY KEY ((satellite_id), timestamp, sensor_id)
) WITH CLUSTERING ORDER BY (timestamp DESC);
