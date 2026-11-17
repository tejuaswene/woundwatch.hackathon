"""
WoundWatch - EfficientNetB4 Training on Post-Surgical Wound Images
==================================================================
Uses ONLY wound images from wound_data/ folder (NO cancer/dermoscopy)
3-class: healthy (GREEN), mild_risk (YELLOW), infected (RED)

BEFORE RUNNING - Fix TensorFlow + NumPy:
  pip install "numpy==1.26.4"
  pip install tensorflow==2.15.0
  OR
  pip install "tensorflow>=2.16" (supports numpy 2.x)

Then: python train_wounds.py
"""

import os, sys, random, json, time, shutil
import numpy as np
from pathlib import Path
from PIL import Image

# ============================================================
# CONFIG
# ============================================================
IMG_SIZE = 380
BATCH_SIZE = 4           # Small for 4GB GPU
NUM_CLASSES = 3
PHASE1_EPOCHS = 20       # Head only
PHASE2_EPOCHS = 50       # Fine-tune top 50 layers
MIN_PER_CLASS = 7000     # Target 7K/class = 21K total

WOUND_DATA = Path("wound_data")  # Your 3 folders live here
DATASET = Path("dataset")        # Organized train/val/test

start_time = time.time()

def elapsed():
    m = (time.time() - start_time) / 60
    return f"{m:.0f}m" if m < 60 else f"{m/60:.1f}h"

def count_images(folder):
    folder = Path(folder)
    if not folder.exists(): return 0
    c = 0
    for ext in ['*.jpg','*.jpeg','*.png','*.bmp','*.tiff','*.gif']:
        c += len(list(folder.rglob(ext)))
    return c

# ============================================================
# STEP 1: GPU Setup + Mixed Precision
# ============================================================
print("=" * 60)
print("STEP 1: GPU Setup")
print("=" * 60)

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

try:
    import tensorflow as tf
    print(f"TensorFlow: {tf.__version__}")
    print(f"NumPy: {np.__version__}")
except ImportError:
    print("ERROR: TensorFlow not found!")
    print("Install: pip install tensorflow>=2.16")
    sys.exit(1)

# Check numpy compatibility
tf_major = int(tf.__version__.split('.')[0])
tf_minor = int(tf.__version__.split('.')[1])
np_major = int(np.__version__.split('.')[0])

if tf_minor <= 15 and np_major >= 2:
    print("\n*** WARNING: TensorFlow 2.15 needs numpy<2.0 ***")
    print("    You have numpy", np.__version__)
    print("\n    Fix option 1: pip install \"numpy==1.26.4\"")
    print("    Fix option 2: pip install \"tensorflow>=2.16\"")
    print("\n    After fixing, re-run this script.")
    sys.exit(1)

# Enable mixed precision
from tensorflow.keras import mixed_precision
mixed_precision.set_global_policy('mixed_float16')
print("Mixed precision (FP16) enabled")

gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(f"GPU: {gpus}")
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
    print("Memory growth enabled")
else:
    print("WARNING: No GPU found! Training will be VERY slow on CPU.")
    resp = input("Continue on CPU? (y/n): ").strip().lower()
    if resp != 'y':
        sys.exit(0)

# ============================================================
# STEP 2: Scan wound_data/ for ALL images
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 2: Scanning wound_data/ folder...")
print("=" * 60)

if not WOUND_DATA.exists():
    print(f"ERROR: {WOUND_DATA}/ folder not found!")
    print("Create it and put your wound images inside.")
    sys.exit(1)

# Find all image files across all subfolders
all_images = []
for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.gif']:
    all_images.extend(list(WOUND_DATA.rglob(ext)))

print(f"Found {len(all_images)} total images in wound_data/")

# Show breakdown by folder
folders = {}
for img_path in all_images:
    # Get the immediate subfolder under wound_data
    rel = img_path.relative_to(WOUND_DATA)
    top_folder = rel.parts[0] if len(rel.parts) > 1 else "(root)"
    folders[top_folder] = folders.get(top_folder, 0) + 1

for folder, count in sorted(folders.items()):
    print(f"  {folder}: {count} images")

if len(all_images) == 0:
    print("\nERROR: No images found in wound_data/!")
    print("Download datasets first using download_datasets.py")
    sys.exit(1)

# ============================================================
# STEP 3: Classify images into 3 categories using color analysis
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 3: Classifying {len(all_images)} images...")
print("=" * 60)
print("Using wound color analysis: redness, texture, inflammation markers")

