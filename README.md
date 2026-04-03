# 🌡️ Azorian · Thermal Sentinel

> **AI-powered thermal leak detection system for reefer (refrigerated) shipping containers** — built for DP World Hackathon 2027 (DPWH027)

A real-time port gate intelligence system that scans containers using thermal imaging, detects refrigerant leaks using YOLOv8 + Gaussian anomaly injection, logs every scan to a SQLite database, and streams live results to a web dashboard.

---

## 🏗️ Architecture

```
  Thermal Images ──► detector.py ──► POST /scan + POST /frame
                                              │
                                     FastAPI (main.py)
                                     SQLite Database
                                              │
                                     dashboard.html  ◄── Browser
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **AI / Detection** | YOLOv8 (Ultralytics) — container boundary detection |
| **Thermal Simulation** | OpenCV + NumPy — Gaussian hotspot injection |
| **Backend API** | FastAPI + Uvicorn — REST + WebSocket |
| **Database** | SQLite (auto-created, no setup needed) |
| **Frontend** | Vanilla HTML / CSS / JavaScript |
| **Live Streaming** | JPEG-over-HTTP + WebSocket push |
| **Training Data** | FLIR Thermal Dataset + Small-WTB-Thermal1 + Reefer Dataset v2 |

---

## 📂 Repository Structure

```
Azorian--DPWH027/
│
├── src/
│   ├── main.py               ← FastAPI backend
│   ├── detector.py           ← Local thermal scanner
│   ├── database.py           ← SQLite helpers
│   ├── models.py             ← Pydantic schemas
│   └── api.py                ← API helpers
│
├── dashboard.html            ← Frontend UI
├── requirements.txt          ← API dependencies
├── requirements-local.txt    ← Detector dependencies (YOLO + OpenCV)
└── README.md
```

> **Not included in repo** (too large):
> `data/` datasets · `runs/best.pt` model weights · `.venv/` virtual env

---

## 🖥️ Run Locally — Step by Step

Follow these exact steps to run the full system on your own machine.

---

### ✅ Prerequisites

Make sure you have these installed before starting:

- **Python 3.11** → [python.org/downloads](https://www.python.org/downloads/)
- **Git** → [git-scm.com](https://git-scm.com/)
- **Your thermal images** — a folder on your PC with `.jpg` / `.png` thermal images

---

### Step 1 — Get the code from GitHub

Open **Command Prompt** and run:

```cmd
git clone https://github.com/vivekbobbili9/Azorian--DPWH027.git
```

Then enter the project folder:

```cmd
cd Azorian--DPWH027
```

---

### Step 2 — Install dependencies

Install the API dependencies:

```cmd
pip install -r requirements.txt
```

Install the detector dependencies (YOLO + OpenCV):

```cmd
pip install -r requirements-local.txt
```

> ⏳ This may take 5–10 minutes the first time (downloads PyTorch + Ultralytics)

---

### Step 3 — Point the detector to your images

Open `src/detector.py` in any text editor and find this section (around line 55):

```python
DATASET_DIRS = [
    Path(r"C:\Users\bandi\Downloads\thermul"),
    Path(r"C:\Users\bandi\Downloads\THERMAL-SENTINEL\data\..."),
]
```

**Change these paths to YOUR thermal image folder.** Example:

```python
DATASET_DIRS = [
    Path(r"C:\Users\YourName\Downloads\my-thermal-images"),
]
```

> ℹ️ Any folder with `.jpg` or `.png` images works. Even normal photos — the system converts them to thermal colormap automatically.

---

### Step 4 — Open 3 separate Command Prompt windows

You need **3 terminals open at the same time**.

---

**Terminal 1 — Start the API:**

```cmd
cd Azorian--DPWH027\src
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ Database initialized!
```

---

**Terminal 2 — Start the detector:**

```cmd
cd Azorian--DPWH027
python src/detector.py
```

You should see:
```
✅ Model: yolov8n.pt
🚀 245 images loaded.
📡 API → MSCU1234567 | 68.3°C | 201
```

> An OpenCV window also opens showing the thermal scan live.

---

**Terminal 3 — Serve the dashboard:**

```cmd
cd Azorian--DPWH027
python -m http.server 3000
```

---

### Step 5 — Open the dashboard

Open your browser and go to:

```
http://localhost:3000/dashboard.html
```

Or go directly to the API (also serves dashboard):

```
http://127.0.0.1:8000
```

---

### Step 6 — What you should see

| Panel | What it shows |
|-------|--------------|
| **Live scan** | Real thermal frame from your detector, updates every scan |
| **← Prev / Next →** | Control which image the detector is on |
| **Stats bar** | Total scans, Critical, Safe, Moderate, Detection rate |
| **Status badge** | SAFE / MODERATE / CRITICAL based on latest scan |
| **ΔT gauge** | Temperature difference from ambient |
| **Scan history table** | Every scan result with timestamp and verdict |

---

### Controls

| Key / Button | Action |
|---|---|
| `Next →` on dashboard | Go to next image |
| `← Prev` on dashboard | Go to previous image |
| `Q` in OpenCV window | Quit the detector |
| `Ctrl+C` in any terminal | Stop that service |

---

### Stopping everything

Press `Ctrl+C` in each of the 3 terminals to stop.

---

## 🔌 API Endpoints

Once the API is running, you can view all endpoints at:
```
http://127.0.0.1:8000/docs
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard UI |
| `GET` | `/stats` | KPI summary |
| `GET` | `/scans` | Scan history |
| `POST` | `/scan` | Submit a scan |
| `GET` | `/frame` | Latest thermal frame |
| `WS` | `/ws/alerts` | Real-time WebSocket alerts |

---

## 🌡️ How It Works

```
1. detector.py loads images from your folder
      ↓
2. YOLOv8 finds the container region (falls back to full frame)
      ↓
3. Gaussian hotspot injected on 45% of images (simulates a leak)
      ↓
4. Peak temperature calculated from pixel brightness
   SAFE < 40°C  |  MODERATE 40–60°C  |  CRITICAL > 60°C
      ↓
5. Result POSTed to /scan → saved in SQLite database
      ↓
6. Frame encoded as JPEG → POSTed to /frame
      ↓
7. Dashboard receives NEW_FRAME via WebSocket
   → All panels update instantly
```

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
