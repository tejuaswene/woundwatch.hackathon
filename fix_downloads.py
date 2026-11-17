"""
WoundWatch - Fix Downloads & Count All Images
Run AFTER: pip install numpy>=2.0
Then: python fix_downloads.py
"""

import os, sys, subprocess, zipfile, shutil, io, base64, glob
from pathlib import Path

BASE = Path("wound_data")

def count_images(folder):
    count = 0
    folder = Path(folder)
    if not folder.exists(): return 0
    for ext in ['*.jpg','*.jpeg','*.png','*.bmp','*.tiff','*.tif','*.gif']:
        count += len(list(folder.rglob(ext)))
    return count

# ============================================================
# Fix 1: Check UWM repos - find images inside nested folders
# ============================================================
print("=" * 60)
print("FIX 1: Scanning UWM repos for images...")
print("=" * 60)

uwm_dirs = [
    BASE / "kaggle_wounds" / "uwm_wounds",
    BASE / "kaggle_wounds" / "uwm_multimodal",
    BASE / "kaggle_wounds" / "uwm_localization",
]

for d in uwm_dirs:
    if not d.exists():
        print(f"\n  {d.name}: Not found, skipping")
        continue

    # List all files to understand structure
    print(f"\n  {d.name}:")
    all_files = list(d.rglob("*"))
    print(f"    Total files: {len(all_files)}")

    # Show file extensions
    exts = {}
    for f in all_files:
        if f.is_file():
            ext = f.suffix.lower()
            exts[ext] = exts.get(ext, 0) + 1
    print(f"    File types: {dict(sorted(exts.items(), key=lambda x: -x[1]))}")

    # Count images
    img_count = count_images(d)
    print(f"    Images found: {img_count}")

    # If no standard images, check for other formats
    if img_count == 0:
        # Check if images are in .npy, .pkl, .h5, or other formats
        for ext in ['.npy', '.pkl', '.h5', '.hdf5', '.mat', '.npz', '.csv']:
            files = list(d.rglob(f"*{ext}"))
            if files:
                print(f"    Found {len(files)} {ext} files - images may be stored here")

        # Show first few directories
        dirs = [x for x in d.rglob("*") if x.is_dir()]
        if dirs:
            print(f"    Subdirectories:")
            for dd in dirs[:10]:
                rel = dd.relative_to(d)
                print(f"      {rel}/")

# ============================================================
# Fix 2: Download SurgWound (fix NumPy issue)
# ============================================================
print(f"\n{'=' * 60}")
print("FIX 2: Downloading SurgWound...")
print("=" * 60)

ds1_dir = BASE / "surgwound"
if count_images(ds1_dir) > 100:
    c = count_images(ds1_dir)
    print(f"  Already downloaded! ({c} images)")