# Create organized folders
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

        # Analyze wound color characteristics
        thumb = img.resize((100, 100))
        arr = np.array(thumb, dtype=np.float32)

        r_ch = arr[:, :, 0]
        g_ch = arr[:, :, 1]
        b_ch = arr[:, :, 2]

        r_mean = r_ch.mean()
        g_mean = g_ch.mean()
        b_mean = b_ch.mean()

        # Redness index: how much red dominates
        redness = r_mean - (g_mean + b_mean) / 2

        # Yellowness: pus/discharge indicator
        yellowness = (r_mean + g_mean) / 2 - b_mean

        # Darkness: necrotic tissue
        brightness = (r_mean + g_mean + b_mean) / 3

        # Color variance: texture indicator
        r_var = r_ch.var()

        # Classification logic for post-surgical wounds:
        # - Healthy: pink/light, moderate redness, uniform color
        # - Mild risk: increased redness or slight yellowness
        # - Infected: high redness, yellow/green discharge, dark necrotic areas

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

        # Save with unique name
        safe_name = img_path.stem.replace(" ", "_")
        out_name = f"{safe_name}_{idx:05d}.jpg"
        img.save(all_dir / cls / out_name, "JPEG", quality=95)
        classified[cls] += 1

        if (idx + 1) % 500 == 0:
            print(f"  [{elapsed()}] Processed {idx+1}/{len(all_images)}...")

    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  Error on {img_path.name}: {e}")

print(f"\nClassification results:")
for cls, count in classified.items():
    print(f"  {cls}: {count}")
print(f"  Total: {sum(classified.values())} (errors: {errors})")

# ============================================================
# STEP 4: Balance & Augment to 20K+ (7K per class)
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 4: Augmenting to {MIN_PER_CLASS} per class...")
print("=" * 60)

from tensorflow.keras.preprocessing.image import ImageDataGenerator as IDG

# Multiple augmentation strategies for diversity
augmentors = [
    IDG(rotation_range=40, width_shift_range=0.3, height_shift_range=0.3,
        shear_range=0.3, zoom_range=0.4, horizontal_flip=True,
        vertical_flip=True, brightness_range=[0.5, 1.5], fill_mode='nearest'),
    IDG(rotation_range=90, width_shift_range=0.2, height_shift_range=0.2,
        shear_range=0.4, zoom_range=0.5, horizontal_flip=True,
        channel_shift_range=40, fill_mode='reflect'),
    IDG(rotation_range=30, zoom_range=0.3, horizontal_flip=True,
        brightness_range=[0.6, 1.4], channel_shift_range=30, fill_mode='nearest'),
]

for cls in ["healthy", "mild_risk", "infected"]:
    folder = all_dir / cls
    existing = list(folder.glob("*.jpg")) + list(folder.glob("*.png"))
    current = len(existing)
    need = MIN_PER_CLASS - current

    if need <= 0:
        print(f"  {cls}: already at {current} (target {MIN_PER_CLASS})")
        continue

    if current == 0:
        print(f"  {cls}: NO images! Cannot augment from 0.")
        print(f"  Skipping this class - model may not train well.")
        continue

    print(f"  [{elapsed()}] {cls}: {current} real -> augmenting +{need}...")
    generated = 0
    aug_idx = 0

    while generated < need:
        src = random.choice(existing)
        aug = augmentors[aug_idx % len(augmentors)]
        aug_idx += 1
        try:
            img_pil = Image.open(src).convert("RGB").resize((IMG_SIZE, IMG_SIZE))
            arr = np.array(img_pil).reshape(1, IMG_SIZE, IMG_SIZE, 3)
            aug_img = next(aug.flow(arr, batch_size=1))[0].astype(np.uint8)
            Image.fromarray(aug_img).save(
                folder / f"aug_{cls}_{generated:05d}.jpg", "JPEG", quality=85
            )
            generated += 1
            if generated % 1000 == 0:
                print(f"    [{elapsed()}] +{generated}/{need}...")
        except:
            continue

    final = len(list(folder.glob("*.jpg")))
    print(f"  {cls}: {current} real + {generated} augmented = {final} total")

# Show final counts
print(f"\n  Final dataset:")
total = 0
for cls in ["healthy", "mild_risk", "infected"]:
    c = len(list((all_dir / cls).glob("*")))
    total += c
    print(f"    {cls}: {c}")
print(f"    TOTAL: {total}")

# ============================================================
# STEP 5: Split into train/val/test (70/15/15)
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 5: Splitting dataset (70/15/15)...")
print("=" * 60)

