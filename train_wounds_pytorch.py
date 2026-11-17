"""
WoundWatch - EfficientNetB4 Training (PyTorch + NVIDIA GPU)
============================================================
Uses ONLY wound images from wound_data/ folder
3-class: healthy (GREEN), mild_risk (YELLOW), infected (RED)

INSTALL FIRST:
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

Then: python train_wounds_pytorch.py
"""

import os, sys, random, json, time, shutil
import numpy as np
from pathlib import Path
from PIL import Image

# ============================================================
# CONFIG
# ============================================================
IMG_SIZE = 380
BATCH_SIZE = 8           # PyTorch is more memory efficient
NUM_CLASSES = 3
PHASE1_EPOCHS = 20       # Head only
PHASE2_EPOCHS = 50       # Fine-tune
MIN_PER_CLASS = 7000     # 7K/class = 21K total
LR_PHASE1 = 0.001
LR_PHASE2 = 0.0001

WOUND_DATA = Path("wound_data")
DATASET = Path("dataset")

start_time = time.time()

def elapsed():
    m = (time.time() - start_time) / 60
    return f"{m:.0f}m" if m < 60 else f"{m/60:.1f}h"

def count_images(folder):
    folder = Path(folder)
    if not folder.exists(): return 0
    c = 0
    for ext in ['*.jpg','*.jpeg','*.png','*.bmp']:
        c += len(list(folder.rglob(ext)))
    return c

# ============================================================
# STEP 1: GPU Setup
# ============================================================
print("=" * 60)
print("STEP 1: GPU Setup")
print("=" * 60)

