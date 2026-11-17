"""
WoundWatch - Auto Download & Sort Wound Datasets
Downloads from multiple free sources and sorts into train/val folders
Classes: healthy (GREEN), mild_risk (YELLOW), infected (RED)
"""

import os
import sys
import shutil
import zipfile
import random
from pathlib import Path

def install_deps():
    print("Installing dependencies...")
    os.system(f"{sys.executable} -m pip install requests pillow datasets huggingface_hub roboflow --quiet --break-system-packages")

def create_folders(base_dir):
    """Create dataset folder structure"""
    for split in ["train", "val"]:
        for cls in ["healthy", "mild_risk", "infected"]:
            (base_dir / split / cls).mkdir(parents=True, exist_ok=True)
    print("Folder structure created!")

def download_surgwound(base_dir):
    """Download SurgWound dataset from HuggingFace (697 images)"""
    print("\n" + "="*50)
    print("[1/3] Downloading SurgWound from HuggingFace...")
    print("="*50)

    try:
        from datasets import load_dataset
        from PIL import Image

        ds = load_dataset("SATHEESHMA/SurgWound", split="train")
        print(f"  Found {len(ds)} samples")

        saved = 0
        for i, sample in enumerate(ds):
            try:
                img = sample.get("image")
                if img is None:
                    continue

                if not isinstance(img, Image.Image):
                    continue

                img = img.convert("RGB")

                # Try to classify based on metadata
                risk = "mild_risk"  # default

                # Check all fields for infection/risk info
                for key, val in sample.items():
                    if key == "image":
                        continue
                    val_str = str(val).lower().strip()

                    # Check for infection risk
                    if any(word in key.lower() for word in ["infection", "risk", "healing"]):
                        if any(w in val_str for w in ["low", "none", "no", "minimal", "good", "well", "normal", "clean"]):
                            risk = "healthy"
                        elif any(w in val_str for w in ["high", "severe", "critical", "yes", "poor", "infected"]):
                            risk = "infected"
                        elif any(w in val_str for w in ["moderate", "medium", "mild", "some"]):
                            risk = "mild_risk"

                    # Check erythema/edema fields
                    if any(word in key.lower() for word in ["erythema", "edema", "redness"]):
                        if any(w in val_str for w in ["severe", "high", "significant", "marked"]):
                            risk = "infected"
                        elif any(w in val_str for w in ["mild", "slight", "minimal"]):
                            risk = "mild_risk" if risk != "infected" else risk
                        elif any(w in val_str for w in ["none", "no", "absent"]):
                            risk = "healthy" if risk == "mild_risk" else risk

                filename = f"surgwound_{i:04d}.jpg"
                img.save(base_dir / "all" / risk / filename, "JPEG", quality=95)
                saved += 1

                if saved % 50 == 0:
                    print(f"  Saved {saved} images...")

            except Exception as e:
                continue

        print(f"  SurgWound: Saved {saved} images")
        return saved

    except Exception as e:
        print(f"  SurgWound download failed: {e}")
        return 0


