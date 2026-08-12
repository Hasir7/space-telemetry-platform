import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_smoke():
    assert True


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