random.seed(42)

for cls in ["healthy", "mild_risk", "infected"]:
    images = list((all_dir / cls).glob("*.jpg")) + list((all_dir / cls).glob("*.png"))
    random.shuffle(images)
    n = len(images)
    t1 = int(n * 0.70)
    t2 = int(n * 0.85)

    for p in images[:t1]:
        shutil.copy2(p, DATASET / "train" / cls / p.name)
    for p in images[t1:t2]:
        shutil.copy2(p, DATASET / "val" / cls / p.name)
    for p in images[t2:]:
        shutil.copy2(p, DATASET / "test" / cls / p.name)

    print(f"  {cls}: {t1} train / {t2-t1} val / {n-t2} test")

# Clean up all/ folder to save disk space
shutil.rmtree(all_dir, ignore_errors=True)
print("Dataset split complete!")

# ============================================================
# STEP 6: Build EfficientNetB4 Model
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 6: Building EfficientNetB4...")
print("=" * 60)

from tensorflow.keras.applications import EfficientNetB4
from tensorflow.keras.layers import (
    Dense, GlobalAveragePooling2D, Dropout, BatchNormalization, Input
)
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import (
    EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
)

# Data generators
train_datagen = IDG(
    rescale=1./255,
    rotation_range=40, width_shift_range=0.2, height_shift_range=0.2,
    shear_range=0.2, zoom_range=0.3,
    horizontal_flip=True, vertical_flip=True,
    brightness_range=[0.7, 1.3], channel_shift_range=30, fill_mode='nearest'
)
val_datagen = IDG(rescale=1./255)

train_gen = train_datagen.flow_from_directory(
    str(DATASET / "train"), target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE, class_mode='categorical', shuffle=True
)
val_gen = val_datagen.flow_from_directory(
    str(DATASET / "val"), target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE, class_mode='categorical', shuffle=False
)
test_gen = val_datagen.flow_from_directory(
    str(DATASET / "test"), target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE, class_mode='categorical', shuffle=False
)

print(f"\nTrain: {train_gen.samples} | Val: {val_gen.samples} | Test: {test_gen.samples}")

if train_gen.samples == 0:
    print("ERROR: No training images found!")
    sys.exit(1)

# Save label mapping
labels_config = {
    "model": "EfficientNetB4",
    "img_size": IMG_SIZE,
    "class_indices": train_gen.class_indices,
    "index_to_class": {v: k for k, v in train_gen.class_indices.items()},
    "risk_mapping": {
        "healthy":   {"risk": "GREEN",  "label": "Healthy - Normal Healing"},
        "mild_risk": {"risk": "YELLOW", "label": "Mild Risk - Monitor Closely"},
        "infected":  {"risk": "RED",    "label": "Infected - Seek Medical Attention"}
    }
}
with open("wound_labels.json", "w") as f:
    json.dump(labels_config, f, indent=2)
print("Saved wound_labels.json")

# Build model
print("\nBuilding EfficientNetB4 (mixed precision)...")
base_model = EfficientNetB4(
    weights='imagenet', include_top=False,
    input_shape=(IMG_SIZE, IMG_SIZE, 3)
)
base_model.trainable = False  # Freeze for Phase 1

inputs = Input(shape=(IMG_SIZE, IMG_SIZE, 3))
x = base_model(inputs, training=False)
x = GlobalAveragePooling2D()(x)
x = BatchNormalization()(x)
x = Dense(256, activation='relu')(x)
x = Dropout(0.5)(x)
x = BatchNormalization()(x)
x = Dense(128, activation='relu')(x)
x = Dropout(0.3)(x)
x = Dense(64, activation='relu')(x)
x = Dropout(0.2)(x)
# float32 output for mixed precision stability
outputs = Dense(NUM_CLASSES, activation='softmax', dtype='float32')(x)

model = Model(inputs, outputs)
print(f"Total params: {model.count_params():,}")

# ============================================================
# STEP 7: Phase 1 - Train head only (base frozen)
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 7: Phase 1 - Training head ({PHASE1_EPOCHS} epochs)...")
print("=" * 60)
print(f"Batch: {BATCH_SIZE} | Estimated: 2-4 hours")

