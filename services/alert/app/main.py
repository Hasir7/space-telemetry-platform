import os
from datetime import datetime, timezone
from fastapi import FastAPI
from pymongo import MongoClient
import redis

app = FastAPI(title="Telemetry Alert Service", version="0.1.0")
mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = mongo[os.getenv("MONGO_DB", "telemetry")]
r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)

@app.get("/")
def root(): return {"service": "alert", "version": "0.1.0"}

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/evaluate/{satellite_id}")
def evaluate(satellite_id: str):
    h = r.hgetall(f"satellite:{satellite_id}:health")
    if not h: return {"satellite_id": satellite_id, "alerts": []}
    alerts=[]
    temp=float(h.get("temperature_c",0)); battery=float(h.get("battery_pct",100))
    if temp > 80:
        alerts.append({"satellite_id":satellite_id,"type":"HIGH_TEMPERATURE","severity":"critical","value":temp,"threshold":80})
    if battery < 20:
        alerts.append({"satellite_id":satellite_id,"type":"LOW_BATTERY","severity":"warning","value":battery,"threshold":20})
    for a in alerts:
        a["timestamp"]=datetime.now(timezone.utc).isoformat()
        db.alerts.insert_one(dict(a))
        r.xadd("mission-alerts", {"satellite_id":satellite_id,"type":a["type"],"severity":a["severity"]}, maxlen=1000)
    return {"satellite_id": satellite_id, "alerts": alerts}