def download_mendeley_wound(base_dir):
    """Download Lower Limb Wound Dataset from Mendeley (8000+ images)"""
    print("\n" + "="*50)
    print("[2/3] Downloading Lower Limb Wound from Mendeley...")
    print("="*50)

    import requests

    # Mendeley Data API
    urls_to_try = [
        "https://data.mendeley.com/public-files/datasets/hsj38fwnvr/files/",
        "https://prod-dcd-datasets-cache-zipfiles.s3.eu-west-1.amazonaws.com/hsj38fwnvr-3.zip",
    ]

    download_dir = base_dir / "downloads"
    download_dir.mkdir(exist_ok=True)

    print("  This is a large dataset (~8000 images).")
    print("  If auto-download fails, manually download from:")
    print("  https://data.mendeley.com/datasets/hsj38fwnvr/3")
    print("  Then extract ZIP into: dataset/downloads/mendeley/")

    try:
        # Try direct download
        for url in urls_to_try:
            try:
                print(f"  Trying download...")
                r = requests.get(url, stream=True, timeout=30, allow_redirects=True)
                if r.status_code == 200 and int(r.headers.get('content-length', 0)) > 1000000:
                    zip_path = download_dir / "mendeley_wound.zip"
                    total = int(r.headers.get('content-length', 0))
                    downloaded = 0

                    with open(zip_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                pct = downloaded * 100 // total
                                if pct % 10 == 0:
                                    print(f"  Downloading: {pct}%", end='\r')

                    print(f"\n  Downloaded: {zip_path}")

                    # Extract
                    extract_dir = download_dir / "mendeley"
                    extract_dir.mkdir(exist_ok=True)

                    with zipfile.ZipFile(zip_path, 'r') as z:
                        z.extractall(extract_dir)
                    print(f"  Extracted to: {extract_dir}")

                    # Sort images
                    return sort_mendeley_images(extract_dir, base_dir)

            except Exception as e:
                continue

        # If download failed, check if manually placed
        manual_dir = download_dir / "mendeley"
        if manual_dir.exists():
            return sort_mendeley_images(manual_dir, base_dir)

        print("  Auto-download not available. Download manually:")
        print("  1. Go to: https://data.mendeley.com/datasets/hsj38fwnvr/3")
        print("  2. Click Download")
        print("  3. Extract ZIP to: dataset/downloads/mendeley/")
        print("  4. Run this script again")
        return 0

    except Exception as e:
        print(f"  Mendeley download error: {e}")
        return 0


def sort_mendeley_images(extract_dir, base_dir):
    """Sort Mendeley wound images into our classes"""
    from PIL import Image
    import numpy as np

    saved = 0

    # Walk through all extracted folders
    for root, dirs, files in os.walk(extract_dir):
        folder_name = Path(root).name.lower()

        for fname in files:
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                continue

            fpath = Path(root) / fname

            # Classify based on folder name
            if any(w in folder_name for w in ["normal", "healthy", "clean"]):
                cls = "healthy"
            elif any(w in folder_name for w in ["wound_main", "wound", "ulcer"]):
                # Use color analysis to sub-classify wounds
                cls = classify_by_color(str(fpath))
            elif any(w in folder_name for w in ["mask", "segmentation"]):
                continue  # Skip mask images
            else:
                cls = classify_by_color(str(fpath))

            try:
                img = Image.open(fpath).convert("RGB")
                img = img.resize((224, 224), Image.LANCZOS)
                dest = base_dir / "all" / cls / f"mendeley_{saved:05d}.jpg"
                img.save(dest, "JPEG", quality=90)
                saved += 1

                if saved % 200 == 0:
                    print(f"  Sorted {saved} images...")
            except:
                continue

    print(f"  Mendeley: Saved {saved} images")
    return saved


def classify_by_color(image_path):
    """Classify wound image by color analysis (for sorting)"""
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            return "mild_risk"

        # Resize for speed
        img = cv2.resize(img, (100, 100))

        # Convert to LAB
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)

        mean_a = float(np.mean(a_ch))  # redness
        mean_b = float(np.mean(b_ch))  # yellowness
        std_a = float(np.std(a_ch))    # color variation

        # HSV for red detection
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_red1 = np.array([0, 80, 80])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 80, 80])
        upper_red2 = np.array([180, 255, 255])

        red_mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
        red_pct = np.sum(red_mask > 0) / red_mask.size * 100

        # Score
        score = 0
        score += max(0, (mean_a - 128) * 1.5)  # redness
        score += max(0, (mean_b - 135) * 1.0)   # yellowish discharge
        score += red_pct * 0.5                    # red area
        score += max(0, std_a - 15) * 0.5        # color variation

        if score < 15:
            return "healthy"
        elif score < 40:
            return "mild_risk"
        else:
            return "infected"

    except:
        return "mild_risk"


def download_roboflow_wounds(base_dir):
    """Download wound datasets from Roboflow"""
    print("\n" + "="*50)
    print("[3/3] Downloading from Roboflow...")
    print("="*50)

    print("  Roboflow requires a free account to download.")
    print("  Manual steps:")
    print("  1. Go to: https://universe.roboflow.com/clinicvision/classify-wounds-pgnkj")
    print("  2. Sign up free (Google login works)")
    print("  3. Click 'Download Dataset' → Format: 'Folder' → Download")
    print("  4. Extract images to: dataset/downloads/roboflow/")
    print("")
    print("  More wound datasets on Roboflow:")
    print("  - https://universe.roboflow.com/wounddetection-lvlph/surgical-wound-classification")
    print("  - https://universe.roboflow.com/wounddetectionai/wounds_type-jtzt1")
    print("  - https://universe.roboflow.com/kiranbk/wsdv2")

    # Check if manually downloaded
    roboflow_dir = base_dir / "downloads" / "roboflow"
    if roboflow_dir.exists():
        return sort_roboflow_images(roboflow_dir, base_dir)

    return 0


def sort_roboflow_images(roboflow_dir, base_dir):
    """Sort Roboflow downloaded images"""
    from PIL import Image

    saved = 0
    for root, dirs, files in os.walk(roboflow_dir):
        folder_name = Path(root).name.lower()

        for fname in files:
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue

            fpath = Path(root) / fname

            # Map Roboflow class names to ours
            if any(w in folder_name for w in ["abrasion", "laceration", "cut"]):
                cls = "mild_risk"
            elif any(w in folder_name for w in ["burn", "infected", "severe"]):
                cls = "infected"
            elif any(w in folder_name for w in ["bruise", "healing", "normal"]):
                cls = "healthy"
            else:
                cls = classify_by_color(str(fpath))

            try:
                img = Image.open(fpath).convert("RGB")
                img = img.resize((224, 224), Image.LANCZOS)
                dest = base_dir / "all" / cls / f"roboflow_{saved:04d}.jpg"
                img.save(dest, "JPEG", quality=90)
                saved += 1
            except:
                continue

    print(f"  Roboflow: Saved {saved} images")
    return saved