try:
    import torch
    import torchvision
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        device = torch.device("cuda")
    else:
        print("WARNING: CUDA not found! Check PyTorch CUDA install.")
        print("Install: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
        resp = input("Continue on CPU? (y/n): ").strip().lower()
        if resp != 'y':
            sys.exit(0)
        device = torch.device("cpu")
except ImportError:
    print("PyTorch not installed!")
    print("Run: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
    sys.exit(1)

print(f"Device: {device}")

# ============================================================
# STEP 2: Scan wound_data/
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 2: Scanning wound_data/...")
print("=" * 60)

if not WOUND_DATA.exists():
    print(f"ERROR: {WOUND_DATA}/ not found!")
    sys.exit(1)

all_images = []
for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
    all_images.extend(list(WOUND_DATA.rglob(ext)))

print(f"Found {len(all_images)} images")

folders = {}
for img_path in all_images:
    rel = img_path.relative_to(WOUND_DATA)
    top = rel.parts[0] if len(rel.parts) > 1 else "(root)"
    folders[top] = folders.get(top, 0) + 1
for f, c in sorted(folders.items()):
    print(f"  {f}: {c}")

if len(all_images) == 0:
    print("ERROR: No images found!")
    sys.exit(1)

# ============================================================
# STEP 3: Classify into 3 categories
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 3: Classifying {len(all_images)} images...")
print("=" * 60)

if DATASET.exists():
    shutil.rmtree(DATASET)
for split in ["train", "val", "test"]:
    for cls in ["healthy", "mild_risk", "infected"]:
        (DATASET / split / cls).mkdir(parents=True, exist_ok=True)
all_dir = DATASET / "all"
for cls in ["healthy", "mild_risk", "infected"]:
    (all_dir / cls).mkdir(parents=True, exist_ok=True)

classified = {"healthy": 0, "mild_risk": 0, "infected": 0}
errors = 0

for idx, img_path in enumerate(all_images):
    try:
        img = Image.open(img_path).convert("RGB")
        thumb = img.resize((100, 100))
        arr = np.array(thumb, dtype=np.float32)

        r_mean = arr[:,:,0].mean()
        g_mean = arr[:,:,1].mean()
        b_mean = arr[:,:,2].mean()
        r_var = arr[:,:,0].var()

        redness = r_mean - (g_mean + b_mean) / 2
        yellowness = (r_mean + g_mean) / 2 - b_mean
        brightness = (r_mean + g_mean + b_mean) / 3

        if redness > 35 or (yellowness > 50 and redness > 20):
            cls = "infected"
        elif redness > 30 and r_var > 800:
            cls = "infected"
        elif brightness < 80 and redness > 15:
            cls = "infected"
        elif redness > 15 or (yellowness > 35 and redness > 5):
            cls = "mild_risk"
        elif r_var > 600 and redness > 8:
            cls = "mild_risk"
        else:
            cls = "healthy"

        out_name = f"{img_path.stem}_{idx:05d}.jpg"
        img.save(all_dir / cls / out_name, "JPEG", quality=95)
        classified[cls] += 1

        if (idx + 1) % 1000 == 0:
            print(f"  [{elapsed()}] {idx+1}/{len(all_images)}...")
    except:
        errors += 1

print(f"\nClassified:")
for cls, count in classified.items():
    print(f"  {cls}: {count}")
print(f"  Total: {sum(classified.values())} (errors: {errors})")

# ============================================================
# STEP 4: Augment to 7K per class
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 4: Augmenting to {MIN_PER_CLASS}/class...")
print("=" * 60)

from torchvision import transforms

aug_transform = transforms.Compose([
    transforms.RandomResizedCrop(IMG_SIZE, scale=(0.6, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(45),
    transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.3, hue=0.1),
    transforms.RandomAffine(degrees=30, translate=(0.2, 0.2), shear=15),
])

for cls in ["healthy", "mild_risk", "infected"]:
    folder = all_dir / cls
    existing = list(folder.glob("*.jpg")) + list(folder.glob("*.png"))
    current = len(existing)
    need = MIN_PER_CLASS - current

    if need <= 0:
        print(f"  {cls}: already at {current}")
        continue
    if current == 0:
        print(f"  {cls}: NO images, skipping!")
        continue

    print(f"  [{elapsed()}] {cls}: {current} -> augmenting +{need}...")
    generated = 0
    while generated < need:
        src = random.choice(existing)
        try:
            img = Image.open(src).convert("RGB")
            aug_img = aug_transform(img)
            aug_img.save(folder / f"aug_{cls}_{generated:05d}.jpg", "JPEG", quality=85)
            generated += 1
            if generated % 2000 == 0:
                print(f"    [{elapsed()}] +{generated}/{need}...")
        except:
            continue

    print(f"  {cls}: {current} real + {generated} augmented")

print(f"\nFinal counts:")
total = 0
for cls in ["healthy", "mild_risk", "infected"]:
    c = len(list((all_dir / cls).glob("*")))
    total += c
    print(f"  {cls}: {c}")
print(f"  TOTAL: {total}")

# ============================================================
# STEP 5: Split train/val/test (70/15/15)
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 5: Splitting (70/15/15)...")
print("=" * 60)

random.seed(42)
for cls in ["healthy", "mild_risk", "infected"]:
    images = list((all_dir / cls).glob("*.jpg"))
    random.shuffle(images)
    n = len(images)
    t1, t2 = int(n * 0.70), int(n * 0.85)
    for p in images[:t1]: shutil.copy2(p, DATASET / "train" / cls / p.name)
    for p in images[t1:t2]: shutil.copy2(p, DATASET / "val" / cls / p.name)
    for p in images[t2:]: shutil.copy2(p, DATASET / "test" / cls / p.name)
    print(f"  {cls}: {t1} train / {t2-t1} val / {n-t2} test")

shutil.rmtree(all_dir, ignore_errors=True)

# ============================================================
# STEP 6: Build EfficientNetB4
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 6: Building EfficientNetB4...")
print("=" * 60)

from torchvision.models import efficientnet_b4, EfficientNet_B4_Weights
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader
import torch.nn as nn
import torch.optim as optim
from torch.cuda.amp import GradScaler, autocast

# Data transforms
train_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(30),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
val_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

train_dataset = ImageFolder(str(DATASET / "train"), transform=train_transform)
val_dataset = ImageFolder(str(DATASET / "val"), transform=val_transform)
test_dataset = ImageFolder(str(DATASET / "test"), transform=val_transform)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True,
                          num_workers=0, pin_memory=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False,
                        num_workers=0, pin_memory=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False,
                         num_workers=0, pin_memory=True)

print(f"Train: {len(train_dataset)} | Val: {len(val_dataset)} | Test: {len(test_dataset)}")
print(f"Classes: {train_dataset.class_to_idx}")

# Save label config
labels_config = {
    "model": "EfficientNetB4",
    "img_size": IMG_SIZE,
    "class_to_idx": train_dataset.class_to_idx,
    "idx_to_class": {v: k for k, v in train_dataset.class_to_idx.items()},
    "risk_mapping": {
        "healthy":   {"risk": "GREEN",  "label": "Healthy - Normal Healing"},
        "mild_risk": {"risk": "YELLOW", "label": "Mild Risk - Monitor Closely"},
        "infected":  {"risk": "RED",    "label": "Infected - Seek Medical Attention"}
    }
}
with open("wound_labels.json", "w") as f:
    json.dump(labels_config, f, indent=2)

# Build model
model = efficientnet_b4(weights=EfficientNet_B4_Weights.IMAGENET1K_V1)

# Freeze base for Phase 1
for param in model.parameters():
    param.requires_grad = False

# Replace classifier head
in_features = model.classifier[1].in_features
model.classifier = nn.Sequential(
    nn.Dropout(0.4),
    nn.Linear(in_features, 256),
    nn.ReLU(),
    nn.Dropout(0.3),
    nn.Linear(256, 128),
    nn.ReLU(),
    nn.Dropout(0.2),
    nn.Linear(128, NUM_CLASSES),
)

model = model.to(device)

total_params = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"\nTotal params: {total_params:,}")
print(f"Trainable (Phase 1): {trainable_params:,}")

# ============================================================
# Training function
# ============================================================
scaler = GradScaler()

def train_epoch(model, loader, criterion, optimizer):
    model.train()
    total_loss, correct, total = 0, 0, 0
    for batch_idx, (images, labels) in enumerate(loader):
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()

        with autocast():
            outputs = model(images)
            loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        total_loss += loss.item() * images.size(0)
        _, predicted = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total += images.size(0)

        if (batch_idx + 1) % 100 == 0:
            print(f"    Batch {batch_idx+1}/{len(loader)} - "
                  f"Loss: {total_loss/total:.4f} Acc: {correct/total:.2%}")

    return total_loss / total, correct / total

def validate(model, loader, criterion):
    model.eval()
    total_loss, correct, total = 0, 0, 0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            with autocast():
                outputs = model(images)
                loss = criterion(outputs, labels)
            total_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            correct += predicted.eq(labels).sum().item()
            total += images.size(0)
    return total_loss / total, correct / total

# ============================================================
# STEP 7: Phase 1 - Train head only
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 7: Phase 1 - Training head ({PHASE1_EPOCHS} epochs)...")
print("=" * 60)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.classifier.parameters(), lr=LR_PHASE1)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)