else:
    try:
        import numpy as np
        print(f"  NumPy version: {np.__version__}")
        if int(np.__version__.split('.')[0]) < 2:
            print("  ERROR: NumPy must be >= 2.0")
            print("  Run: pip install numpy>=2.0")
            print("  Then re-run this script")
        else:
            from datasets import load_dataset
            from PIL import Image

            ds1_dir.mkdir(parents=True, exist_ok=True)
            print("  Loading SurgWound from HuggingFace...")
            ds = load_dataset("SATHEESHMA/SurgWound", split="train")
            print(f"  Found {len(ds)} samples")
            print(f"  Columns: {ds.column_names}")

            # Debug first sample
            sample = ds[0]
            print(f"  Sample keys & types:")
            for key, val in sample.items():
                if isinstance(val, Image.Image):
                    print(f"    {key}: PIL Image {val.size}")
                elif isinstance(val, str) and len(val) > 200:
                    print(f"    {key}: str (len={len(val)}) starts with: {val[:40]}...")
                elif isinstance(val, dict):
                    print(f"    {key}: dict keys={list(val.keys())}")
                elif isinstance(val, bytes):
                    print(f"    {key}: bytes (len={len(val)})")
                else:
                    print(f"    {key}: {type(val).__name__} = {str(val)[:60]}")

            saved = 0
            errors = 0
            for i, sample in enumerate(ds):
                try:
                    img = None
                    for key in sample.keys():
                        val = sample[key]

                        # PIL Image
                        if isinstance(val, Image.Image):
                            img = val; break

                        # Dict with bytes
                        if isinstance(val, dict) and "bytes" in val and val["bytes"]:
                            img = Image.open(io.BytesIO(val["bytes"])); break

                        # Raw bytes
                        if isinstance(val, bytes) and len(val) > 100:
                            try: img = Image.open(io.BytesIO(val)); break
                            except: pass

                        # BASE64 STRING
                        if isinstance(val, str) and len(val) > 200:
                            try:
                                raw = val
                                if "," in raw[:100]:
                                    raw = raw.split(",", 1)[1]
                                decoded = base64.b64decode(raw)
                                if len(decoded) > 100:
                                    img = Image.open(io.BytesIO(decoded)); break
                            except: pass

                    if img is None:
                        errors += 1
                        if errors <= 3:
                            print(f"    Sample {i}: Could not extract image")
                        continue

                    img = img.convert("RGB")
                    img.save(ds1_dir / f"surgwound_{i:05d}.jpg", "JPEG", quality=95)
                    saved += 1
                    if saved % 500 == 0:
                        print(f"    {saved} images saved...")
                except Exception as e:
                    errors += 1
                    if errors <= 5: print(f"    Error {i}: {e}")

            print(f"  SurgWound: {saved} saved, {errors} errors")
    except ImportError as e:
        print(f"  Import error: {e}")
        print("  Run: pip install numpy>=2.0 datasets huggingface_hub Pillow")
    except Exception as e:
        print(f"  Error: {e}")

# ============================================================
# Fix 3: Try additional HuggingFace datasets
# ============================================================
print(f"\n{'=' * 60}")
print("FIX 3: Trying extra HuggingFace wound datasets...")
print("=" * 60)

hf_datasets = [
    "xuxuxuxuxu/SurgWound",
    "Sonulee/SurgWound",
]

for ds_name in hf_datasets:
    folder_name = ds_name.replace("/", "_")
    ds_dir = BASE / folder_name
    if count_images(ds_dir) > 50:
        print(f"  {ds_name}: Already downloaded ({count_images(ds_dir)} images)")
        continue

    try:
        from datasets import load_dataset
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
                img = img.convert("RGB")
                img.save(ds_dir / f"{folder_name}_{i:05d}.jpg", "JPEG", quality=95)
                saved += 1
                if saved % 500 == 0:
                    print(f"    {saved} images...")
            except: continue

        if saved > 0:
            print(f"  {ds_name}: {saved} images!")
        else:
            shutil.rmtree(ds_dir, ignore_errors=True)
            print(f"  {ds_name}: No images, skipped")
    except Exception as e:
        print(f"  {ds_name}: {e}")
        shutil.rmtree(ds_dir, ignore_errors=True)

# ============================================================
# FINAL SUMMARY
# ============================================================
print(f"\n{'=' * 60}")
print("FINAL IMAGE COUNT")
print("=" * 60)

grand_total = 0
for sub in sorted(BASE.rglob("*")):
    if sub.is_dir():
        c = count_images(sub)
        if c > 0:
            # Only show leaf folders with images
            has_child_with_images = False
            for child in sub.iterdir():
                if child.is_dir() and count_images(child) > 0:
                    has_child_with_images = True
                    break
            if not has_child_with_images:
                rel = sub.relative_to(BASE)
                print(f"  {rel}: {c} images")

grand_total = count_images(BASE)
print(f"\n  GRAND TOTAL: {grand_total} images")

if grand_total >= 3000:
    print(f"\n  Ready for training! Run train_local_full.py next.")
elif grand_total >= 500:
    print(f"\n  Minimum viable dataset. Will augment to 20K+.")
    print(f"  Download more from Kaggle/Roboflow for better accuracy.")
else:
    print(f"\n  Need more images. Download manually:")
    print(f"  - Kaggle: https://www.kaggle.com/datasets/leoscode/wound-segmentation-images")
    print(f"  - Roboflow: https://universe.roboflow.com/wounddetection-lvlph/surgical-wound-classification")
