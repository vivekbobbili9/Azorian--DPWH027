"""
Thermal Sentinel — Detector (Dashboard-Connected Edition)
=========================================================
• Pushes each processed frame as JPEG to /frame  → shown live in dashboard
• Pushes scan result to /scan                     → updates stats instantly
• Polls /command every 200 ms                     → dashboard arrows control it
• OpenCV window still opens (press Q to quit)
"""

import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import random, time, requests

import os
API_URL = os.environ.get("API_URL", "https://dpwh027.onrender.com")

# ─────────────────────────────────────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def push_frame(frame_bgr: np.ndarray):
    """Encode frame as JPEG and push to /frame endpoint."""
    try:
        _, buf = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
        requests.post(f"{API_URL}/frame",
                      data=buf.tobytes(),
                      headers={"Content-Type": "application/octet-stream"},
                      timeout=0.5)
    except Exception:
        pass

def report_scan(container_id, thermal_max_temp, confidence_score, gate_id="GATE-1"):
    try:
        r = requests.post(f"{API_URL}/scan", json={
            "container_id":     container_id,
            "thermal_max_temp": thermal_max_temp,
            "confidence_score": confidence_score,
            "gate_id":          gate_id
        }, timeout=1)
        print(f"📡 API → {container_id} | {thermal_max_temp:.1f}°C | {r.status_code}")
    except Exception as e:
        print(f"⚠️  API offline: {e}")

def poll_command() -> str:
    """Returns 'next', 'prev', 'quit' or '' — clears the command server-side."""
    try:
        r = requests.get(f"{API_URL}/command", timeout=0.3)
        return r.json().get("action", "")
    except Exception:
        return ""

# ─────────────────────────────────────────────────────────────────────────────
# MODEL & IMAGES
# ─────────────────────────────────────────────────────────────────────────────
model_path = Path("runs/detect/runs/thermal_sentinel/reefer_v1/weights/best.pt")
model = YOLO(str(model_path)) if model_path.exists() else YOLO('yolov8n.pt')
print(f"✅ Model: {model_path if model_path.exists() else 'yolov8n.pt'}")

DATASET_DIRS = [
    Path("sample_data"),                          # ← included in repo, works for everyone
    Path(r"C:\Users\bandi\Downloads\thermul"),    # original local path
    Path(r"C:\Users\bandi\Downloads\THERMAL-SENTINEL\data\reefer_dataset.v2i.yolov8\train\images"),
]

image_files = []
for folder in DATASET_DIRS:
    if folder.exists():
        for ext in ["*.jpg","*.jpeg","*.png","*.JPG","*.JPEG","*.PNG","*.webp"]:
            image_files.extend(folder.rglob(ext))

if not image_files:
    print("💥 No images found!"); exit()

random.shuffle(image_files)
print(f"🚀 {len(image_files)} images loaded.")
print("   Dashboard arrows = next/prev  |  Q in OpenCV window = quit\n")

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def inject_leak(gray_crop, cx, cy, radius, intensity):
    h, w = gray_crop.shape
    Y, X = np.ogrid[:h, :w]
    blob = np.exp(-(((X-cx)**2)/(2*(radius/2)**2)+((Y-cy)**2)/(2*(radius/2)**2)))*intensity
    return np.clip(gray_crop.astype(np.float32)+blob, 0, 255).astype(np.uint8)

def draw_thermometer(frame):
    h, w = frame.shape[:2]
    bar_w, bar_h = 25, int(h*0.4)
    sx, sy = w-bar_w-20, int((h-bar_h)/2)
    gradient = np.tile(np.linspace(255,0,bar_h,dtype=np.uint8),(bar_w,1)).T
    frame[sy:sy+bar_h, sx:sx+bar_w] = cv2.applyColorMap(gradient, cv2.COLORMAP_JET)
    cv2.rectangle(frame,(sx,sy),(sx+bar_w,sy+bar_h),(255,255,255),2)
    for txt, y in [("85C",sy+10),("20C",sy+bar_h)]:
        cv2.putText(frame,txt,(sx-45,y),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,0),3)
        cv2.putText(frame,txt,(sx-45,y),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,255),1)

def best_box(boxes):
    if not boxes: return []
    def score(b):
        x1,y1,x2,y2=b; bw=x2-x1; bh=y2-y1
        aspect=bw/max(bh,1)
        return bw*bh*(min(aspect/1.5,2.0) if aspect>=1.2 else 0.5)
    return sorted(boxes,key=score,reverse=True)[:1]

