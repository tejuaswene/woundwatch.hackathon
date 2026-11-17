"""
WoundWatch - Download ALL Wound Datasets (FIXED)
=================================================
Fixes: pyarrow/numpy conflict, GitHub URLs, error handling
Run: python download_all_wounds_v2.py
"""

import os, sys, subprocess, shutil, zipfile, io, base64
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

def pip_install(pkg):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg],
                   capture_output=True)

# ============================================================
# FIX: Install compatible pyarrow that works with numpy 1.26
# ============================================================
print("Fixing pyarrow compatibility...")
pip_install("pyarrow==14.0.2")  # Works with numpy 1.26.x
pip_install("datasets")
pip_install("huggingface_hub")
pip_install("Pillow")
pip_install("requests")

from PIL import Image
import requests

results = {}

def download_hf_dataset(ds_name, folder_name, label, max_imgs=5000):
    """Download a HuggingFace dataset, handling all image formats."""
    ds_dir = BASE / folder_name

    if count_images(ds_dir) >= 50:
        c = count_images(ds_dir)
        print(f"  Already downloaded! ({c} images)")
        results[label] = f"{c} images ✅"
        return

    try:
        from datasets import load_dataset
        ds_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Downloading {ds_name}...")
        ds = load_dataset(ds_name, split="train", streaming=True)

        saved = 0
        for i, sample in enumerate(ds):
            if saved >= max_imgs: break
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
                img.convert("RGB").save(ds_dir / f"{folder_name}_{i:05d}.jpg", "JPEG", quality=95)
                saved += 1
                if saved % 500 == 0: print(f"    {saved} saved...")
            except: continue

        if saved > 0:
            print(f"  Done: {saved} images")
            results[label] = f"{saved} images ✅"
        else:
            shutil.rmtree(ds_dir, ignore_errors=True)
            print(f"  No extractable images")
            results[label] = "0 images ⚠️"
    except Exception as e:
        print(f"  Failed: {e}")
        results[label] = f"FAILED ❌ ({str(e)[:50]})"


# ============================================================
# 1-3: HuggingFace SurgWound datasets
# ============================================================
print("=" * 60)
print("1/7  SATHEESHMA/SurgWound")
print("=" * 60)
download_hf_dataset("SATHEESHMA/SurgWound", "surgwound", "1. SurgWound")

print(f"\n{'='*60}")
print("2/7  xuxuxuxuxu/SurgWound")
print("=" * 60)
download_hf_dataset("xuxuxuxuxu/SurgWound", "xuxuxuxuxu_SurgWound", "2. xuxuxuxuxu")

print(f"\n{'='*60}")
print("3/7  Sonulee/SurgWound")
print("=" * 60)
download_hf_dataset("Sonulee/SurgWound", "Sonulee_SurgWound", "3. Sonulee")

# ============================================================
# 4: UWM Wound Classification (GitHub) - try multiple URLs
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
    ds_dir.mkdir(parents=True, exist_ok=True)
    downloaded = False

    # Try multiple possible GitHub URLs
    urls = [
        "https://github.com/uwm-bigdata/wound-classification/archive/refs/heads/master.zip",
        "https://github.com/uwm-bigdata/wound-classification/archive/refs/heads/main.zip",
        "https://github.com/uwm-bigdata/Chronic-Wound-Classification/archive/refs/heads/main.zip",
        "https://github.com/uwm-bigdata/Chronic-Wound-Classification/archive/refs/heads/master.zip",
    ]

    for url in urls:
        try:
            print(f"  Trying: {url.split('/')[-4]}...")
            r = requests.get(url, stream=True, timeout=60, allow_redirects=True)
            if r.status_code == 200:
                zip_path = ds_dir / "repo.zip"
                total = 0
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                        total += len(chunk)
                print(f"  Downloaded: {total/(1024*1024):.1f} MB")

                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(ds_dir)
                zip_path.unlink()

                img_count = count_images(ds_dir)
                print(f"  Images found: {img_count}")
                downloaded = True
                results["4. UWM Classification"] = f"{img_count} images {'✅' if img_count > 0 else '⚠️'}"
                break
        except Exception as e:
            print(f"    Failed: {str(e)[:60]}")
            continue

    if not downloaded:
        print("  All GitHub URLs failed")
        results["4. UWM Classification"] = "NOT AVAILABLE ⚠️"