model.compile(
    optimizer=Adam(learning_rate=0.001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

history1 = model.fit(
    train_gen, epochs=PHASE1_EPOCHS,
    validation_data=val_gen,
    callbacks=[
        EarlyStopping(monitor='val_accuracy', patience=5, restore_best_weights=True),
        ModelCheckpoint('wound_phase1.h5', monitor='val_accuracy', save_best_only=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=1e-6)
    ]
)
best_p1 = max(history1.history['val_accuracy'])
print(f"\n[{elapsed()}] Phase 1 best val accuracy: {best_p1:.2%}")

# ============================================================
# STEP 8: Phase 2 - Fine-tune top 50 layers
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 8: Phase 2 - Fine-tuning ({PHASE2_EPOCHS} epochs)...")
print("=" * 60)
print(f"Unfreezing top 50 layers | Estimated: 8-20 hours")

base_model.trainable = True
for layer in base_model.layers[:-50]:
    layer.trainable = False

trainable = sum(p.numpy().size for p in model.trainable_weights)
print(f"Trainable params now: {trainable:,}")

model.compile(
    optimizer=Adam(learning_rate=0.0001),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

history2 = model.fit(
    train_gen,
    epochs=PHASE1_EPOCHS + PHASE2_EPOCHS,
    initial_epoch=len(history1.history['loss']),
    validation_data=val_gen,
    callbacks=[
        EarlyStopping(monitor='val_accuracy', patience=8, restore_best_weights=True),
        ModelCheckpoint('wound_model.h5', monitor='val_accuracy', save_best_only=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=4, min_lr=1e-7)
    ]
)
best_p2 = max(history2.history['val_accuracy'])
print(f"\n[{elapsed()}] Phase 2 best val accuracy: {best_p2:.2%}")

# ============================================================
# STEP 9: Evaluate on test set
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 9: Final Evaluation...")
print("=" * 60)

best_model = tf.keras.models.load_model('wound_model.h5')
test_loss, test_acc = best_model.evaluate(test_gen)
print(f"\nTest Accuracy: {test_acc:.2%}")

# Training plot
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    acc = history1.history['accuracy'] + history2.history['accuracy']
    val_acc = history1.history['val_accuracy'] + history2.history['val_accuracy']
    loss = history1.history['loss'] + history2.history['loss']
    val_loss = history1.history['val_loss'] + history2.history['val_loss']

    phase1_end = len(history1.history['accuracy']) - 1

    ax1.plot(acc, label='Train', color='#2BA84A')
    ax1.plot(val_acc, label='Val', color='#2F2B6E')
    ax1.axvline(phase1_end, color='red', ls='--', label='Fine-tune start')
    ax1.set_title('Accuracy'); ax1.set_xlabel('Epoch'); ax1.legend()

    ax2.plot(loss, label='Train', color='#E89B2C')
    ax2.plot(val_loss, label='Val', color='#D64545')
    ax2.axvline(phase1_end, color='red', ls='--', label='Fine-tune start')
    ax2.set_title('Loss'); ax2.set_xlabel('Epoch'); ax2.legend()

    plt.suptitle(f'WoundWatch EfficientNetB4 - Test Acc: {test_acc:.2%}')
    plt.tight_layout()
    plt.savefig('training_history.png', dpi=150)
    print("Saved training_history.png")
except:
    print("Could not save plot (matplotlib missing)")

# ============================================================
# STEP 10: Export model
# ============================================================
print(f"\n{'='*60}")
print(f"[{elapsed()}] STEP 10: Exporting...")
print("=" * 60)

model.save('wound_model.h5')
h5_size = os.path.getsize('wound_model.h5') / (1024 * 1024)
print(f"wound_model.h5: {h5_size:.1f} MB")

# TFLite for mobile
try:
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite = converter.convert()
    with open('wound_model.tflite', 'wb') as f:
        f.write(tflite)
    print(f"wound_model.tflite: {len(tflite)/(1024*1024):.1f} MB")
except Exception as e:
    print(f"TFLite skipped: {e}")

total_hours = (time.time() - start_time) / 3600
print(f"\n{'='*60}")
print(f"TRAINING COMPLETE! ({total_hours:.1f} hours)")
print("=" * 60)
print(f"  Test Accuracy: {test_acc:.2%}")
print(f"  Phase 1 best:  {best_p1:.2%}")
print(f"  Phase 2 best:  {best_p2:.2%}")
print(f"\nOutput files:")
print(f"  wound_model.h5       ({h5_size:.1f} MB)")
print(f"  wound_labels.json")
print(f"  training_history.png")
print(f"\nNext steps:")
print(f"  1. Copy wound_model.h5 + wound_labels.json to backend/")
print(f"  2. Replace wound_analyzer.py with wound_analyzer_ml.py")
print(f"  3. Restart: cd backend && python main.py")