PREFIXES = ["TRHU","MSCU","HLXU","GESU","TEMU"]

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP — index-based so Prev works
# ─────────────────────────────────────────────────────────────────────────────
idx = 0
while 0 <= idx < len(image_files):
    img_path = image_files[idx]
    raw = cv2.imread(str(img_path))
    if raw is None:
        idx += 1; continue

    h0, w0 = raw.shape[:2]
    if w0 > 1000:
        raw = cv2.resize(raw, (1000, int(1000*h0/w0)))
    h, w = raw.shape[:2]
    image_area = h * w

    gray = (cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY).astype(np.float32) * 0.35).astype(np.uint8)
    results = model(raw, conf=0.15, verbose=False)

    valid_boxes = []
    for r in results:
        for box in r.boxes:
            x1,y1,x2,y2 = map(int, box.xyxy[0])
            if (x2-x1)*(y2-y1) >= image_area*0.05:
                valid_boxes.append((x1,y1,x2,y2))

    valid_boxes = best_box(valid_boxes)
    using_fallback = False
    if not valid_boxes:
        px,py = int(w*0.04), int(h*0.04)
        valid_boxes = [(px,py,w-px,h-py)]
        using_fallback = True

    do_inject = random.random() < 0.45
    ui_elements = []
    fake_id = f"{random.choice(PREFIXES)}{random.randint(1000000,9999999)}"

    if do_inject:
        x1,y1,x2,y2 = valid_boxes[0]
        bw, bh = x2-x1, y2-y1
        crop = gray[y1:y2, x1:x2]
        if crop.size > 0:
            m = 20; sw = bw-2*m; sh = bh-2*m
            if sw > 10 and sh > 10:
                cx, cy = m+random.randint(0,sw), m+random.randint(0,sh)
                r_   = random.randint(22,50)
                I    = random.randint(100,165)
                new  = inject_leak(crop,cx,cy,r_,I)
                gray[y1:y2,x1:x2] = new
                peak_b    = float(np.max(new[max(0,cy-2):cy+3, max(0,cx-2):cx+3]))
                peak_temp = 20.0 + (peak_b/255.0)*65.0
                color,status = ((0,0,255),"CRITICAL LEAK") if peak_temp>=60 else \
                               ((0,165,255),"MODERATE WARNING") if peak_temp>=40 else \
                               ((0,220,100),"MINOR WARMING")
                lx1=x1+max(0,cx-r_); ly1=y1+max(0,cy-r_)
                lx2=x1+min(bw,cx+r_); ly2=y1+min(bh,cy+r_)
                ui_elements.append({"coords":(x1,y1,x2,y2),"color":color,
                                    "status":status,"temp":peak_temp,
                                    "leak":(lx1,ly1,lx2,ly2),"has_leak":True})
                report_scan(fake_id, peak_temp, round(random.uniform(0.75,0.99),2))
    else:
        for box in valid_boxes:
            ui_elements.append({"coords":box,"color":(0,220,0),
                                 "status":"SYSTEM SAFE","temp":22.0,
                                 "leak":None,"has_leak":False})
        report_scan(fake_id, 22.0, round(random.uniform(0.75,0.99),2))

    # ── Build display frame ────────────────────────────────────────────────
    display = cv2.applyColorMap(gray, cv2.COLORMAP_JET)

    for ui in ui_elements:
        x1,y1,x2,y2 = ui["coords"]; c = ui["color"]
        cv2.rectangle(display,(x1,y1),(x2,y2),c,2 if using_fallback else 3)
        bg_y1 = max(0,y1-35)
        cv2.rectangle(display,(x1,bg_y1),(x2,bg_y1+35),(0,0,0),-1)
        pfx = f"Peak: {ui['temp']:.1f}C | " if ui["has_leak"] else ""
        cv2.putText(display,f"{pfx}{ui['status']}",(x1+10,bg_y1+25),
                    cv2.FONT_HERSHEY_SIMPLEX,0.7,c,2)
        if ui["has_leak"] and ui["leak"]:
            lx1,ly1,lx2,ly2 = ui["leak"]
            cv2.rectangle(display,(lx1-3,ly1-3),(lx2+3,ly2+3),c,3)
            cv2.rectangle(display,(lx1,ly1),(lx2,ly2),c,2)
            py_ = max(0,ly1-20)
            cv2.rectangle(display,(lx1,py_),(lx1+55,py_+20),c,-1)
            cv2.putText(display,"LEAK",(lx1+4,py_+15),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,255),2)

    draw_thermometer(display)

    # ── Filename watermark ─────────────────────────────────────────────────
    cv2.putText(display, f"[{idx+1}/{len(image_files)}] {img_path.name}",
                (8,18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120,120,120), 1)

    # ── Push frame to dashboard ────────────────────────────────────────────
    push_frame(display)

    # ── Show in OpenCV window too ──────────────────────────────────────────
    cv2.imshow("Thermal Sentinel", display)

    # ── Wait for command (dashboard arrows or keyboard) ────────────────────
    step = 0          # +1=next  -1=prev
    deadline = time.time() + 30  # auto-advance after 30s if no command
    while step == 0 and time.time() < deadline:
        key = cv2.waitKey(200) & 0xFF
        if key == ord('q') or key == 27:
            cv2.destroyAllWindows()
            print("Quit."); exit()
        if key in (32, 100, 83):    # Space, D, Right
            step = 1; break
        if key == 97:               # A / Left
            step = -1; break

        cmd = poll_command()
        if cmd == "next":  step = 1;  break
        if cmd == "prev":  step = -1; break
        if cmd == "quit":
            cv2.destroyAllWindows(); exit()

    idx = max(0, idx + (step if step != 0 else 1))

cv2.destroyAllWindows()
print("All images processed.")