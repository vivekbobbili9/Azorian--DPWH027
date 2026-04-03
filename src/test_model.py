# src/test_model.py
import cv2
from ultralytics import YOLO
from pathlib import Path

WEIGHTS  = "runs/thermal_sentinel/reefer_v1/weights/best.pt"
TEST_DIR = Path("data/reefer_dataset.v2i.yolov8/test/images")

model = YOLO(WEIGHTS)
Path("outputs").mkdir(exist_ok=True)

images = list(TEST_DIR.glob("*.jpg")) + list(TEST_DIR.glob("*.png"))
print(f"Testing on {len(images)} images...\n")

for i, img_path in enumerate(images[:10]):
    img     = cv2.imread(str(img_path))
    results = model(img, conf=0.30, verbose=False)[0]

    for box in results.boxes:
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        # Leak logic: low confidence = anomaly = potential leak
        if conf < 0.60:
            color = (0, 0, 255)   # red = leak suspected
            label = f"LEAK SUSPECTED {conf:.0%}"
        else:
            color = (0, 255, 0)   # green = normal
            label = f"Normal {conf:.0%}"

        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)
        cv2.putText(img, label, (x1, max(0, y1-10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    out = f"outputs/result_{i+1}.jpg"
    cv2.imwrite(out, img)
    print(f"Saved → {out}")

print("\nDone. Check outputs/ folder.")