def split_train_val(base_dir, train_ratio=0.8):
    """Split 'all' folder into train (80%) and val (20%)"""
    print("\n" + "="*50)
    print("Splitting into train/val...")
    print("="*50)

    all_dir = base_dir / "all"

    for cls in ["healthy", "mild_risk", "infected"]:
        cls_dir = all_dir / cls
        if not cls_dir.exists():
            continue

        images = list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.png"))
        random.shuffle(images)

        split_idx = int(len(images) * train_ratio)
        train_images = images[:split_idx]
        val_images = images[split_idx:]

        # Copy to train
        for img_path in train_images:
            shutil.copy2(img_path, base_dir / "train" / cls / img_path.name)

        # Copy to val
        for img_path in val_images:
            shutil.copy2(img_path, base_dir / "val" / cls / img_path.name)

        print(f"  {cls}: {len(train_images)} train + {len(val_images)} val = {len(images)} total")

    # Count totals
    total_train = sum(len(list((base_dir / "train" / c).glob("*"))) for c in ["healthy", "mild_risk", "infected"])
    total_val = sum(len(list((base_dir / "val" / c).glob("*"))) for c in ["healthy", "mild_risk", "infected"])

    print(f"\n  TOTAL: {total_train} train + {total_val} val = {total_train + total_val} images")


def print_summary(base_dir):
    """Print final dataset summary"""
    print("\n" + "="*50)
    print("DATASET READY!")
    print("="*50)

    for split in ["train", "val"]:
        print(f"\n  {split.upper()}:")
        for cls in ["healthy", "mild_risk", "infected"]:
            folder = base_dir / split / cls
            if folder.exists():
                count = len(list(folder.glob("*")))
                risk = {"healthy": "GREEN", "mild_risk": "YELLOW", "infected": "RED"}[cls]
                print(f"    {cls:12s} ({risk:6s}): {count} images")

    print(f"\n  Dataset location: {base_dir.absolute()}")
    print(f"\n  Next step: Run train_model.py to train the ML model!")
    print(f"    python train_model.py")


def main():
    print("="*50)
    print("WoundWatch - Dataset Downloader & Sorter")
    print("="*50)

    install_deps()

    base_dir = Path("dataset")

    # Create folder structure
    create_folders(base_dir)

    # Create 'all' temp folder for collecting before split
    for cls in ["healthy", "mild_risk", "infected"]:
        (base_dir / "all" / cls).mkdir(parents=True, exist_ok=True)

    total = 0

    # Download from each source
    total += download_surgwound(base_dir)
    total += download_mendeley_wound(base_dir)
    total += download_roboflow_wounds(base_dir)

    if total == 0:
        print("\nNo images downloaded automatically.")
        print("Please download manually and place in dataset/downloads/")
        print("Then run this script again.")

        # Create README with instructions
        readme = base_dir / "HOW_TO_ADD_IMAGES.txt"
        readme.write_text("""
HOW TO ADD WOUND IMAGES TO DATASET
===================================

DOWNLOAD FROM THESE FREE SOURCES:
1. Mendeley (8000+ images): https://data.mendeley.com/datasets/hsj38fwnvr/3
2. HuggingFace SurgWound (697 images): https://huggingface.co/datasets/SATHEESHMA/SurgWound
3. Roboflow Wound Classification: https://universe.roboflow.com/clinicvision/classify-wounds-pgnkj

SORTING GUIDE - Which images go in which folder:

HEALTHY (GREEN - Normal Healing):
  - Clean surgical incision, pink edges
  - No redness spreading beyond wound edge
  - Skin color looks normal around wound
  - Dry wound with no discharge
  - Scab forming normally

MILD_RISK (YELLOW - Monitor):
  - Slight redness around wound (1-2cm)
  - Minor swelling
  - Slight warmth/pink area
  - Small amount of clear discharge
  - Wound edges slightly puffy

INFECTED (RED - Seek Doctor):
  - Heavy redness spreading far from wound
  - Yellow/green pus or discharge
  - Wound is very swollen/hot
  - Dark discoloration around wound
  - Wound smells bad
  - Red streaks going away from wound
  - Wound is getting bigger instead of smaller

PUT IMAGES IN THESE FOLDERS:
  dataset/train/healthy/     (80% of healthy images)
  dataset/train/mild_risk/   (80% of mild risk images)
  dataset/train/infected/    (80% of infected images)
  dataset/val/healthy/       (20% of healthy images)
  dataset/val/mild_risk/     (20% of mild risk images)
  dataset/val/infected/      (20% of infected images)

Then run: python train_model.py
""")
        print(f"\nSee {readme} for detailed sorting guide!")
        return

    # Split into train/val
    split_train_val(base_dir)

    # Cleanup temp 'all' folder
    shutil.rmtree(base_dir / "all", ignore_errors=True)
    shutil.rmtree(base_dir / "downloads", ignore_errors=True)

    # Print summary
    print_summary(base_dir)


if __name__ == "__main__":
    random.seed(42)
    main()
