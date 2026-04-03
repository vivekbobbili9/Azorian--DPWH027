"""
Thermal Sentinel — FastAPI Backend
Run: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.responses import Response, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import sqlite3
import json
import asyncio
import uuid
import random

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
AMBIENT_TEMP       = 28.0
CRITICAL_THRESHOLD = 60.0
MODERATE_THRESHOLD = 40.0
DELTA_T_ALERT      = 15.0
DB_PATH            = "thermal_sentinel.db"

# In-memory frame + command store
_latest_frame: bytes = b""
_pending_cmd:  str   = ""


# ─────────────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Thermal Sentinel API",
    description="DP World Reefer Leak Detection System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE — thread-safe connection every time
# ─────────────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id               TEXT PRIMARY KEY,
            container_id     TEXT NOT NULL,
            thermal_max_temp REAL NOT NULL,
            ambient_temp     REAL NOT NULL DEFAULT 28.0,
            delta_t          REAL,
            confidence_score REAL NOT NULL,
            status           TEXT NOT NULL,
            alert_triggered  INTEGER DEFAULT 0,
            operator_note    TEXT,
            operator_status  TEXT DEFAULT 'PENDING',
            timestamp        TEXT NOT NULL,
            gate_id          TEXT DEFAULT 'GATE-1',
            image_path       TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialized!")


init_db()

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
class ScanInput(BaseModel):
    container_id:     str
    thermal_max_temp: float
    confidence_score: float
    timestamp:        Optional[str] = None
    gate_id:          Optional[str] = "GATE-1"
    image_path:       Optional[str] = None
    ambient_temp:     Optional[float] = AMBIENT_TEMP


class ScanResponse(BaseModel):
    id:               str
    container_id:     str
    thermal_max_temp: float
    ambient_temp:     float
    delta_t:          float
    confidence_score: float
    status:           str
    alert_triggered:  bool
    operator_status:  str
    timestamp:        str
    gate_id:          str
    image_path:       Optional[str]
    operator_note:    Optional[str]


class OperatorUpdate(BaseModel):
    operator_status: str
    operator_note:   Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKET
# ─────────────────────────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, payload: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)


manager = ConnectionManager()

# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS LOGIC
# ─────────────────────────────────────────────────────────────────────────────
def evaluate_scan(thermal_max_temp: float, ambient: float) -> dict:
    delta_t = round(thermal_max_temp - ambient, 2)
    alert   = delta_t >= DELTA_T_ALERT

    if thermal_max_temp >= CRITICAL_THRESHOLD:
        status = "CRITICAL"
    elif thermal_max_temp >= MODERATE_THRESHOLD:
        status = "MODERATE"
    else:
        status = "SAFE"

    return {"delta_t": delta_t, "status": status, "alert_triggered": alert}

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=FileResponse, tags=["Health"])
def root():
    """Serve the dashboard UI."""
    import os
    # Try project root first, then one level up from src/
    for path in ["dashboard.html", "../dashboard.html"]:
        if os.path.exists(path):
            return FileResponse(path, media_type="text/html")
    return {"status": "Thermal Sentinel API Online", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── POST /scan ────────────────────────────────────────────────────────────────
@app.post("/scan", response_model=ScanResponse, status_code=201, tags=["Ingestion"])
async def ingest_scan(payload: ScanInput):
    scan_id   = str(uuid.uuid4())
    timestamp = payload.timestamp or datetime.utcnow().isoformat()
    decision  = evaluate_scan(payload.thermal_max_temp, payload.ambient_temp)

    row = {
        "id":               scan_id,
        "container_id":     payload.container_id.strip().upper(),
        "thermal_max_temp": payload.thermal_max_temp,
        "ambient_temp":     payload.ambient_temp,
        "delta_t":          decision["delta_t"],
        "confidence_score": payload.confidence_score,
        "status":           decision["status"],
        "alert_triggered":  int(decision["alert_triggered"]),
        "operator_note":    None,
        "operator_status":  "PENDING",
        "timestamp":        timestamp,
        "gate_id":          payload.gate_id or "GATE-1",
        "image_path":       payload.image_path,
    }

    db = get_db()
    db.execute("""
        INSERT INTO scans
            (id, container_id, thermal_max_temp, ambient_temp, delta_t,
             confidence_score, status, alert_triggered, operator_note,
             operator_status, timestamp, gate_id, image_path)
        VALUES
            (:id, :container_id, :thermal_max_temp, :ambient_temp, :delta_t,
             :confidence_score, :status, :alert_triggered, :operator_note,
             :operator_status, :timestamp, :gate_id, :image_path)
    """, row)
    db.commit()
    db.close()

    if decision["alert_triggered"]:
        await manager.broadcast({
            "event":            "LEAK_ALERT",
            "scan_id":          scan_id,
            "container_id":     row["container_id"],
            "status":           decision["status"],
            "thermal_max_temp": payload.thermal_max_temp,
            "delta_t":          decision["delta_t"],
            "gate_id":          row["gate_id"],
            "timestamp":        timestamp,
        })

    return ScanResponse(**{**row, "alert_triggered": bool(row["alert_triggered"])})


# ── GET /scans ────────────────────────────────────────────────────────────────
@app.get("/scans", response_model=List[ScanResponse], tags=["Database"])
def get_scans(
    hours:   int           = Query(24),
    status:  Optional[str] = Query(None),
    gate_id: Optional[str] = Query(None),
    limit:   int           = Query(100),
):
    since  = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    query  = "SELECT * FROM scans WHERE timestamp >= ?"
    params: list = [since]

    if status:
        query += " AND status = ?"
        params.append(status.upper())
    if gate_id:
        query += " AND gate_id = ?"
        params.append(gate_id)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    db   = get_db()
    rows = db.execute(query, params).fetchall()
    db.close()
    return [ScanResponse(**{**dict(r), "alert_triggered": bool(r["alert_triggered"])}) for r in rows]


# ── GET /scans/{id} ───────────────────────────────────────────────────────────
@app.get("/scans/{scan_id}", response_model=ScanResponse, tags=["Database"])
def get_scan(scan_id: str):
    db  = get_db()
    row = db.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse(**{**dict(row), "alert_triggered": bool(row["alert_triggered"])})


# ── PATCH /scans/{id}/review ──────────────────────────────────────────────────
@app.patch("/scans/{scan_id}/review", response_model=ScanResponse, tags=["Database"])
def update_scan(scan_id: str, update: OperatorUpdate):
    db  = get_db()
    row = db.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="Scan not found")

    db.execute(
        "UPDATE scans SET operator_status = ?, operator_note = ? WHERE id = ?",
        (update.operator_status.upper(), update.operator_note, scan_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    db.close()
    return ScanResponse(**{**dict(updated), "alert_triggered": bool(updated["alert_triggered"])})


# ── GET /stats ────────────────────────────────────────────────────────────────
@app.get("/stats", tags=["Analytics"])
def get_stats(hours: int = Query(24)):
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    db    = get_db()
    rows  = db.execute("SELECT * FROM scans WHERE timestamp >= ?", (since,)).fetchall()
    db.close()

    total    = len(rows)
    critical = sum(1 for r in rows if r["status"] == "CRITICAL")
    moderate = sum(1 for r in rows if r["status"] == "MODERATE")
    safe     = sum(1 for r in rows if r["status"] == "SAFE")
    alerted  = sum(1 for r in rows if r["alert_triggered"])
    avg_dt   = round(sum(r["delta_t"] for r in rows) / total, 2) if total else 0
    hottest  = max(rows, key=lambda r: r["thermal_max_temp"], default=None)

    return {
        "window_hours":      hours,
        "total_scans":       total,
        "critical":          critical,
        "moderate":          moderate,
        "safe":              safe,
        "alerts_fired":      alerted,
        "avg_delta_t":       avg_dt,
        "hottest_container": {
            "container_id":     hottest["container_id"],
            "thermal_max_temp": hottest["thermal_max_temp"],
            "timestamp":        hottest["timestamp"],
        } if hottest else None,
    }


# ── POST /simulate ────────────────────────────────────────────────────────────
@app.post("/simulate", status_code=201, tags=["Demo"])
async def simulate_scan():
    prefixes  = ["TRHU", "MSCU", "HLXU", "GESU", "TEMU"]
    fake_temp = round(random.uniform(22.0, 85.0), 1)
    fake_conf = round(random.uniform(0.55, 0.99), 2)
    fake_cont = f"{random.choice(prefixes)}{random.randint(1000000, 9999999)}"
    fake_gate = random.choice(["GATE-1", "GATE-2", "GATE-3"])

    payload = ScanInput(
        container_id     = fake_cont,
        thermal_max_temp = fake_temp,
        confidence_score = fake_conf,
        gate_id          = fake_gate,
    )
    return await ingest_scan(payload)


# ── WEBSOCKET ─────────────────────────────────────────────────────────────────
@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"event": "PING"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── LIVE FRAME STREAM ─────────────────────────────────────────────────────────
@app.post("/frame", tags=["Stream"])
async def push_frame(request: Request):
    global _latest_frame
    _latest_frame = await request.body()
    # Broadcast to WebSocket clients so dashboard refreshes immediately
    await manager.broadcast({"event": "NEW_FRAME"})
    return {"ok": True}

@app.get("/frame", tags=["Stream"])
def get_frame():
    if not _latest_frame:
        raise HTTPException(status_code=404, detail="No frame yet")
    return Response(content=_latest_frame, media_type="image/jpeg")


# ── DETECTOR COMMAND CONTROL ──────────────────────────────────────────────────
@app.post("/command", tags=["Control"])
async def post_command(body: dict):
    global _pending_cmd
    _pending_cmd = body.get("action", "")
    return {"ok": True, "action": _pending_cmd}

@app.get("/command", tags=["Control"])
def get_command():
    global _pending_cmd
    cmd, _pending_cmd = _pending_cmd, ""   # read-and-clear
    return {"action": cmd}