"""
WoundWatch - Download ALL 7 Wound Datasets
===========================================
Auto-downloads what it can, gives instructions for manual ones.
Run: python download_all_wounds.py

Datasets:
  1. SATHEESHMA/SurgWound     (HuggingFace - auto)
  2. xuxuxuxuxu/SurgWound     (HuggingFace - auto)
  3. Sonulee/SurgWound         (HuggingFace - auto)
  4. UWM Wound Classification  (GitHub - auto)
  5. UWM Multi-modal Wounds    (GitHub - auto)
  6. Kaggle Wound Segmentation (Kaggle - auto if kaggle CLI installed)
  7. Roboflow Surgical Wounds  (Roboflow - auto if API key set)
"""

import os, sys, subprocess, shutil, zipfile, io, base64, glob
from pathlib import Path

BASE = Path("wound_data")
BASE.mkdir(exist_ok=True)

def count_images(folder):
    folder = Path(folder)
    if not folder.exists(): return 0
    c = 0
    for ext in ['*.jpg','*.jpeg','*.png','*.bmp','*.tiff','*.gif']:
        c += len(list(folder.rglob(ext)))
    return c

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

# Ensure dependencies
for pkg in ["datasets", "huggingface_hub", "Pillow", "requests"]:
    try:
        __import__(pkg.lower().replace("-","_").split("[")[0])
    except ImportError:
        print(f"Installing {pkg}...")
        install(pkg)

import requests
from PIL import Image

results = {}

# ============================================================
# DATASET 1: SATHEESHMA/SurgWound (HuggingFace)
# ============================================================
ds_dir = BASE / "surgwound"
print("=" * 60)
print("1/7  SATHEESHMA/SurgWound (HuggingFace)")
print("=" * 60)

if count_images(ds_dir) >= 100:
    c = count_images(ds_dir)
    print(f"  Already downloaded! ({c} images)")
    results["1. SurgWound"] = f"{c} images ✅"
else:
    try:
        from datasets import load_dataset
        ds_dir.mkdir(parents=True, exist_ok=True)
        print("  Downloading from HuggingFace...")
        ds = load_dataset("SATHEESHMA/SurgWound", split="train")
        print(f"  Found {len(ds)} samples, columns: {ds.column_names}")

        saved = 0
        for i, sample in enumerate(ds):
            try:
                img = None
                for key in sample.keys():
                    val = sample[key]
                    if isinstance(val, Image.Image):
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
                if img is None: continue
                img.convert("RGB").save(ds_dir / f"surgwound_{i:05d}.jpg", "JPEG", quality=95)
                saved += 1
                if saved % 500 == 0: print(f"    {saved} saved...")
            except: continue

        print(f"  Done: {saved} images")
        results["1. SurgWound"] = f"{saved} images ✅"
    except Exception as e:
        print(f"  Failed: {e}")
        results["1. SurgWound"] = f"FAILED ❌ ({e})"

# ============================================================
# DATASET 2: xuxuxuxuxu/SurgWound (HuggingFace)
# ============================================================
ds_dir = BASE / "xuxuxuxuxu_SurgWound"
print(f"\n{'='*60}")
print("2/7  xuxuxuxuxu/SurgWound (HuggingFace)")
print("=" * 60)

if count_images(ds_dir) >= 50:
    c = count_images(ds_dir)
    print(f"  Already downloaded! ({c} images)")
    results["2. xuxuxuxuxu/SurgWound"] = f"{c} images ✅"
