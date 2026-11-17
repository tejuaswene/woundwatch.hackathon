"""
WoundWatch - Download ALL wound image datasets
Run: python download_datasets.py
Downloads everything into wound_data\ folder
"""

import os, sys, subprocess, zipfile, shutil, time
from pathlib import Path

BASE = Path("wound_data")
BASE.mkdir(exist_ok=True)

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

# Ensure required packages
for pkg in ["requests", "datasets", "huggingface_hub", "gdown"]:
    try:
        __import__(pkg)
    except ImportError:
        print(f"Installing {pkg}...")
        install(pkg)

import requests

def download_file(url, save_path, desc=""):
    """Download a file with progress"""
    print(f"\n  Downloading: {desc or url}")
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        downloaded = 0
        with open(save_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded * 100 / total
                    mb = downloaded / (1024*1024)
                    print(f"\r  {mb:.1f} MB ({pct:.0f}%)", end="", flush=True)
        print(f"\n  Saved: {save_path} ({downloaded/(1024*1024):.1f} MB)")
        return True
    except Exception as e:
        print(f"\n  ERROR: {e}")
        return False

def download_github_repo(repo_url, save_dir, desc=""):
    """Download GitHub repo as ZIP"""
    # Convert repo URL to ZIP download URL
    # github.com/user/repo -> github.com/user/repo/archive/refs/heads/main.zip
    repo_url = repo_url.rstrip("/")
    zip_url = f"{repo_url}/archive/refs/heads/main.zip"
    zip_path = Path(save_dir) / "repo.zip"

    print(f"\n  Downloading GitHub: {desc or repo_url}")
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    success = download_file(zip_url, zip_path, desc)
    if not success:
        # Try master branch
        zip_url = f"{repo_url}/archive/refs/heads/master.zip"
        success = download_file(zip_url, zip_path, f"{desc} (master branch)")

    if success and zip_path.exists():
        print(f"  Extracting...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(save_dir)
            zip_path.unlink()
            print(f"  Extracted to {save_dir}")
            return True
        except Exception as e:
            print(f"  Extract error: {e}")
    return False

def count_images(folder):
    """Count image files in folder recursively"""
    count = 0
    folder = Path(folder)
    if not folder.exists():
        return 0
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif']:
        count += len(list(folder.rglob(ext)))
    return count

# ============================================================
print("=" * 60)
print("WoundWatch - Downloading ALL Wound Datasets")
print("=" * 60)
print(f"Save location: {BASE.resolve()}")
print()

total_datasets = 0
total_images = 0

# ============================================================
# Dataset 1: SurgWound from HuggingFace (3,915 images)
# ============================================================
print("\n" + "=" * 60)
print("DATASET 1: SurgWound (HuggingFace) - ~3,915 surgical wound images")
print("=" * 60)

ds1_dir = BASE / "surgwound"
if count_images(ds1_dir) > 100:
    c = count_images(ds1_dir)
    print(f"  Already downloaded! ({c} images)")
    total_images += c
    total_datasets += 1
else:
    try:
        from datasets import load_dataset
        import io, base64
        from PIL import Image

        ds1_dir.mkdir(parents=True, exist_ok=True)
        print("  Loading from HuggingFace (this may take a few minutes)...")
        ds = load_dataset("SATHEESHMA/SurgWound", split="train")
        print(f"  Found {len(ds)} samples")

        saved = 0
        errors = 0
        for i, sample in enumerate(ds):
            try:
                img = None
                for key in sample.keys():
                    val = sample[key]
                    if hasattr(val, 'save') and hasattr(val, 'convert'):  # PIL Image
                        img = val; break
                    if isinstance(val, dict) and "bytes" in val and val["bytes"]:
                        img = Image.open(io.BytesIO(val["bytes"])); break
                    if isinstance(val, bytes) and len(val) > 100:
                        try: img = Image.open(io.BytesIO(val)); break
                        except: pass
                    if isinstance(val, str) and len(val) > 200:
                        try:
                            raw = val
                            if "," in raw[:100]: raw = raw.split(",", 1)[1]
                            decoded = base64.b64decode(raw)
                            if len(decoded) > 100:
                                img = Image.open(io.BytesIO(decoded)); break
                        except: pass

                if img is None:
                    errors += 1; continue

                img = img.convert("RGB")
                img.save(ds1_dir / f"surgwound_{i:05d}.jpg", "JPEG", quality=95)
                saved += 1
                if saved % 500 == 0:
                    print(f"  {saved} images saved...")
            except:
                errors += 1

        print(f"  Done! {saved} images saved, {errors} errors")
        total_images += saved
        total_datasets += 1
    except Exception as e:
        print(f"  ERROR: {e}")
        print("  Install: pip install datasets huggingface_hub Pillow")

# ============================================================
# Dataset 2: WoundsDB - Chronic Wound Database (needs registration)
# ============================================================
print("\n" + "=" * 60)
print("DATASET 2: WoundsDB (chronicwounddatabase.eu)")
print("=" * 60)

ds2_dir = BASE / "woundsdb"
if count_images(ds2_dir) > 10:
    c = count_images(ds2_dir)
    print(f"  Already downloaded! ({c} images)")
    total_images += c
    total_datasets += 1
else:
    ds2_dir.mkdir(parents=True, exist_ok=True)
    print("  *** MANUAL DOWNLOAD REQUIRED ***")
    print("  1. Go to: https://chronicwounddatabase.eu/Download")
    print("  2. Register (if not done)")
    print("  3. Download 'Processed data' (336 MB)")
    print("  4. Download 'Description data' (21 kB)")
    print(f"  5. Extract both ZIPs into: {ds2_dir.resolve()}")
    print()

    # Check if user already downloaded
    for zf in ds2_dir.glob("*.zip"):
        print(f"  Found ZIP: {zf.name} - Extracting...")
        try:
            with zipfile.ZipFile(zf, 'r') as z:
                z.extractall(ds2_dir)
            print(f"  Extracted!")
        except Exception as e:
            print(f"  Error: {e}")

    c = count_images(ds2_dir)
    if c > 0:
        print(f"  Found {c} images!")
        total_images += c
        total_datasets += 1

# ============================================================
# Dataset 3: Kaggle Wound Segmentation (2,760 images)
# ============================================================
print("\n" + "=" * 60)
print("DATASET 3: Kaggle Wound Segmentation (2,760 images)")
print("=" * 60)

ds3_dir = BASE / "kaggle_wounds" / "wound_segmentation"
if count_images(ds3_dir) > 100:
    c = count_images(ds3_dir)
    print(f"  Already downloaded! ({c} images)")
    total_images += c
    total_datasets += 1
else:
    ds3_dir.mkdir(parents=True, exist_ok=True)

    # Try kaggle API first
    try:
        import kaggle
        print("  Downloading via Kaggle API...")
        subprocess.run([
            sys.executable, "-m", "kaggle", "datasets", "download",
            "-d", "leoscode/wound-segmentation-images",
            "-p", str(ds3_dir), "--unzip"
        ], check=True)
        c = count_images(ds3_dir)
        print(f"  Done! {c} images")
        total_images += c
        total_datasets += 1
    except:
        print("  *** MANUAL DOWNLOAD REQUIRED ***")
        print("  1. Go to: https://www.kaggle.com/datasets/leoscode/wound-segmentation-images")
        print("  2. Login to Kaggle")
        print("  3. Click 'Download' button (top right)")
        print(f"  4. Extract ZIP into: {ds3_dir.resolve()}")
        print()
        print("  OR install Kaggle API:")
        print("    pip install kaggle")
        print("    Put kaggle.json in C:\\Users\\276ro\\.kaggle\\")
        print("    Re-run this script")

        # Check for manual downloads
        for zf in ds3_dir.glob("*.zip"):
            print(f"  Found ZIP: {zf.name} - Extracting...")
            try:
                with zipfile.ZipFile(zf, 'r') as z:
                    z.extractall(ds3_dir)
            except: pass
        c = count_images(ds3_dir)
        if c > 0:
            print(f"  Found {c} images!")
            total_images += c
            total_datasets += 1

# ============================================================
# Dataset 4: UWM Wound Classification (400 images - has SURGICAL!)
# ============================================================
print("\n" + "=" * 60)
print("DATASET 4: UWM Wound Classification (400 images)")
print("  Types: surgical, venous, diabetic, pressure")
print("=" * 60)

ds4_dir = BASE / "kaggle_wounds" / "uwm_wounds"
if count_images(ds4_dir) > 50:
    c = count_images(ds4_dir)
    print(f"  Already downloaded! ({c} images)")
    total_images += c
    total_datasets += 1
else:
    success = download_github_repo(
        "https://github.com/uwm-bigdata/wound_classification",
        str(ds4_dir),
        "UWM Wound Classification"
    )
    if success:
        c = count_images(ds4_dir)
        print(f"  Found {c} images!")
        total_images += c
        total_datasets += 1

# ============================================================
# Dataset 5: UWM Multi-modal Wound (730 images)
# ============================================================
print("\n" + "=" * 60)
print("DATASET 5: UWM Multi-modal Wound (730 images)")
print("=" * 60)

ds5_dir = BASE / "kaggle_wounds" / "uwm_multimodal"
if count_images(ds5_dir) > 50:
    c = count_images(ds5_dir)
    print(f"  Already downloaded! ({c} images)")
    total_images += c
    total_datasets += 1
else:
    success = download_github_repo(
        "https://github.com/uwm-bigdata/wound-classification-using-images-and-locations",
        str(ds5_dir),
        "UWM Multi-modal Wound"
    )
    if success:
        c = count_images(ds5_dir)
        print(f"  Found {c} images!")
        total_images += c
        total_datasets += 1

# ============================================================
# Dataset 6: UWM Wound Localization (1,000 images)
# ============================================================
print("\n" + "=" * 60)
print("DATASET 6: UWM Wound Localization (1,000 images)")
print("=" * 60)

ds6_dir = BASE / "kaggle_wounds" / "uwm_localization"
if count_images(ds6_dir) > 50:
    c = count_images(ds6_dir)
    print(f"  Already downloaded! ({c} images)")
    total_images += c
    total_datasets += 1
else:
    success = download_github_repo(
        "https://github.com/uwm-bigdata/wound_localization",
        str(ds6_dir),
        "UWM Wound Localization"
    )
    if success:
        c = count_images(ds6_dir)
        print(f"  Found {c} images!")
        total_images += c
        total_datasets += 1

# ============================================================
# Dataset 7: Roboflow Surgical Wound (708 images)
# ============================================================
print("\n" + "=" * 60)
print("DATASET 7: Roboflow Surgical Wound Classification (708 images)")
print("  Classes: clean, clean-contaminated, contaminated, infected")
print("=" * 60)

ds7_dir = BASE / "kaggle_wounds" / "roboflow_surgical"
if count_images(ds7_dir) > 50:
    c = count_images(ds7_dir)
    print(f"  Already downloaded! ({c} images)")
    total_images += c
    total_datasets += 1
else:
    ds7_dir.mkdir(parents=True, exist_ok=True)
    print("  *** MANUAL DOWNLOAD REQUIRED ***")
    print("  1. Go to: https://universe.roboflow.com/wounddetection-lvlph/surgical-wound-classification")
    print("  2. Click 'Download Dataset' (free account needed)")
    print("  3. Format: select 'Folder Structure'")
    print(f"  4. Extract into: {ds7_dir.resolve()}")

    for zf in ds7_dir.glob("*.zip"):
        print(f"  Found ZIP: {zf.name} - Extracting...")
        try:
            with zipfile.ZipFile(zf, 'r') as z:
                z.extractall(ds7_dir)
        except: pass
    c = count_images(ds7_dir)
    if c > 0:
        print(f"  Found {c} images!")
        total_images += c
        total_datasets += 1

# ============================================================
# BONUS: Try additional HuggingFace wound datasets
# ============================================================
print("\n" + "=" * 60)
print("BONUS: Trying extra HuggingFace wound datasets...")
print("=" * 60)

bonus_datasets = [
    ("xuxuxuxuxu/SurgWound", "surgwound_v2"),
    ("Sonulee/SurgWound", "surgwound_sonulee"),
]

for ds_name, folder_name in bonus_datasets:
    ds_dir = BASE / folder_name
    if count_images(ds_dir) > 50:
        c = count_images(ds_dir)
        print(f"  {ds_name}: Already downloaded ({c} images)")
        total_images += c
        total_datasets += 1
        continue

    try:
        from datasets import load_dataset
        import io, base64
        from PIL import Image

        ds_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n  Trying {ds_name}...")
        ds = load_dataset(ds_name, split="train", streaming=True)

        saved = 0
        for i, sample in enumerate(ds):
            if saved >= 5000: break
            try:
                img = None
                for key in sample.keys():
                    val = sample[key]
                    if hasattr(val, 'save') and hasattr(val, 'convert'):
                        img = val; break
                    if isinstance(val, dict) and "bytes" in val and val["bytes"]:
                        img = Image.open(io.BytesIO(val["bytes"])); break
                    if isinstance(val, str) and len(val) > 200:
                        try:
                            raw = val
                            if "," in raw[:100]: raw = raw.split(",", 1)[1]
                            decoded = base64.b64decode(raw)
                            if len(decoded) > 100:
                                img = Image.open(io.BytesIO(decoded)); break
                        except: pass

                if img is None: continue
                img = img.convert("RGB")
                img.save(ds_dir / f"{folder_name}_{i:05d}.jpg", "JPEG", quality=95)
                saved += 1
                if saved % 500 == 0:
                    print(f"    {saved} images...")
            except: continue

        if saved > 0:
            print(f"  {ds_name}: {saved} images saved!")
            total_images += saved
            total_datasets += 1
        else:
            shutil.rmtree(ds_dir, ignore_errors=True)
            print(f"  {ds_name}: No images found, skipped")
    except Exception as e:
        print(f"  {ds_name}: Failed - {e}")
        shutil.rmtree(ds_dir, ignore_errors=True)

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("DOWNLOAD SUMMARY")
print("=" * 60)

grand_total = 0
for folder in BASE.rglob("*"):
    pass  # just traversing

print(f"\nImages per folder:")
for sub in sorted(BASE.iterdir()):
    if sub.is_dir():
        c = count_images(sub)
        grand_total += c
        status = "OK" if c > 0 else "EMPTY - download manually!"
        print(f"  {sub.name}: {c} images [{status}]")

print(f"\n  GRAND TOTAL: {grand_total} real wound images")
print(f"  Datasets downloaded: {total_datasets}")

if grand_total < 5000:
    print(f"\n  You need to manually download the datasets marked EMPTY above.")
    print(f"  After downloading, put the ZIPs in the correct folders and re-run this script.")
else:
    print(f"\n  Good! After augmentation this will become 20,000+ images.")
    print(f"\n  Next step: Run train_local_full.py to start training!")

# Check which need manual download
print("\n" + "=" * 60)
print("MANUAL DOWNLOADS STILL NEEDED:")
print("=" * 60)

manual = []
if count_images(BASE / "woundsdb") == 0:
    manual.append(("WoundsDB", "https://chronicwounddatabase.eu/Download", str(BASE / "woundsdb")))
if count_images(BASE / "kaggle_wounds" / "wound_segmentation") == 0:
    manual.append(("Kaggle Wounds", "https://www.kaggle.com/datasets/leoscode/wound-segmentation-images", str(BASE / "kaggle_wounds" / "wound_segmentation")))
if count_images(BASE / "kaggle_wounds" / "roboflow_surgical") == 0:
    manual.append(("Roboflow Surgical", "https://universe.roboflow.com/wounddetection-lvlph/surgical-wound-classification", str(BASE / "kaggle_wounds" / "roboflow_surgical")))

if manual:
    for name, url, path in manual:
        print(f"\n  {name}:")
        print(f"    URL: {url}")
        print(f"    Save to: {path}")
else:
    print("  None! All datasets downloaded successfully.")

print("\n" + "=" * 60)
print("DONE!")
print("=" * 60)