# ============================================================
# 5: UWM Multi-modal Wounds (GitHub)
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
    ds_dir.mkdir(parents=True, exist_ok=True)
    downloaded = False

    urls = [
        "https://github.com/uwm-bigdata/Multi-modal-Wound-Classification-using-Images-and-Locations/archive/refs/heads/master.zip",
        "https://github.com/uwm-bigdata/Multi-modal-Wound-Classification-using-Images-and-Locations/archive/refs/heads/main.zip",
    ]

    for url in urls:
        try:
            repo_name = url.split("/")[4]
            print(f"  Trying: {repo_name[:40]}...")
            r = requests.get(url, stream=True, timeout=120, allow_redirects=True)
            if r.status_code == 200:
                zip_path = ds_dir / "repo.zip"
                total = 0
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                        total += len(chunk)
                print(f"  Downloaded: {total/(1024*1024):.1f} MB")

                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(ds_dir)
                zip_path.unlink()

                img_count = count_images(ds_dir)
                print(f"  Images found: {img_count}")
                downloaded = True
                results["5. UWM Multi-modal"] = f"{img_count} images {'✅' if img_count > 0 else '⚠️'}"
                break
        except Exception as e:
            print(f"    Failed: {str(e)[:60]}")
            continue

    if not downloaded:
        print("  GitHub download failed")
        results["5. UWM Multi-modal"] = "NOT AVAILABLE ⚠️"

# ============================================================
# 6: Kaggle Wound Segmentation
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
    kaggle_ok = False
    try:
        result = subprocess.run(
            [sys.executable, "-m", "kaggle", "datasets", "download",
             "-d", "leoscode/wound-segmentation-images",
             "-p", str(ds_dir), "--unzip"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            kaggle_ok = True
            img_count = count_images(ds_dir)
            print(f"  Downloaded via Kaggle CLI: {img_count} images")
            results["6. Kaggle Wounds"] = f"{img_count} images ✅"
    except: pass

    if not kaggle_ok:
        print("  MANUAL DOWNLOAD NEEDED:")
        print("  1. Open: https://www.kaggle.com/datasets/leoscode/wound-segmentation-images")
        print("  2. Click 'Download' button")
        print(f"  3. Extract ZIP to: {ds_dir.absolute()}")
        results["6. Kaggle Wounds"] = "MANUAL ⬇️"

# ============================================================
# 7: Roboflow Surgical Wound
# ============================================================
ds_dir = BASE / "roboflow_surgical"
print(f"\n{'='*60}")
print("7/7  Roboflow Surgical Wound (708 images)")
print("=" * 60)

if count_images(ds_dir) >= 50:
    c = count_images(ds_dir)
    print(f"  Already downloaded! ({c} images)")
    results["7. Roboflow"] = f"{c} images ✅"
else:
    print("  MANUAL DOWNLOAD NEEDED:")
    print("  1. Open: https://universe.roboflow.com/wounddetection-lvlph/surgical-wound-classification")
    print("  2. Click 'Download Dataset' > Format: Folder of Images")
    print(f"  3. Extract to: {ds_dir.absolute()}")
    results["7. Roboflow"] = "MANUAL ⬇️"

# ============================================================
# BONUS: Extra HuggingFace wound datasets
# ============================================================
print(f"\n{'='*60}")
print("BONUS: Extra HuggingFace datasets...")
print("=" * 60)

extras = [
    ("hongrui/miccai_wound", "miccai_wound"),
    ("keremberke/wound-detection", "wound_detection"),
]

for ds_name, folder_name in extras:
    ds_dir = BASE / folder_name
    if count_images(ds_dir) >= 50:
        print(f"  {ds_name}: Already have {count_images(ds_dir)} images")
        continue
    try:
        download_hf_dataset(ds_name, folder_name, f"B. {folder_name}")
    except:
        print(f"  {ds_name}: Not available")

# ============================================================
# SUMMARY
# ============================================================
print(f"\n{'='*60}")
print("DOWNLOAD SUMMARY")
print("=" * 60)

for name, status in results.items():
    print(f"  {name}: {status}")

grand_total = count_images(BASE)
print(f"\n  GRAND TOTAL: {grand_total} images")

print(f"\n  Per folder:")
for sub in sorted(BASE.iterdir()):
    if sub.is_dir():
        c = count_images(sub)
        if c > 0:
            print(f"    {sub.name}: {c}")

print(f"\n  NEXT STEPS:")
print(f"  1. Download Kaggle + Roboflow manually (links above)")
print(f"  2. pip install numpy==1.26.4")
print(f"  3. python train_wounds.py")
