import os
import ssl
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import redis
from neo4j import GraphDatabase

from .config import get_cors_origins


# ============================================================
# CONFIGURATION
# ============================================================

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://mongodb:27017"
)

MONGO_DB = os.getenv(
    "MONGO_DB",
    "telemetry"
)

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://redis:6379/0"
)

CASSANDRA_HOST = os.getenv(
    "CASSANDRA_HOST",
    "cassandra"
)

CASSANDRA_PORT = int(
    os.getenv(
        "CASSANDRA_PORT",
        "9042"
    )
)

CASSANDRA_KEYSPACE = os.getenv("CASSANDRA_KEYSPACE", "telemetry")
CASSANDRA_USERNAME = os.getenv("CASSANDRA_USERNAME", "")
CASSANDRA_PASSWORD = os.getenv("CASSANDRA_PASSWORD", "")
CASSANDRA_SSL = os.getenv("CASSANDRA_SSL", "false").lower() in {
    "1", "true", "yes", "on"
}

NEO4J_URI = os.getenv(
    "NEO4J_URI",
    "bolt://neo4j:7687"
)

NEO4J_USER = os.getenv(
    "NEO4J_USER",
    "neo4j"
)

NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD",
    "space-telemetry-dev"
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Space Telemetry API",
    version="0.1.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE CLIENTS
# ============================================================

mongo_client = None
mongo_db = None

redis_client = None

cassandra_cluster = None
cassandra_session = None

neo4j_driver = None


# ============================================================
# STARTUP
# ============================================================

def create_cassandra_cluster(cluster_factory=None, auth_provider_factory=None):
    if cluster_factory is None:
        from cassandra.cluster import Cluster
        cluster_factory = Cluster

    if auth_provider_factory is None:
        from cassandra.auth import PlainTextAuthProvider
        auth_provider_factory = PlainTextAuthProvider

    cluster_options = {"port": CASSANDRA_PORT}

    if bool(CASSANDRA_USERNAME) != bool(CASSANDRA_PASSWORD):
        raise ValueError(
            "CASSANDRA_USERNAME and CASSANDRA_PASSWORD must be set together"
        )

    if CASSANDRA_USERNAME:
        cluster_options["auth_provider"] = auth_provider_factory(
            username=CASSANDRA_USERNAME,
            password=CASSANDRA_PASSWORD,
        )

    if CASSANDRA_SSL:
        cluster_options["ssl_context"] = ssl.create_default_context()

    return cluster_factory([CASSANDRA_HOST], **cluster_options)

@app.on_event("startup")
def startup():
    global mongo_client
    global mongo_db
    global redis_client
    global cassandra_cluster
    global cassandra_session
    global neo4j_driver

    # --------------------------------------------------------
    # MongoDB
    # --------------------------------------------------------

    try:
        mongo_client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=3000
        )

        mongo_client.admin.command("ping")

        mongo_db = mongo_client[MONGO_DB]

        print("MongoDB connected")

    except Exception as exc:
        print(f"MongoDB connection failed: {exc}")
        mongo_client = None
        mongo_db = None

    # --------------------------------------------------------
    # Redis
    # --------------------------------------------------------

    try:
        redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True
        )

        redis_client.ping()

        print("Redis connected")

    except Exception as exc:
        print(f"Redis connection failed: {exc}")
        redis_client = None

    # --------------------------------------------------------
    # Cassandra
    # --------------------------------------------------------

    try:
        cassandra_cluster = create_cassandra_cluster()

        cassandra_session = cassandra_cluster.connect(CASSANDRA_KEYSPACE)

        print("Cassandra connected")

    except Exception as exc:
        print(f"Cassandra connection failed: {exc}")
        cassandra_cluster = None
        cassandra_session = None

    # --------------------------------------------------------
    # Neo4j
    # --------------------------------------------------------

    try:
        neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(
                NEO4J_USER,
                NEO4J_PASSWORD
            )
        )

        neo4j_driver.verify_connectivity()

        print("Neo4j connected")

    except Exception as exc:
        print(f"Neo4j connection failed: {exc}")
        neo4j_driver = None


# ============================================================
# SHUTDOWN
# ============================================================

@app.on_event("shutdown")
def shutdown():
    global mongo_client
    global cassandra_cluster
    global neo4j_driver

    if mongo_client:
        mongo_client.close()

    if cassandra_cluster:
        cassandra_cluster.shutdown()

    if neo4j_driver:
        neo4j_driver.close()


