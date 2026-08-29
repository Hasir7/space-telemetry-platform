import os
import random
import ssl
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
import redis
from neo4j import GraphDatabase


app = FastAPI(
    title="Space Telemetry Ingestion Service",
    version="1.0.0",
)


# ============================================================
# Environment
# ============================================================

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://mongodb:27017",
)

MONGO_DB = os.getenv(
    "MONGO_DB",
    "telemetry",
)

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://redis:6379",
)

CASSANDRA_HOST = os.getenv(
    "CASSANDRA_HOST",
    "cassandra",
)

CASSANDRA_PORT = int(os.getenv("CASSANDRA_PORT", "9042"))

CASSANDRA_KEYSPACE = os.getenv(
    "CASSANDRA_KEYSPACE",
    "telemetry",
)

CASSANDRA_USERNAME = os.getenv("CASSANDRA_USERNAME", "")
CASSANDRA_PASSWORD = os.getenv("CASSANDRA_PASSWORD", "")
CASSANDRA_SSL = os.getenv("CASSANDRA_SSL", "false").lower() in {
    "1", "true", "yes", "on"
}

NEO4J_URI = os.getenv(
    "NEO4J_URI",
    "bolt://neo4j:7687",
)

NEO4J_USER = os.getenv(
    "NEO4J_USER",
    "neo4j",
)

NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD",
    "space-telemetry-dev",
)


# ============================================================
# Database clients
# ============================================================

mongo_client = None
mongo_db = None
redis_client = None
cassandra_cluster = None
cassandra_session = None
neo4j_driver = None


# ============================================================
# Cassandra connection
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

def connect_cassandra():
    """
    Connect to the existing Cassandra keyspace.

    The Docker initialization script creates the keyspace
    named 'telemetry', so we use that keyspace here.
    """

    global cassandra_cluster
    global cassandra_session

    last_error = None

    for attempt in range(1, 31):
        try:
            print(
                f"Connecting to Cassandra "
                f"(attempt {attempt}/30)...",
                flush=True,
            )

            cassandra_cluster = create_cassandra_cluster()

            cassandra_session = cassandra_cluster.connect(
                CASSANDRA_KEYSPACE
            )

            print(
                f"Cassandra connected successfully "
                f"using keyspace '{CASSANDRA_KEYSPACE}'.",
                flush=True,
            )

            return

        except Exception as exc:
            last_error = exc

            print(
                f"Cassandra not ready: {exc}",
                flush=True,
            )

            if cassandra_cluster is not None:
                try:
                    cassandra_cluster.shutdown()
                except Exception:
                    pass

                cassandra_cluster = None

            time.sleep(2)

    raise RuntimeError(
        f"Unable to connect to Cassandra after 30 attempts: "
        f"{last_error}"
    )


# ============================================================
# MongoDB connection
# ============================================================

def connect_mongodb():
    global mongo_client
    global mongo_db

    mongo_client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )

    mongo_client.admin.command("ping")

    mongo_db = mongo_client[MONGO_DB]

    print(
        f"MongoDB connected successfully: {MONGO_DB}",
        flush=True,
    )


# ============================================================
# Redis connection
# ============================================================

def connect_redis():
    global redis_client

    redis_client = redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    redis_client.ping()

    print(
        "Redis connected successfully.",
        flush=True,
    )


# ============================================================
# Neo4j connection
# ============================================================

def connect_neo4j():
    global neo4j_driver

    neo4j_driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USER,
            NEO4J_PASSWORD,
        ),
    )

    neo4j_driver.verify_connectivity()

    print(
        "Neo4j connected successfully.",
        flush=True,
    )


# ============================================================
# Application startup
# ============================================================

@app.on_event("startup")
def startup():

    print(
        "Starting Space Telemetry Ingestion Service...",
        flush=True,
    )

    connect_mongodb()
    connect_redis()
    connect_cassandra()
    connect_neo4j()

    print(
        "All database connections established.",
        flush=True,
    )


# ============================================================
# Application shutdown
# ============================================================

@app.on_event("shutdown")
def shutdown():

    global mongo_client
    global cassandra_cluster
    global neo4j_driver

    if mongo_client is not None:
        mongo_client.close()

    if cassandra_cluster is not None:
        cassandra_cluster.shutdown()

    if neo4j_driver is not None:
        neo4j_driver.close()

    print(
        "Database connections closed.",
        flush=True,
    )


# ============================================================
# Generate telemetry packet
# ============================================================

def generate_packet(satellite_id: str):

    now = datetime.now(timezone.utc)

    packet = {
        "telemetry_id": str(uuid.uuid4()),
        "satellite_id": satellite_id,
        "timestamp": now,
        "sensor_id": f"SENSOR-{random.randint(1, 10):03d}",
        "temperature_c": round(
            random.uniform(15.0, 95.0),
            2,
        ),
        "voltage_v": round(
            random.uniform(20.0, 30.0),
            2,
        ),
        "battery_pct": round(
            random.uniform(20.0, 100.0),
            2,
        ),
        "cpu_pct": round(
            random.uniform(10.0, 95.0),
            2,
        ),
        "signal_dbm": round(
            random.uniform(-100.0, -40.0),
            2,
        ),
        "status": "OK",
    }

    # Simple anomaly rule
    if packet["temperature_c"] > 85:
        packet["status"] = "WARNING"

    if packet["battery_pct"] < 25:
        packet["status"] = "WARNING"

    return packet