else:
    try:
        from datasets import load_dataset
        ds_dir.mkdir(parents=True, exist_ok=True)
        print("  Downloading...")
        ds = load_dataset("xuxuxuxuxu/SurgWound", split="train", streaming=True)

        saved = 0
        for i, sample in enumerate(ds):
            if saved >= 5000: break
            try:
                img = None
                for key in sample.keys():
                    val = sample[key]
                    if isinstance(val, Image.Image):
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
                img.convert("RGB").save(ds_dir / f"xuxu_{i:05d}.jpg", "JPEG", quality=95)
                saved += 1
                if saved % 500 == 0: print(f"    {saved} saved...")
            except: continue

        if saved > 0:
            print(f"  Done: {saved} images")
            results["2. xuxuxuxuxu/SurgWound"] = f"{saved} images ✅"
        else:
            shutil.rmtree(ds_dir, ignore_errors=True)
            print("  No images found")
            results["2. xuxuxuxuxu/SurgWound"] = "0 images ⚠️"
    except Exception as e:
        print(f"  Failed: {e}")
        results["2. xuxuxuxuxu/SurgWound"] = f"FAILED ❌"

# ============================================================
# DATASET 3: Sonulee/SurgWound (HuggingFace)
# ============================================================
ds_dir = BASE / "Sonulee_SurgWound"
print(f"\n{'='*60}")
print("3/7  Sonulee/SurgWound (HuggingFace)")
print("=" * 60)

if count_images(ds_dir) >= 50:
    c = count_images(ds_dir)
    print(f"  Already downloaded! ({c} images)")
    results["3. Sonulee/SurgWound"] = f"{c} images ✅"
else:
    try:
        from datasets import load_dataset
        ds_dir.mkdir(parents=True, exist_ok=True)
        print("  Downloading...")
        ds = load_dataset("Sonulee/SurgWound", split="train", streaming=True)

        saved = 0
        for i, sample in enumerate(ds):
            if saved >= 5000: break
            try:
                img = None
                for key in sample.keys():
                    val = sample[key]
                    if isinstance(val, Image.Image):
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
                img.convert("RGB").save(ds_dir / f"sonulee_{i:05d}.jpg", "JPEG", quality=95)
                saved += 1
                if saved % 500 == 0: print(f"    {saved} saved...")
            except: continue

        if saved > 0:
            print(f"  Done: {saved} images")
            results["3. Sonulee/SurgWound"] = f"{saved} images ✅"
        else:
            shutil.rmtree(ds_dir, ignore_errors=True)
            print("  No images found")
            results["3. Sonulee/SurgWound"] = "0 images ⚠️"
    except Exception as e:
        print(f"  Failed: {e}")
        results["3. Sonulee/SurgWound"] = f"FAILED ❌"

# ============================================================
# DATASET 4: UWM Wound Classification (GitHub)
# ============================================================
ds_dir = BASE / "uwm_classification"
print(f"\n{'='*60}")
print("4/7  UWM Wound Classification (GitHub)")
print("=" * 60)

if count_images(ds_dir) >= 50:
    c = count_images(ds_dir)
    print(f"  Already downloaded! ({c} images)")
    results["4. UWM Classification"] = f"{c} images ✅"