# ============================================================
# HELPERS
# ============================================================

def make_json_safe(value: Any):
    """
    Convert MongoDB / Neo4j / Cassandra values into
    JSON-safe Python values.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            str(k): make_json_safe(v)
            for k, v in value.items()
        }

    if isinstance(value, list):
        return [
            make_json_safe(v)
            for v in value
        ]

    # MongoDB ObjectId
    if value.__class__.__name__ == "ObjectId":
        return str(value)

    # Neo4j Node
    if value.__class__.__name__ == "Node":
        return {
            str(k): make_json_safe(v)
            for k, v in value.items()
        }

    return value


def get_redis_health(satellite_id: str):
    """
    Read current satellite health from Redis.
    """

    if redis_client is None:
        return None

    key = f"satellite:{satellite_id}:health"

    data = redis_client.hgetall(key)

    if not data:
        return None

    numeric_fields = [
        "temperature_c",
        "voltage_v",
        "battery_pct",
        "cpu_pct",
        "signal_dbm",
    ]

    for field in numeric_fields:
        if field in data:
            try:
                data[field] = float(data[field])
            except (TypeError, ValueError):
                pass

    return data


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "service": "api",
        "version": "0.1.0",
        "status": "online"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    checks = {
        "mongodb": "down",
        "redis": "down",
        "cassandra": "down",
        "neo4j": "down",
    }

    # MongoDB
    try:
        if mongo_client:
            mongo_client.admin.command("ping")
            checks["mongodb"] = "ok"
    except Exception:
        checks["mongodb"] = "down"

    # Redis
    try:
        if redis_client:
            redis_client.ping()
            checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "down"

    # Cassandra
    try:
        if cassandra_session:
            cassandra_session.execute(
                "SELECT now() FROM system.local"
            )
            checks["cassandra"] = "ok"
    except Exception:
        checks["cassandra"] = "down"

    # Neo4j
    try:
        if neo4j_driver:
            neo4j_driver.verify_connectivity()
            checks["neo4j"] = "ok"
    except Exception:
        checks["neo4j"] = "down"

    overall = (
        "ok"
        if all(
            value == "ok"
            for value in checks.values()
        )
        else "degraded"
    )

    return {
        "status": overall,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "checks": checks,
    }


# ============================================================
# SATELLITE HEALTH
# ============================================================

@app.get("/api/v1/satellites/{satellite_id}/health")
def get_satellite_health(
    satellite_id: str
):
    health_data = get_redis_health(
        satellite_id
    )

    if health_data is None:
        return {
            "satellite_id": satellite_id,
            "health": None
        }

    return {
        "satellite_id": satellite_id,
        "health": health_data
    }


# ============================================================
# TELEMETRY
# ============================================================

@app.get(
    "/api/v1/satellites/{satellite_id}/telemetry"
)
def get_telemetry(
    satellite_id: str,
    limit: int = 20
):
    limit = max(
        1,
        min(limit, 200)
    )

    # --------------------------------------------------------
    # MongoDB
    # --------------------------------------------------------

    if mongo_db is not None:

        try:
            collection = mongo_db.telemetry

            cursor = (
                collection
                .find(
                    {
                        "satellite_id": satellite_id
                    }
                )
                .sort(
                    "timestamp",
                    -1
                )
                .limit(limit)
            )

            items = []

            for document in cursor:

                document.pop(
                    "_id",
                    None
                )

                items.append(
                    make_json_safe(
                        document
                    )
                )

            if items:
                return {
                    "satellite_id": satellite_id,
                    "count": len(items),
                    "items": items
                }

        except Exception as exc:
            print(
                f"MongoDB telemetry error: {exc}"
            )

    # --------------------------------------------------------
    # Cassandra fallback
    # --------------------------------------------------------

    if cassandra_session is not None:

        try:
            query = """
                SELECT
                    satellite_id,
                    timestamp,
                    sensor_id,
                    temperature_c,
                    voltage_v,
                    battery_pct,
                    cpu_pct,
                    signal_dbm,
                    status
                FROM telemetry_by_satellite
                WHERE satellite_id = %s
                LIMIT %s
            """

            rows = cassandra_session.execute(
                query,
                (
                    satellite_id,
                    limit
                )
            )

            items = []

            for row in rows:

                item = {
                    "satellite_id": row.satellite_id,
                    "timestamp": (
                        row.timestamp.isoformat()
                        if row.timestamp
                        else None
                    ),
                    "sensor_id": row.sensor_id,
                    "temperature_c": row.temperature_c,
                    "voltage_v": row.voltage_v,
                    "battery_pct": row.battery_pct,
                    "cpu_pct": row.cpu_pct,
                    "signal_dbm": row.signal_dbm,
                    "status": row.status,
                }

                items.append(
                    make_json_safe(item)
                )

            return {
                "satellite_id": satellite_id,
                "count": len(items),
                "items": items
            }

        except Exception as exc:
            print(
                f"Cassandra telemetry error: {exc}"
            )

    return {
        "satellite_id": satellite_id,
        "count": 0,
        "items": []
    }


# ============================================================
# ALERTS
# ============================================================

@app.get("/api/v1/alerts")
def get_alerts():
    if mongo_db is None:
        return {
            "count": 0,
            "items": []
        }

    try:

        cursor = (
            mongo_db.alerts
            .find({})
            .sort(
                "timestamp",
                -1
            )
            .limit(50)
        )

        items = []

        for document in cursor:

            document.pop(
                "_id",
                None
            )

            items.append(
                make_json_safe(
                    document
                )
            )

        return {
            "count": len(items),
            "items": items
        }

    except Exception as exc:

        print(
            f"MongoDB alerts error: {exc}"
        )

        return {
            "count": 0,
            "items": []
        }


# ============================================================
# NEO4J DEPENDENCIES
# ============================================================

@app.get(
    "/api/v1/satellites/{satellite_id}/dependencies"
)
def get_dependencies(
    satellite_id: str
):

    if neo4j_driver is None:
        return {
            "satellite_id": satellite_id,
            "dependencies": []
        }

    query = """
        MATCH (
            s:Satellite
            {satellite_id: $satellite_id}
        )
        -[:HAS_SENSOR]->
        (sensor:Sensor)

        RETURN sensor
        ORDER BY sensor.sensor_id
    """

    try:

        with neo4j_driver.session() as session:

            result = session.run(
                query,
                satellite_id=satellite_id
            )

            dependencies = []

            for record in result:

                sensor = record["sensor"]

                dependencies.append({
                    "sensor_id": sensor.get(
                        "sensor_id"
                    ),
                    "last_seen": sensor.get(
                        "last_seen"
                    ),
                    "temperature": sensor.get(
                        "last_temperature"
                    ),
                    "battery": sensor.get(
                        "last_battery"
                    ),
                    "voltage": sensor.get(
                        "last_voltage"
                    ),
                    "cpu": sensor.get(
                        "last_cpu"
                    ),
                    "signal": sensor.get(
                        "last_signal"
                    ),
                    "status": sensor.get(
                        "last_status"
                    ),
                })

        return {
            "satellite_id": satellite_id,
            "dependencies": make_json_safe(
                dependencies
            )
        }

    except Exception as exc:

        print(
            f"Neo4j dependency error: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


# ============================================================
# SATELLITE SUMMARY
# ============================================================

@app.get(
    "/api/v1/satellites/{satellite_id}"
)
def get_satellite(
    satellite_id: str
):

    health_data = get_redis_health(
        satellite_id
    )

    dependencies = []

    if neo4j_driver is not None:

        query = """
            MATCH (
                s:Satellite
                {satellite_id: $satellite_id}
            )
            -[:HAS_SENSOR]->
            (sensor:Sensor)

            RETURN sensor
            ORDER BY sensor.sensor_id
        """

        try:

            with neo4j_driver.session() as session:

                result = session.run(
                    query,
                    satellite_id=satellite_id
                )

                for record in result:

                    sensor = record["sensor"]

                    dependencies.append({
                        "sensor_id": sensor.get(
                            "sensor_id"
                        ),
                        "status": sensor.get(
                            "last_status"
                        ),
                        "temperature": sensor.get(
                            "last_temperature"
                        ),
                        "battery": sensor.get(
                            "last_battery"
                        ),
                    })

        except Exception as exc:
            print(
                f"Neo4j summary error: {exc}"
            )

    return {
        "satellite_id": satellite_id,
        "health": health_data,
        "sensor_count": len(
            dependencies
        ),
        "dependencies": dependencies
    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
