# 🌡️ Azorian · Thermal Sentinel

> AI-powered thermal leak detection system for reefer containers — DP World Hackathon 2027 (DPWH027)

---

## ⚡ Quick Start — For Judges

> **Total time: ~10 minutes.** Just 4 steps. No manual configuration needed.

---

### Before you begin — install these two things:

| Software | Download Link |
|----------|--------------|
| **Python 3.11** | https://www.python.org/downloads/release/python-3119/ → scroll down → **Windows installer (64-bit)** → ⚠️ tick **"Add Python to PATH"** before installing |
| **Git** | https://git-scm.com/download/win → download and install with all default settings |

---

### Step 1 — Clone the repository

Open **Command Prompt** (search "cmd" in Start menu) and run:

```
git clone https://github.com/vivekbobbili9/Azorian--DPWH027.git
cd Azorian--DPWH027
```

---

### Step 2 — Run setup (one time only)

In File Explorer, open the `Azorian--DPWH027` folder and **double-click `setup.bat`**

Or in CMD:
```
setup.bat
```

> ⏳ This installs all dependencies. Takes **5–10 minutes** the first time.  
> If you see any red errors — just wait, it keeps going and usually succeeds.

---

### Step 3 — Start everything

In the same folder, **double-click `start_all.bat`**

Or in CMD:
```
start_all.bat
```

> This opens 3 terminal windows automatically + launches the browser.

---

### Step 4 — View the dashboard

Your browser will open automatically to:
```
http://localhost:3000/dashboard.html
```

If it doesn't open automatically, paste that link into your browser manually.

---

### ✅ What you'll see

- **Live scan panel** — thermal images being scanned with AI detection
- **Stats bar** — total scans, critical alerts, safe containers, detection rate
- **← Prev / Next →** buttons — browse through images from the dashboard
- **Scan history table** — every result logged in real time
- **DENY GATE ENTRY banner** — flashes red when a critical leak is detected

---

### ❌ Troubleshooting

| Problem | Fix |
|---------|-----|
| `python not found` | Reinstall Python 3.11, tick "Add Python to PATH" |
| `pip install error / subprocess failed` | Run `setup.bat` again — it uses `--prefer-binary` flag to avoid build errors |
| Dashboard shows `API Offline` | Wait 10 seconds — the API takes a moment to start |
| Live frame says "Waiting for detector" | Wait 20 seconds for the detector to load images |
| Port already in use | Restart your PC and try again |

---

### To stop the system

Close the 3 black terminal windows that `start_all.bat` opened.

---

---

## 🏗️ How It Works

```
  Thermal Images ──► detector.py ──► POST /scan + POST /frame
                                              │
                                     FastAPI (main.py)
                                     SQLite Database
                                              │
                                     dashboard.html  ◄── Browser
```

### Detection Pipeline

```
1. Load thermal images from sample_data/ folder
      ↓
2. YOLOv8 detects container boundaries in each image
      ↓
3. Gaussian hotspot injected on ~45% of images (simulates refrigerant leak)
      ↓
4. Peak temperature calculated from pixel brightness
   — SAFE      below 40°C delta
   — MODERATE  40–60°C delta
   — CRITICAL  above 60°C delta
      ↓
5. Result saved to SQLite database via POST /scan
      ↓
6. Frame encoded as JPEG → sent to dashboard via POST /frame
      ↓
7. Dashboard updated instantly via WebSocket
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **AI / Detection** | YOLOv8 (Ultralytics) |
| **Thermal Simulation** | OpenCV + NumPy — Gaussian hotspot injection |
| **Backend API** | FastAPI + Uvicorn — REST + WebSocket |
| **Database** | SQLite (auto-created on first run) |
| **Frontend** | HTML / CSS / JavaScript — no framework |
| **Live Feed** | JPEG-over-HTTP + WebSocket push |

---

## 📂 Repository Structure

```
Azorian--DPWH027/
│
├── sample_data/              ← Sample thermal images (included — works out of the box)
│
├── src/
│   ├── main.py               ← FastAPI backend
│   ├── detector.py           ← Thermal scanner + YOLO detection
│   ├── database.py           ← SQLite helpers
│   └── models.py             ← Data schemas
│
├── dashboard.html            ← Web dashboard (frontend)
├── setup.bat                 ← One-click dependency installer
├── start_all.bat             ← One-click start all services
├── requirements.txt          ← API dependencies
└── requirements-local.txt    ← Detector dependencies
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard UI |
| `GET` | `/stats` | KPI summary |
| `GET` | `/scans` | Scan history |
| `POST` | `/scan` | Submit a scan result |
| `GET` | `/frame` | Latest thermal frame |
| `WS` | `/ws/alerts` | Real-time WebSocket alerts |
| `GET` | `/docs` | Interactive API explorer |

---

## 📦 Datasets Used

| Dataset | Source |
|---------|--------|
| FLIR Thermal | [Kaggle](https://www.kaggle.com/datasets/deepnewbie/flir-thermal-images-dataset) |
| Small-WTB-Thermal1 | [GitHub](https://github.com/MoShekaramiz/Small-WTB-Thermal1) |
| Reefer Container Dataset v2 | Roboflow |

---

## 👥 Team

**DPWH027 — Azorian**  
Built for the DP World Global Hackathon 2027

---

## 📄 License

MIT — free to use with attribution.