best_val_acc = 0
patience_counter = 0
PATIENCE = 5

for epoch in range(PHASE1_EPOCHS):
    train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer)
    val_loss, val_acc = validate(model, val_loader, criterion)
    scheduler.step(val_loss)

    lr = optimizer.param_groups[0]['lr']
    print(f"  [{elapsed()}] Epoch {epoch+1}/{PHASE1_EPOCHS} - "
          f"Train: {train_acc:.2%} | Val: {val_acc:.2%} | "
          f"Loss: {val_loss:.4f} | LR: {lr:.6f}")

    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save(model.state_dict(), "wound_phase1.pth")
        patience_counter = 0
    else:
        patience_counter += 1
        if patience_counter >= PATIENCE:
            print(f"  Early stopping at epoch {epoch+1}")
            break

print(f"\nPhase 1 best val accuracy: {best_val_acc:.2%}")
model.load_state_dict(torch.load("wound_phase1.pth"))

# ============================================================
# STEP 8: Phase 2 - Fine-tune top layers
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 8: Phase 2 - Fine-tuning ({PHASE2_EPOCHS} epochs)...")
print("=" * 60)

# Unfreeze last 50 layers of the feature extractor
all_layers = list(model.features.parameters())
for param in all_layers[-50:]:
    param.requires_grad = True

trainable_params2 = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"Trainable params now: {trainable_params2:,}")

optimizer2 = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=LR_PHASE2)
scheduler2 = optim.lr_scheduler.ReduceLROnPlateau(optimizer2, patience=4, factor=0.3)

best_val_acc2 = best_val_acc
patience_counter = 0
PATIENCE2 = 8

