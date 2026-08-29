import sys
from collections import namedtuple
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_smoke():
    assert True


def test_canonical_mongo_config_and_collections():
    from services.alert.app import main as alert_main
    from services.api.app import main as api_main
    from services.ingestion.app import main as ingestion_main

    assert api_main.MONGO_DB == "telemetry"
    assert ingestion_main.MONGO_DB == "telemetry"
    assert alert_main.db.name == "telemetry"

    schema = (PROJECT_ROOT / "database/mongodb/schema.md").read_text()
    assert "`telemetry` stores" in schema
    assert "`alerts` stores" in schema
    assert "telemetry_packets" not in schema


def test_cassandra_table_query_and_returned_fields_are_consistent(monkeypatch):
    from services.api.app import main as api_main

    init_cql = (PROJECT_ROOT / "database/cassandra/init.cql").read_text()
    ingestion_source = (
        PROJECT_ROOT / "services/ingestion/app/main.py"
    ).read_text()
    assert "CREATE TABLE IF NOT EXISTS telemetry_by_satellite" in init_cql
    assert "INSERT INTO telemetry_by_satellite" in ingestion_source

    columns = [
        "satellite_id", "timestamp", "sensor_id", "temperature_c",
        "voltage_v", "battery_pct", "cpu_pct", "signal_dbm", "status",
    ]
    Row = namedtuple("Row", columns)
    row = Row("SAT-1", None, "SENSOR-1", 20.0, 28.0, 90.0, 10.0, -50.0, "OK")

    class FakeSession:
        def execute(self, query, parameters):
            assert "FROM telemetry_by_satellite" in query
            assert "WHERE satellite_id = %s" in query
            assert "LIMIT %s" in query
            assert parameters == ("SAT-1", 7)
            return [row]

    monkeypatch.setattr(api_main, "mongo_db", None)
    monkeypatch.setattr(api_main, "cassandra_session", FakeSession())
    result = api_main.get_telemetry("SAT-1", 7)
    assert list(result["items"][0]) == columns


@pytest.mark.parametrize(
    "module_name",
    ["services.api.app.main", "services.ingestion.app.main"],
)
def test_cassandra_tls_and_auth_configuration(monkeypatch, module_name):
    module = __import__(module_name, fromlist=["main"])
    captured = {}

    class FakeCluster:
        def __init__(self, hosts, **options):
            captured.update(hosts=hosts, options=options)

    monkeypatch.setattr(module, "CASSANDRA_HOST", "db.example.com")
    monkeypatch.setattr(module, "CASSANDRA_PORT", 9142)
    monkeypatch.setattr(module, "CASSANDRA_USERNAME", "app-user")
    monkeypatch.setattr(module, "CASSANDRA_PASSWORD", "secret")
    monkeypatch.setattr(module, "CASSANDRA_SSL", True)
    module.create_cassandra_cluster(
        cluster_factory=FakeCluster,
        auth_provider_factory=lambda **credentials: credentials,
    )

    assert captured["hosts"] == ["db.example.com"]
    assert captured["options"]["port"] == 9142
    assert captured["options"]["protocol_version"] == 4
    assert captured["options"]["connect_timeout"] == 20
    assert captured["options"]["auth_provider"] is not None
    assert isinstance(captured["options"]["ssl_context"], object)
    assert captured["options"]["ssl_options"] == {
        "server_hostname": "db.example.com"
    }


def test_cassandra_local_defaults_do_not_require_tls_or_auth(monkeypatch):
    from services.api.app import main as api_main

    captured = {}

    def fake_cluster(hosts, **options):
        captured.update(hosts=hosts, options=options)
        return object()

    monkeypatch.setattr(api_main, "CASSANDRA_USERNAME", "")
    monkeypatch.setattr(api_main, "CASSANDRA_PASSWORD", "")
    monkeypatch.setattr(api_main, "CASSANDRA_SSL", False)
    api_main.create_cassandra_cluster(
        cluster_factory=fake_cluster,
        auth_provider_factory=lambda **credentials: credentials,
    )
    assert "auth_provider" not in captured["options"]
    assert "ssl_context" not in captured["options"]
    assert "ssl_options" not in captured["options"]
    assert captured["options"]["protocol_version"] == 4
    assert captured["options"]["connect_timeout"] == 20


def test_alert_low_battery_uses_requested_satellite_id(monkeypatch):
    from services.alert.app import main as alert_main

    stored_alerts = []
    published_alerts = []

    class FakeAlertsCollection:
        def insert_one(self, alert):
            stored_alerts.append(alert)

    class FakeDatabase:
        alerts = FakeAlertsCollection()

    class FakeRedis:
        def hgetall(self, key):
            assert key == "satellite:SAT-LOW:health"
            return {"temperature_c": "25", "battery_pct": "10"}

        def xadd(self, stream, fields, maxlen):
            published_alerts.append((stream, fields, maxlen))

    monkeypatch.setattr(alert_main, "db", FakeDatabase())
    monkeypatch.setattr(alert_main, "r", FakeRedis())

    result = alert_main.evaluate("SAT-LOW")

    assert result["satellite_id"] == "SAT-LOW"
    assert result["alerts"][0]["satellite_id"] == "SAT-LOW"
    assert result["alerts"][0]["type"] == "LOW_BATTERY"
    assert stored_alerts[0]["satellite_id"] == "SAT-LOW"
    assert published_alerts[0][1]["satellite_id"] == "SAT-LOW"


def test_alert_health_checks_mongodb_and_redis(monkeypatch):
    from services.alert.app import main as alert_main

    class FakeAdmin:
        @staticmethod
        def command(command):
            assert command == "ping"

    class FakeMongo:
        admin = FakeAdmin()

    class FakeRedis:
        @staticmethod
        def ping():
            return True

    monkeypatch.setattr(alert_main, "mongo", FakeMongo())
    monkeypatch.setattr(alert_main, "r", FakeRedis())

    assert alert_main.health() == {
        "status": "ok",
        "checks": {"mongodb": "ok", "redis": "ok"},
    }


def test_api_cors_origins_are_configurable_with_local_defaults(monkeypatch):
    from services.api.app.config import get_cors_origins

    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert get_cors_origins() == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://dashboard.example.com, https://admin.example.com ",
    )
    assert get_cors_origins() == [
        "https://dashboard.example.com",
        "https://admin.example.com",
    ]
