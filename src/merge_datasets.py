import os
import cv2
import shutil
import numpy as np
from pathlib import Path
from tqdm import tqdm

# --- 1. DYNAMIC PATH SOLVER ---
# This looks for your folders whether they are in ROOT or in DATA/
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"


def find_path(folder_name):
    # Check in Root first, then in Data folder
    if (ROOT / folder_name).exists():
        return ROOT / folder_name
    if (DATA_DIR / folder_name).exists():
        return DATA_DIR / folder_name
    return None


# Locate your specific folders from your screenshot
ROBO_DIR = find_path("reefer_dataset.v2i.yolov8")
WTB_DIR = find_path("Small-WTB-Thermal1-main")
ANOM_DIR = find_path("Anomalies")
FINAL_DIR = DATA_DIR / "reefer_final"


def merge():
    print("🚀 Starting Thermal Sentinel Dataset Merger...")

    # Create final structure
    (FINAL_DIR / "images/train").mkdir(parents=True, exist_ok=True)
    (FINAL_DIR / "labels/train").mkdir(parents=True, exist_ok=True)

    # --- STEP 1: ADD NORMAL CONTAINERS (Class 0) ---
    if ROBO_DIR:
        # Roboflow usually puts images in train/images
        img_path = ROBO_DIR / "train" / "images"
        robo_imgs = list(img_path.glob("*.jpg")) + list(img_path.glob("*.png"))

        print(f"📦 Found {len(robo_imgs)} Normal Container images in {img_path}")

        for img_p in tqdm(robo_imgs[:500], desc="Processing Normals"):
            shutil.copy(img_p, FINAL_DIR / "images/train" / img_p.name)
            # Label: Class 0, Center-aligned box
            with open(FINAL_DIR / "labels/train" / f"{img_p.stem}.txt", "w") as f:
                f.write("0 0.5 0.5 0.9 0.9\n")
    else:
        print("❌ ERROR: Could not find reefer_dataset folder!")

    # --- STEP 2: ADD THERMAL LEAKS (Class 1) ---
    leak_sources = []
    # Search WTB and Anomalies folders for any image type
    for folder in [WTB_DIR, ANOM_DIR]:
        if folder:
            print(f"🔍 Searching for leaks in: {folder}")
            for ext in ["**/*.jpg", "**/*.png", "**/*.bmp", "**/*.jpeg"]:
                leak_sources.extend(list(folder.glob(ext)))

    print(f"🔥 Total Leak images found: {len(leak_sources)}")

    if len(leak_sources) == 0:
        print("❌ ERROR: No leak images found. AI will not be able to detect leaks!")
        return

    for i, img_p in enumerate(tqdm(leak_sources, desc="Processing Leaks")):
        new_name = f"leak_{i}.jpg"
        # Standardize images to RGB/JPG for YOLO
        img = cv2.imread(str(img_p))
        if img is not None:
            cv2.imwrite(str(FINAL_DIR / "images/train" / new_name), img)
            # Label: Class 1 (Leak)
            with open(FINAL_DIR / "labels/train" / f"leak_{i}.txt", "w") as f:
                f.write("1 0.5 0.5 0.8 0.8\n")

    print(f"\n✅ SUCCESS! Dataset merged at: {FINAL_DIR.absolute()}")
    print("Next step: Run 'python src/train_reefer.py'")


if __name__ == "__main__":
    merge()
