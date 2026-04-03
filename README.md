# 🌡️ Azorian · Thermal Sentinel

> **AI-powered thermal leak detection system for reefer (refrigerated) shipping containers** — built for DP World Hackathon 2027 (DPWH027)

A real-time port gate intelligence system that scans containers using thermal imaging, detects refrigerant leaks using YOLOv8 + Gaussian anomaly injection, logs every scan to a database, and streams live results to a web dashboard.

---

## 🖥️ Live Dashboard

The dashboard is served directly by the API — once deployed, open your Render URL and the full UI is there.

![Dashboard Preview](docs/dashboard_preview.png)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      LOCAL (Port / Yard)                    │
│                                                             │
│  Thermal Datasets ──► detector.py ──► OpenCV Window         │
│       (images)            │               (live view)       │
│                           │                                 │
│                    POST /scan  +  POST /frame               │
└───────────────────────────┼─────────────────────────────────┘
                            │  HTTP
┌───────────────────────────▼─────────────────────────────────┐
│                    CLOUD (Render)                           │
│                                                             │
│   FastAPI (main.py)                                         │
│   ├── POST /scan       — ingest detection result            │
│   ├── GET  /scans      — query scan history                 │
│   ├── GET  /stats      — KPI summary                        │
│   ├── POST /frame      — push live JPEG frame               │
│   ├── GET  /frame      — serve latest frame to dashboard    │
│   ├── POST /command    — send next/prev to detector         │
│   ├── WS   /ws/alerts  — real-time WebSocket alerts         │
│   └── GET  /           — serve dashboard.html               │
│                                                             │
│   SQLite DB (thermal_sentinel.db)                           │
└─────────────────────────────────────────────────────────────┘
                            │  WebSocket + HTTP
┌───────────────────────────▼─────────────────────────────────┐
│                    BROWSER (Operator)                       │
│                                                             │
│   dashboard.html                                            │
│   ├── Live frame stream (from detector via /frame)          │
│   ├── ← Prev / Next → controls (POST /command)              │
│   ├── Stats bar (Total / Critical / Safe / Rate)            │
│   ├── Status badge + Severity ΔT gauge                     │
│   ├── Thermal escape area + Insulation health               │
│   └── Scan history table (real-time, auto-refresh)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **AI / Detection** | YOLOv8 (Ultralytics) — container boundary detection |
| **Thermal Simulation** | OpenCV + NumPy — Gaussian hotspot injection on real thermal images |
| **Backend API** | FastAPI + Uvicorn — REST + WebSocket |
| **Database** | SQLite (auto-created, no setup needed) |
| **Frontend** | Vanilla HTML/CSS/JavaScript — no framework dependency |
| **Live Streaming** | JPEG-over-HTTP + WebSocket push |
| **Deployment** | Render (cloud) / localhost (detector) |
| **Training Data** | FLIR Thermal Dataset (Kaggle) + Small-WTB-Thermal1 (GitHub) |

---

## 📂 Repository Structure

```
Azorian--DPWH027/
│
├── src/
│   ├── main.py          ← FastAPI backend (deploy this on Render)
│   ├── detector.py      ← Local thermal scanner (run on-site)
│   ├── database.py      ← SQLite helpers
│   ├── models.py        ← Pydantic schemas
│   └── api.py           ← Legacy API helpers
│
├── dashboard.html        ← Frontend UI (served by FastAPI)
├── requirements.txt      ← Production deps (Render)
├── requirements-local.txt← Local deps (detector + YOLO)
├── render.yaml           ← Render deployment config
├── reefer_data.yaml      ← YOLO dataset config
└── README.md
```

> **Not in repo** (too large or local-only):
> - `data/` — thermal image datasets (download separately)
> - `runs/` — trained model weights (`best.pt`)
> - `.venv/` — virtual environment

---

## 🚀 Deployment

### Option A — Deploy API on Render (Recommended)

1. Push this repo to GitHub (see steps below)
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo: `vivekbobbili9/Azorian--DPWH027`
4. Render auto-detects `render.yaml` — click **Deploy**
5. Your API + dashboard will be live at:
   ```
   https://thermal-sentinel-api.onrender.com
   ```

**Render settings (if configuring manually):**
| Setting | Value |
|---------|-------|
| Runtime | Python 3.11 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn src.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

---

### Option B — Run Locally (Full System)

**Step 1 — Install API dependencies:**
```bash
pip install -r requirements.txt
```

**Step 2 — Install detector dependencies:**
```bash
pip install -r requirements-local.txt
```

**Step 3 — Start the API (Terminal 1):**
```bash
cd src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Step 4 — Start the detector (Terminal 2):**
```bash
python src/detector.py
```

**Step 5 — Open the dashboard (Terminal 3):**
```bash
python -m http.server 3000
# Then open: http://localhost:3000/dashboard.html
```

> Or just go to `http://127.0.0.1:8000` — the API serves the dashboard too.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard UI |
| `GET` | `/health` | Health check |
| `POST` | `/scan` | Ingest a scan result |
| `GET` | `/scans` | Get scan history (last 24h) |
| `GET` | `/stats` | KPI summary (total, critical, safe…) |
| `POST` | `/simulate` | Trigger a random simulated scan |
| `POST` | `/frame` | Push latest thermal JPEG (from detector) |
| `GET` | `/frame` | Get latest thermal JPEG (to dashboard) |
| `POST` | `/command` | Send next/prev command to detector |
| `GET` | `/command` | Detector polls this for commands |
| `WS` | `/ws/alerts` | WebSocket — real-time alert push |
| `GET` | `/docs` | Interactive API docs (Swagger UI) |

---

## 🌡️ How It Works — Workflow

```
1. detector.py loads thermal images from local folders
      ↓
2. YOLOv8 detects the container region (bounding box)
   — Falls back to full frame if no box found
      ↓
3. A synthetic Gaussian hotspot is injected (45% chance)
   — Simulates refrigerant leak using real thermal colormap
      ↓
4. Peak temperature is calculated from pixel brightness
   — SAFE   < 40°C ΔT
   — MODERATE  40–60°C ΔT  
   — CRITICAL  > 60°C ΔT
      ↓
5. Result is POSTed to /scan → stored in SQLite
      ↓
6. Display frame is encoded as JPEG → POSTed to /frame
      ↓
7. Dashboard receives NEW_FRAME via WebSocket
   → Fetches latest stats, scans, and frame image
   → Updates all panels in real-time
```

---

## 📊 Dashboard Controls

| Control | Action |
|---------|--------|
| `← Prev` / `Next →` | Navigate detector to previous/next image |
| `Normal / Moderate / Critical` | Local UI simulation (offline mode) |
| `Upload thermal image` tab | Upload any thermal image for simulated scan |

---

## 📦 Datasets Used

| Dataset | Source | Purpose |
|---------|--------|---------|
| FLIR Thermal | [Kaggle](https://www.kaggle.com/datasets/deepnewbie/flir-thermal-images-dataset) | Real thermal imagery for simulation |
| Small-WTB-Thermal1 | [GitHub](https://github.com/MoShekaramiz/Small-WTB-Thermal1) | Wind turbine thermal anomaly patterns |
| Reefer Container Dataset v2 | Roboflow | YOLOv8 container detection training |

---

## 👥 Team

**DPWH027 — Azorian**  
Built for the DP World Global Hackathon 2027

---

## 📄 License

MIT License — free to use, modify, and distribute with attribution.
