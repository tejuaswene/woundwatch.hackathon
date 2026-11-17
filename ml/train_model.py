"""
WoundWatch - Train Wound Infection Classification Model
Uses MobileNetV2 transfer learning for lightweight, fast inference
3 classes: healthy (GREEN), mild_risk (YELLOW), infected (RED)
"""

import os
import sys
import json
import numpy as np
from pathlib import Path

def install_deps():
    os.system(f"{sys.executable} -m pip install tensorflow pillow --quiet")

def train():
    install_deps()

    import tensorflow as tf
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout, BatchNormalization
    from tensorflow.keras.models import Model, Sequential
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

    print("=" * 50)
    print("WoundWatch - ML Model Training")
    print("=" * 50)

    # Config
    IMG_SIZE = 224
    BATCH_SIZE = 16
    EPOCHS = 30
    NUM_CLASSES = 3
    TRAIN_DIR = "dataset/train"
    VAL_DIR = "dataset/val"
    MODEL_PATH = "wound_model.h5"
    LABELS_PATH = "wound_labels.json"

    if not os.path.exists(TRAIN_DIR):
        print("ERROR: dataset/train not found. Run download_dataset.py first!")
        sys.exit(1)

    # Data augmentation for training
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=30,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.2,
        zoom_range=0.3,
        horizontal_flip=True,
        vertical_flip=True,
        brightness_range=[0.7, 1.3],
        fill_mode='nearest'
    )

    val_datagen = ImageDataGenerator(rescale=1./255)

    print("\nLoading training data...")
    train_generator = train_datagen.flow_from_directory(
        TRAIN_DIR,
        target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        shuffle=True
    )

    print("\nLoading validation data...")
    val_generator = val_datagen.flow_from_directory(
        VAL_DIR,
        target_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        shuffle=False
    )

    # Save class labels
    class_indices = train_generator.class_indices
    labels = {v: k for k, v in class_indices.items()}

    # Map to our risk system
    label_mapping = {
        "healthy": {"risk": "GREEN", "label": "Healthy - Normal Healing"},
        "mild_risk": {"risk": "YELLOW", "label": "Mild Risk - Monitor Closely"},
        "infected": {"risk": "RED", "label": "Infected - Seek Medical Attention"}
    }

    labels_config = {
        "class_indices": class_indices,
        "index_to_class": labels,
        "risk_mapping": label_mapping,
        "img_size": IMG_SIZE
    }

    with open(LABELS_PATH, "w") as f:
        json.dump(labels_config, f, indent=2)
    print(f"\nClass mapping: {class_indices}")

    # Build model - MobileNetV2 transfer learning
    print("\nBuilding MobileNetV2 model...")

    base_model = MobileNetV2(
        weights='imagenet',
        include_top=False,
        input_shape=(IMG_SIZE, IMG_SIZE, 3)
    )

    # Freeze base model layers (use pre-trained features)
    base_model.trainable = False

    # Add custom classification head
    model = Sequential([
        base_model,
        GlobalAveragePooling2D(),
        BatchNormalization(),
        Dense(128, activation='relu'),
        Dropout(0.5),
        BatchNormalization(),
        Dense(64, activation='relu'),
        Dropout(0.3),
        Dense(NUM_CLASSES, activation='softmax')
    ])

    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    model.summary()

    # Callbacks
    callbacks = [
        EarlyStopping(
            monitor='val_accuracy',
            patience=8,
            restore_best_weights=True,
            verbose=1
        ),
        ModelCheckpoint(
            MODEL_PATH,
            monitor='val_accuracy',
            save_best_only=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3,
            min_lr=1e-6,
            verbose=1
        )
    ]

    # Phase 1: Train classification head only
    print("\n" + "=" * 50)
    print("Phase 1: Training classification head...")
    print("=" * 50)

    history1 = model.fit(
        train_generator,
        epochs=15,
        validation_data=val_generator,
        callbacks=callbacks,
        verbose=1
    )

    # Phase 2: Fine-tune last 30 layers of base model
    print("\n" + "=" * 50)
    print("Phase 2: Fine-tuning top layers...")
    print("=" * 50)

    base_model.trainable = True
    # Freeze all layers except last 30
    for layer in base_model.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=Adam(learning_rate=0.0001),  # Lower LR for fine-tuning
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    history2 = model.fit(
        train_generator,
        epochs=EPOCHS,
        initial_epoch=len(history1.history['loss']),
        validation_data=val_generator,
        callbacks=callbacks,
        verbose=1
    )

    # Evaluate
    print("\n" + "=" * 50)
    print("Final Evaluation")
    print("=" * 50)

    val_loss, val_acc = model.evaluate(val_generator, verbose=0)
    print(f"Validation Accuracy: {val_acc:.2%}")
    print(f"Validation Loss:     {val_loss:.4f}")

    # Save final model
    model.save(MODEL_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")
    print(f"Labels saved to: {LABELS_PATH}")

    # Also save as TFLite for mobile deployment
    try:
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()
        tflite_path = "wound_model.tflite"
        with open(tflite_path, "wb") as f:
            f.write(tflite_model)
        print(f"TFLite model saved to: {tflite_path} ({len(tflite_model)/(1024*1024):.1f} MB)")
    except Exception as e:
        print(f"TFLite conversion skipped: {e}")

    print("\n" + "=" * 50)
    print("TRAINING COMPLETE!")
    print("=" * 50)
    print(f"\nNext steps:")
    print(f"  1. Copy wound_model.h5 and wound_labels.json to backend/")
    print(f"  2. Copy wound_analyzer_ml.py to backend/wound_analyzer.py")
    print(f"  3. Restart backend server")


if __name__ == "__main__":
    train()