for epoch in range(PHASE2_EPOCHS):
    train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer2)
    val_loss, val_acc = validate(model, val_loader, criterion)
    scheduler2.step(val_loss)

    lr = optimizer2.param_groups[0]['lr']
    print(f"  [{elapsed()}] Epoch {epoch+1}/{PHASE2_EPOCHS} - "
          f"Train: {train_acc:.2%} | Val: {val_acc:.2%} | "
          f"Loss: {val_loss:.4f} | LR: {lr:.6f}")

    if val_acc > best_val_acc2:
        best_val_acc2 = val_acc
        torch.save(model.state_dict(), "wound_model.pth")
        patience_counter = 0
    else:
        patience_counter += 1
        if patience_counter >= PATIENCE2:
            print(f"  Early stopping at epoch {epoch+1}")
            break

print(f"\nPhase 2 best val accuracy: {best_val_acc2:.2%}")
model.load_state_dict(torch.load("wound_model.pth"))

# ============================================================
# STEP 9: Test evaluation
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 9: Final Evaluation...")
print("=" * 60)

test_loss, test_acc = validate(model, test_loader, criterion)
print(f"\nTest Accuracy: {test_acc:.2%}")

# Per-class accuracy
model.eval()
class_correct = {i: 0 for i in range(NUM_CLASSES)}
class_total = {i: 0 for i in range(NUM_CLASSES)}

with torch.no_grad():
    for images, labels in test_loader:
        images, labels = images.to(device), labels.to(device)
        outputs = model(images)
        _, predicted = outputs.max(1)
        for i in range(labels.size(0)):
            label = labels[i].item()
            class_total[label] += 1
            if predicted[i] == label:
                class_correct[label] += 1

idx_to_class = {v: k for k, v in train_dataset.class_to_idx.items()}
print("\nPer-class accuracy:")
for idx in range(NUM_CLASSES):
    cls_name = idx_to_class[idx]
    acc = class_correct[idx] / class_total[idx] if class_total[idx] > 0 else 0
    print(f"  {cls_name}: {acc:.2%} ({class_correct[idx]}/{class_total[idx]})")

# ============================================================
# STEP 10: Export model
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 10: Exporting...")
print("=" * 60)

# Save full model state
torch.save({
    'model_state_dict': model.state_dict(),
    'class_to_idx': train_dataset.class_to_idx,
    'img_size': IMG_SIZE,
    'num_classes': NUM_CLASSES,
}, 'wound_model_full.pth')

pth_size = os.path.getsize('wound_model.pth') / (1024 * 1024)
print(f"wound_model.pth: {pth_size:.1f} MB")
print(f"wound_labels.json: saved")

# Export ONNX for faster inference
try:
    dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE).to(device)
    torch.onnx.export(model, dummy, "wound_model.onnx",
                       input_names=["image"], output_names=["prediction"],
                       dynamic_axes={"image": {0: "batch"}, "prediction": {0: "batch"}})
    onnx_size = os.path.getsize('wound_model.onnx') / (1024 * 1024)
    print(f"wound_model.onnx: {onnx_size:.1f} MB")
except Exception as e:
    print(f"ONNX export skipped: {e}")

# Training plot
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(["Phase 1", "Phase 2", "Test"],
           [best_val_acc * 100, best_val_acc2 * 100, test_acc * 100],
           color=["#2F2B6E", "#7F79B6", "#2BA84A"])
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("WoundWatch EfficientNetB4 Training Results")
    ax.set_ylim(0, 100)
    for i, v in enumerate([best_val_acc, best_val_acc2, test_acc]):
        ax.text(i, v * 100 + 2, f"{v:.1%}", ha='center', fontweight='bold')
    plt.tight_layout()
    plt.savefig('training_history.png', dpi=150)
    print("Saved training_history.png")
except:
    pass

total_hours = (time.time() - start_time) / 3600
print(f"\n{'='*60}")
print(f"TRAINING COMPLETE! ({total_hours:.1f} hours)")
print("=" * 60)
print(f"  Phase 1 val acc: {best_val_acc:.2%}")
print(f"  Phase 2 val acc: {best_val_acc2:.2%}")
print(f"  Test accuracy:   {test_acc:.2%}")
print(f"\nOutput files:")
print(f"  wound_model.pth       ({pth_size:.1f} MB)")
print(f"  wound_model_full.pth")
print(f"  wound_labels.json")
print(f"\nNext: Copy to backend/ and update wound_analyzer to use PyTorch")