else:
    try:
        ds_dir.mkdir(parents=True, exist_ok=True)
        zip_url = "https://github.com/uwm-bigdata/wound-classification/archive/refs/heads/main.zip"
        print(f"  Downloading from GitHub...")
        zip_path = ds_dir / "repo.zip"

        r = requests.get(zip_url, stream=True, timeout=120)
        r.raise_for_status()
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print(f"  Downloaded: {zip_path.stat().st_size / (1024*1024):.1f} MB")

        # Extract
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(ds_dir)
        zip_path.unlink()

        # Find images in extracted content
        img_count = count_images(ds_dir)
        print(f"  Extracted: {img_count} images")

        # If no standard images, check for other formats
        if img_count == 0:
            all_files = list(ds_dir.rglob("*"))
            exts = {}
            for f in all_files:
                if f.is_file():
                    ext = f.suffix.lower()
                    exts[ext] = exts.get(ext, 0) + 1
            print(f"  File types found: {dict(sorted(exts.items(), key=lambda x: -x[1]))}")

            # Check for numpy/pickle files with images
            for ext in ['.npy', '.npz', '.pkl', '.h5', '.mat']:
                found = list(ds_dir.rglob(f"*{ext}"))
                if found:
                    print(f"  Found {len(found)} {ext} files — extracting images...")
                    try:
                        extracted = 0
                        for npy_file in found:
                            if ext == '.npy':
                                data = np.load(str(npy_file), allow_pickle=True)
                                if hasattr(data, 'shape') and len(data.shape) >= 3:
                                    for j in range(min(len(data), 2000)):
                                        try:
                                            img_arr = data[j]
                                            if img_arr.max() <= 1.0:
                                                img_arr = (img_arr * 255).astype(np.uint8)
                                            Image.fromarray(img_arr).save(
                                                ds_dir / f"uwm_cls_{extracted:05d}.jpg", "JPEG", quality=95
                                            )
                                            extracted += 1
                                        except: continue
                            elif ext == '.npz':
                                data = np.load(str(npy_file), allow_pickle=True)
                                for key in data.files:
                                    arr = data[key]
                                    if hasattr(arr, 'shape') and len(arr.shape) >= 3:
                                        for j in range(min(len(arr), 2000)):
                                            try:
                                                img_arr = arr[j]
                                                if img_arr.max() <= 1.0:
                                                    img_arr = (img_arr * 255).astype(np.uint8)
                                                Image.fromarray(img_arr).save(
                                                    ds_dir / f"uwm_cls_{extracted:05d}.jpg", "JPEG", quality=95
                                                )
                                                extracted += 1
                                            except: continue
                        if extracted > 0:
                            print(f"  Extracted {extracted} images from {ext} files")
                            img_count = extracted
                    except Exception as e:
                        print(f"  Could not extract from {ext}: {e}")

        results["4. UWM Classification"] = f"{img_count} images {'✅' if img_count > 0 else '⚠️'}"
    except Exception as e:
        print(f"  Failed: {e}")
        results["4. UWM Classification"] = f"FAILED ❌"

# ============================================================
# DATASET 5: UWM Multi-modal Wounds (GitHub)
# ============================================================
ds_dir = BASE / "uwm_multimodal"
print(f"\n{'='*60}")
print("5/7  UWM Multi-modal Wounds (GitHub)")
print("=" * 60)

if count_images(ds_dir) >= 50:
    c = count_images(ds_dir)
    print(f"  Already downloaded! ({c} images)")
    results["5. UWM Multi-modal"] = f"{c} images ✅"
else:
    try:
        ds_dir.mkdir(parents=True, exist_ok=True)
        zip_url = "https://github.com/uwm-bigdata/Multi-modal-Wound-Classification-using-Images-and-Locations/archive/refs/heads/main.zip"
        print(f"  Downloading from GitHub...")
        zip_path = ds_dir / "repo.zip"

        r = requests.get(zip_url, stream=True, timeout=120)
        r.raise_for_status()
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print(f"  Downloaded: {zip_path.stat().st_size / (1024*1024):.1f} MB")

        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(ds_dir)
        zip_path.unlink()

        img_count = count_images(ds_dir)
        print(f"  Extracted: {img_count} images")

        if img_count == 0:
            all_files = list(ds_dir.rglob("*"))
            exts = {}
            for f in all_files:
                if f.is_file():
                    ext = f.suffix.lower()
                    exts[ext] = exts.get(ext, 0) + 1
            print(f"  File types: {dict(sorted(exts.items(), key=lambda x: -x[1]))}")

            # Try extracting from numpy files
            import numpy as np_load
            for ext in ['.npy', '.npz']:
                found = list(ds_dir.rglob(f"*{ext}"))
                if found:
                    print(f"  Found {len(found)} {ext} files — trying extraction...")
                    extracted = 0
                    for npy_file in found[:10]:
                        try:
                            data = np_load.load(str(npy_file), allow_pickle=True)
                            if hasattr(data, 'shape') and len(data.shape) >= 3:
                                for j in range(min(len(data), 2000)):
                                    try:
                                        img_arr = data[j]
                                        if img_arr.ndim >= 2:
                                            if img_arr.max() <= 1.0:
                                                img_arr = (img_arr * 255).astype(np.uint8)
                                            if img_arr.ndim == 2:
                                                img_arr = np.stack([img_arr]*3, axis=-1)
                                            Image.fromarray(img_arr).save(
                                                ds_dir / f"uwm_mm_{extracted:05d}.jpg", "JPEG", quality=95
                                            )
                                            extracted += 1
                                    except: continue
                        except: continue
                    if extracted > 0:
                        print(f"  Extracted {extracted} images")
                        img_count = extracted

        results["5. UWM Multi-modal"] = f"{img_count} images {'✅' if img_count > 0 else '⚠️'}"
    except Exception as e:
        print(f"  Failed: {e}")
        results["5. UWM Multi-modal"] = f"FAILED ❌"