# ============================================================
# Store telemetry
# ============================================================

def store(packet):

    # --------------------------------------------------------
    # MongoDB
    # --------------------------------------------------------

    mongo_document = dict(packet)

    mongo_db.telemetry.insert_one(
        mongo_document
    )

    # --------------------------------------------------------
    # Redis
    # --------------------------------------------------------

    satellite_id = packet["satellite_id"]

    redis_key = (
        f"satellite:{satellite_id}:health"
    )

    redis_value = {
        "satellite_id": satellite_id,
        "timestamp": packet["timestamp"].isoformat(),
        "temperature_c": packet["temperature_c"],
        "voltage_v": packet["voltage_v"],
        "battery_pct": packet["battery_pct"],
        "cpu_pct": packet["cpu_pct"],
        "signal_dbm": packet["signal_dbm"],
        "status": packet["status"],
    }

    redis_client.hset(
        redis_key,
        mapping=redis_value,
    )

    # Keep the latest health status for 1 hour
    redis_client.expire(
        redis_key,
        3600,
    )

    # --------------------------------------------------------
    # Cassandra
    # --------------------------------------------------------

    query = """
        INSERT INTO telemetry_by_satellite (
            satellite_id,
            timestamp,
            sensor_id,
            temperature_c,
            voltage_v,
            battery_pct,
            cpu_pct,
            signal_dbm,
            status
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
    """

    cassandra_session.execute(
        query,
        (
            packet["satellite_id"],
            packet["timestamp"],
            packet["sensor_id"],
            packet["temperature_c"],
            packet["voltage_v"],
            packet["battery_pct"],
            packet["cpu_pct"],
            packet["signal_dbm"],
            packet["status"],
        ),
    )

    # --------------------------------------------------------
    # Neo4j
    # --------------------------------------------------------

    neo4j_query = """
        MERGE (s:Satellite {
            satellite_id: $satellite_id
        })

        MERGE (sensor:Sensor {
            sensor_id: $sensor_id
        })

        MERGE (s)-[:HAS_SENSOR]->(sensor)

        SET sensor.last_temperature =
            $temperature_c,

            sensor.last_voltage =
            $voltage_v,

            sensor.last_battery =
            $battery_pct,

            sensor.last_cpu =
            $cpu_pct,

            sensor.last_signal =
            $signal_dbm,

            sensor.last_status =
            $status,

            sensor.last_seen =
            $timestamp
    """

    with neo4j_driver.session() as session:
        session.run(
            neo4j_query,
            satellite_id=packet["satellite_id"],
            sensor_id=packet["sensor_id"],
            temperature_c=packet["temperature_c"],
            voltage_v=packet["voltage_v"],
            battery_pct=packet["battery_pct"],
            cpu_pct=packet["cpu_pct"],
            signal_dbm=packet["signal_dbm"],
            status=packet["status"],
            timestamp=packet["timestamp"].isoformat(),
        )

    return packet


# ============================================================
# Health endpoint
# ============================================================

@app.get("/health")
def health():

    checks = {}

    # MongoDB
    try:
        mongo_client.admin.command("ping")
        checks["mongodb"] = "ok"
    except Exception as exc:
        checks["mongodb"] = f"error: {exc}"

    # Redis
    try:
        redis_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    # Cassandra
    try:
        cassandra_session.execute(
            "SELECT now() FROM system.local"
        )
        checks["cassandra"] = "ok"
    except Exception as exc:
        checks["cassandra"] = f"error: {exc}"

    # Neo4j
    try:
        neo4j_driver.verify_connectivity()
        checks["neo4j"] = "ok"
    except Exception as exc:
        checks["neo4j"] = f"error: {exc}"

    overall_status = (
        "ok"
        if all(
            value == "ok"
            for value in checks.values()
        )
        else "degraded"
    )

    return {
        "status": overall_status,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "checks": checks,
    }


# ============================================================
# Generate telemetry
# ============================================================

@app.post("/generate")
def generate(
    satellite_id: str = Query(
        ...,
        description="Satellite identifier",
    ),
    count: int = Query(
        1,
        ge=1,
        le=1000,
        description="Number of telemetry packets",
    ),
):

    if not satellite_id:
        raise HTTPException(
            status_code=400,
            detail="satellite_id is required",
        )

    items = []

    try:

        for _ in range(count):

            packet = generate_packet(
                satellite_id
            )

            stored_packet = store(
                packet
            )

            # Convert datetime for JSON response
            response_packet = dict(
                stored_packet
            )

            response_packet["timestamp"] = (
                response_packet["timestamp"]
                .isoformat()
            )

            items.append(
                response_packet
            )

        return {
            "status": "success",
            "satellite_id": satellite_id,
            "count": len(items),
            "items": items,
        }

    except Exception as exc:

        print(
            f"Telemetry generation failed: {exc}",
            flush=True,
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# Root
# ============================================================

@app.get("/")
def root():

    return {
        "service": "Space Telemetry Ingestion Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "generate": "/generate",
        },
    }
