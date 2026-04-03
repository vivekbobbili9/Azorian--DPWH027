from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import ScanPayload, TicketPayload, TicketUpdatePayload
import database as db

app = FastAPI(
    title="Thermal Sentinel API",
    description="DP World Reefer Leak Detection Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    db.init_db()
    print("🚀 Thermal Sentinel API is live!")

@app.post("/scan")
def submit_scan(payload: ScanPayload):
    coords = None
    if payload.leak_coords:
        c = payload.leak_coords
        coords = (c.x1, c.y1, c.x2, c.y2)

    scan_id = db.insert_scan(
        container_id=payload.container_id,
        status=payload.status,
        peak_temp=payload.peak_temp,
        image_path=payload.image_path,
        leak_coords=coords
    )

    if payload.status == "CRITICAL LEAK":
        db.insert_ticket(payload.container_id, scan_id, "HIGH",
                         f"Auto-flagged: Peak {payload.peak_temp:.1f}°C")
    elif payload.status == "MODERATE WARNING":
        db.insert_ticket(payload.container_id, scan_id, "MEDIUM",
                         f"Auto-flagged: Peak {payload.peak_temp:.1f}°C")

    return {"success": True, "scan_id": scan_id, "status": payload.status}

@app.get("/scans")
def get_scans(limit: int = 50):
    return db.get_all_scans(limit)

@app.get("/containers/flagged")
def flagged_containers():
    return db.get_flagged_containers()

@app.post("/ticket")
def create_ticket(payload: TicketPayload):
    db.insert_ticket(payload.container_id, payload.scan_id,
                     payload.severity, payload.notes)
    return {"success": True, "message": "Ticket created"}

@app.get("/tickets/open")
def open_tickets():
    return db.get_open_tickets()

@app.patch("/ticket/{ticket_id}")
def update_ticket(ticket_id: int, payload: TicketUpdatePayload):
    conn = db.get_connection()
    conn.execute(
        "UPDATE maintenance_tickets SET status = ? WHERE id = ?",
        (payload.status, ticket_id)
    )
    conn.commit()
    conn.close()
    return {"success": True, "ticket_id": ticket_id, "new_status": payload.status}

@app.get("/stats/summary")
def summary_stats():
    conn = db.get_connection()
    total   = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
    leaks   = conn.execute(
        "SELECT COUNT(*) FROM scans WHERE status != 'SYSTEM SAFE'"
    ).fetchone()[0]
    flagged = conn.execute(
        "SELECT COUNT(*) FROM container_stats WHERE flagged = 1"
    ).fetchone()[0]
    open_t  = conn.execute(
        "SELECT COUNT(*) FROM maintenance_tickets WHERE status = 'OPEN'"
    ).fetchone()[0]
    conn.close()
    return {
        "total_scans": total,
        "leak_detections": leaks,
        "flagged_containers": flagged,
        "open_tickets": open_t,
        "detection_rate": f"{(leaks/total*100):.1f}%" if total > 0 else "0%"
    }