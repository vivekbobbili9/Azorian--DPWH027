from pydantic import BaseModel
from typing import Optional

class LeakCoords(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class ScanPayload(BaseModel):
    container_id: str
    status: str
    peak_temp: float
    image_path: Optional[str] = None
    leak_coords: Optional[LeakCoords] = None

class TicketPayload(BaseModel):
    container_id: str
    scan_id: int
    severity: str
    notes: Optional[str] = ""

class TicketUpdatePayload(BaseModel):
    status: str