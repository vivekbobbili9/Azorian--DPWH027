# src/train_reefer.py
from ultralytics import YOLO
import torch

DEVICE = 0 if torch.cuda.is_available() else "cpu"
print(f"Training on: {'GPU' if DEVICE == 0 else 'CPU'}")

model = YOLO("yolov8n.pt")

results = model.train(
    data    = "reefer_data.yaml",
    epochs  = 80,
    imgsz   = 640,
    batch   = 8,
    device  = DEVICE,

    lr0     = 0.01,
    lrf     = 0.01,
    momentum= 0.937,
    weight_decay = 0.0005,
    warmup_epochs= 3,

    # Thermal-safe augmentations
    hsv_h   = 0.0,
    hsv_s   = 0.0,
    hsv_v   = 0.4,
    degrees = 5.0,
    translate= 0.1,
    scale   = 0.3,
    fliplr  = 0.5,
    flipud  = 0.0,
    mosaic  = 0.7,
    mixup   = 0.0,

    project = "runs/thermal_sentinel",
    name    = "reefer_v1",
    save    = True,
    plots   = True,
    cache   = True,
    patience= 20,
    exist_ok= True,
    verbose = True,
)

print("\n✅ TRAINING COMPLETE")
print(f"Best weights: runs/thermal_sentinel/reefer_v1/weights/best.pt")
print(f"mAP50: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")