# ============================================================
# DATASET 6: Kaggle Wound Segmentation (2,760 images)
# ============================================================
ds_dir = BASE / "kaggle_wounds"
print(f"\n{'='*60}")
print("6/7  Kaggle Wound Segmentation (2,760 images)")
print("=" * 60)

if count_images(ds_dir) >= 100:
    c = count_images(ds_dir)
    print(f"  Already downloaded! ({c} images)")
    results["6. Kaggle Wounds"] = f"{c} images ✅"
else:
    # Try kaggle CLI
    kaggle_ok = False
    try:
        import kaggle
        kaggle_ok = True
    except:
        try:
            result = subprocess.run(["kaggle", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                kaggle_ok = True
        except:
            pass

    if kaggle_ok:
        try:
            ds_dir.mkdir(parents=True, exist_ok=True)
            print("  Downloading via Kaggle CLI...")
            subprocess.run([
                sys.executable, "-m", "kaggle", "datasets", "download",
                "-d", "leoscode/wound-segmentation-images",
                "-p", str(ds_dir), "--unzip"
            ], check=True)
            img_count = count_images(ds_dir)
            print(f"  Done: {img_count} images")
            results["6. Kaggle Wounds"] = f"{img_count} images ✅"
        except Exception as e:
            print(f"  Kaggle download failed: {e}")
            results["6. Kaggle Wounds"] = "MANUAL DOWNLOAD NEEDED ⬇️"
    else:
        print("  Kaggle CLI not configured.")
        print("\n  AUTO-SETUP:")
        print("    pip install kaggle")
        print("    Go to kaggle.com > Settings > API > Create New Token")
        print("    Save kaggle.json to C:\\Users\\<you>\\.kaggle\\kaggle.json")
        print("    Then re-run this script")
        print("\n  OR MANUAL DOWNLOAD:")
        print("    1. Go to: https://www.kaggle.com/datasets/leoscode/wound-segmentation-images")
        print("    2. Click 'Download' (2,760 images)")
        print(f"    3. Extract to: {ds_dir.absolute()}")
        results["6. Kaggle Wounds"] = "MANUAL DOWNLOAD NEEDED ⬇️"

# ============================================================
# DATASET 7: Roboflow Surgical Wound Classification (708 images)
# ============================================================
ds_dir = BASE / "roboflow_surgical"
print(f"\n{'='*60}")
print("7/7  Roboflow Surgical Wound Classification (708 images)")
print("=" * 60)

if count_images(ds_dir) >= 50:
    c = count_images(ds_dir)
    print(f"  Already downloaded! ({c} images)")
    results["7. Roboflow Surgical"] = f"{c} images ✅"
else:
    # Try Roboflow API
    rf_key = os.environ.get("ROBOFLOW_API_KEY", "")

    if rf_key:
        try:
            from roboflow import Roboflow
            ds_dir.mkdir(parents=True, exist_ok=True)
            print("  Downloading via Roboflow API...")
            rf = Roboflow(api_key=rf_key)
            project = rf.workspace().project("surgical-wound-classification")
            dataset = project.version(1).download("folder", location=str(ds_dir))
            img_count = count_images(ds_dir)
            print(f"  Done: {img_count} images")
            results["7. Roboflow Surgical"] = f"{img_count} images ✅"
        except Exception as e:
            print(f"  Roboflow download failed: {e}")
            results["7. Roboflow Surgical"] = "MANUAL DOWNLOAD NEEDED ⬇️"
    else:
        print("  Roboflow API key not set.")
        print("\n  OPTION 1 — Free API download:")
        print("    1. Go to: https://universe.roboflow.com/wounddetection-lvlph/surgical-wound-classification")
        print("    2. Sign up free, get API key")
        print("    3. Set: set ROBOFLOW_API_KEY=your_key_here")
        print("    4. Re-run this script")
        print("\n  OPTION 2 — Manual download:")
        print("    1. Go to the Roboflow link above")
        print("    2. Click 'Download Dataset' > Format: Folder")
        print(f"    3. Extract to: {ds_dir.absolute()}")
        results["7. Roboflow Surgical"] = "MANUAL DOWNLOAD NEEDED ⬇️"

# ============================================================
# Also try extra HuggingFace wound datasets
# ============================================================
print(f"\n{'='*60}")
print("BONUS: Trying extra HuggingFace wound datasets...")
print("=" * 60)

extra_hf = [
    ("hongrui/miccai_wound", "miccai_wound"),
    ("keremberke/wound-detection", "wound_detection"),
]

for ds_name, folder_name in extra_hf:
    ds_dir = BASE / folder_name
    if count_images(ds_dir) >= 50:
        print(f"  {ds_name}: Already have {count_images(ds_dir)} images")
        continue
    try:
        from datasets import load_dataset
        ds_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Trying {ds_name}...")
        ds = load_dataset(ds_name, split="train", streaming=True)
        saved = 0
        for i, sample in enumerate(ds):
            if saved >= 3000: break
            try:
                img = None
                for key in sample.keys():
                    val = sample[key]
                    if isinstance(val, Image.Image):
                        img = val; break
                    if isinstance(val, dict) and "bytes" in val and val["bytes"]:
                        img = Image.open(io.BytesIO(val["bytes"])); break
                if img is None: continue
                img.convert("RGB").save(ds_dir / f"{folder_name}_{i:05d}.jpg", "JPEG", quality=95)
                saved += 1
                if saved % 500 == 0: print(f"    {saved} saved...")
            except: continue
        if saved > 0:
            print(f"  {ds_name}: {saved} images ✅")
        else:
            shutil.rmtree(ds_dir, ignore_errors=True)
            print(f"  {ds_name}: No extractable images")
    except Exception as e:
        shutil.rmtree(ds_dir, ignore_errors=True)
        print(f"  {ds_name}: {e}")

# ============================================================
# FINAL SUMMARY
# ============================================================
print(f"\n{'='*60}")
print("DOWNLOAD SUMMARY")
print("=" * 60)

for name, status in results.items():
    print(f"  {name}: {status}")

# Count total
grand_total = count_images(BASE)
print(f"\n  GRAND TOTAL: {grand_total} images in wound_data/")

# Per-folder breakdown
print(f"\n  Folder breakdown:")
for sub in sorted(BASE.iterdir()):
    if sub.is_dir():
        c = count_images(sub)
        if c > 0:
            print(f"    {sub.name}: {c}")

if grand_total >= 3000:
    print(f"\n  Dataset ready for training!")
    print(f"  Next: Fix numpy, then run train_wounds.py")
    print(f"    pip install numpy==1.26.4")
    print(f"    python train_wounds.py")
elif grand_total >= 500:
    print(f"\n  Minimum viable dataset ({grand_total} images).")
    print(f"  Will augment to 20K+ during training.")
    print(f"  For better accuracy, also download Kaggle + Roboflow manually.")
else:
    print(f"\n  Need more images! Download Kaggle + Roboflow manually.")
