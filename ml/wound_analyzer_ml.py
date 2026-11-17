"""
WoundWatch - ML-Based Wound Infection Analyzer
Replaces OpenCV color analysis with trained MobileNetV2 model
Falls back to OpenCV analysis if model not found
"""

import os
import json
import numpy as np
from pathlib import Path

# Try to load ML model
ML_MODEL = None
LABELS_CONFIG = None
USE_ML = False

def load_model():
    """Load the trained model on first use"""
    global ML_MODEL, LABELS_CONFIG, USE_ML

    model_path = Path(__file__).parent / "wound_model.h5"
    labels_path = Path(__file__).parent / "wound_labels.json"

    if model_path.exists() and labels_path.exists():
        try:
            import tensorflow as tf
            # Suppress TF warnings
            os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
            tf.get_logger().setLevel('ERROR')

            ML_MODEL = tf.keras.models.load_model(str(model_path))
            with open(labels_path, "r") as f:
                LABELS_CONFIG = json.load(f)
            USE_ML = True
            print(f"[WoundWatch] ML model loaded successfully")
        except Exception as e:
            print(f"[WoundWatch] ML model failed to load: {e}")
            print(f"[WoundWatch] Falling back to OpenCV analysis")
            USE_ML = False
    else:
        print(f"[WoundWatch] No ML model found at {model_path}")
        print(f"[WoundWatch] Using OpenCV color analysis (fallback)")
        USE_ML = False


def analyze_wound_ml(image_path: str) -> dict:
    """Analyze wound using trained ML model"""
    import tensorflow as tf
    from PIL import Image

    img_size = LABELS_CONFIG.get("img_size", 224)

    # Load and preprocess image
    img = Image.open(image_path).convert("RGB")
    img_resized = img.resize((img_size, img_size))
    img_array = np.array(img_resized) / 255.0
    img_batch = np.expand_dims(img_array, axis=0)

    # Predict
    predictions = ML_MODEL.predict(img_batch, verbose=0)[0]

    # Get class with highest confidence
    predicted_idx = int(np.argmax(predictions))
    confidence = float(predictions[predicted_idx])

    # Map to class name
    index_to_class = LABELS_CONFIG["index_to_class"]
    risk_mapping = LABELS_CONFIG["risk_mapping"]

    class_name = index_to_class[str(predicted_idx)]
    risk_info = risk_mapping[class_name]

    # Build detailed results
    class_probs = {}
    for idx, prob in enumerate(predictions):
        cls = index_to_class[str(idx)]
        class_probs[cls] = round(float(prob) * 100, 1)

    # Map to GREEN/YELLOW/RED
    risk_level = risk_info["risk"]

    # Generate risk score (0-100)
    if risk_level == "GREEN":
        risk_score = round((1 - confidence) * 30, 1)  # 0-30
    elif risk_level == "YELLOW":
        risk_score = round(30 + confidence * 35, 1)    # 30-65
    else:  # RED
        risk_score = round(65 + confidence * 35, 1)    # 65-100

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "confidence": round(confidence * 100, 1),
        "diagnosis": risk_info["label"],
        "analysis_method": "ML (MobileNetV2)",
        "class_probabilities": class_probs,
        "metrics": {
            "healthy_prob": class_probs.get("healthy", 0),
            "mild_risk_prob": class_probs.get("mild_risk", 0),
            "infected_prob": class_probs.get("infected", 0),
        },
        "recommendations": get_recommendations(risk_level, confidence)
    }


def analyze_wound_opencv(image_path: str) -> dict:
    """Fallback: OpenCV LAB color space analysis (original method)"""
    import cv2

    img = cv2.imread(image_path)
    if img is None:
        return {
            "risk_level": "YELLOW",
            "risk_score": 50,
            "confidence": 0,
            "diagnosis": "Unable to analyze image",
            "analysis_method": "OpenCV (fallback)",
            "error": "Could not read image"
        }

    # Convert to LAB color space
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # Analyze redness (a-channel in LAB, higher = more red)
    mean_a = float(np.mean(a_channel))
    std_a = float(np.std(a_channel))

    # Analyze brightness/darkness
    mean_l = float(np.mean(l_channel))

    # Analyze yellowness (b-channel, higher = more yellow)
    mean_b = float(np.mean(b_channel))

    # HSV analysis for redness
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Red mask (two ranges because red wraps around in HSV)
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])

    red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    red_mask = red_mask1 | red_mask2

    red_percentage = float(np.sum(red_mask > 0)) / red_mask.size * 100

    # Scoring
    redness_score = min((mean_a - 128) * 2, 40)  # a > 128 = red
    swelling_score = min(std_a / 5, 30)
    discharge_score = min(max(mean_b - 128, 0) * 1.5, 30)

    total_score = max(0, min(100, redness_score + swelling_score + discharge_score))

    # Classify
    if total_score < 30:
        risk_level = "GREEN"
        diagnosis = "Healthy - Normal Healing"
    elif total_score < 65:
        risk_level = "YELLOW"
        diagnosis = "Mild Risk - Monitor Closely"
    else:
        risk_level = "RED"
        diagnosis = "Infected - Seek Medical Attention"

    return {
        "risk_level": risk_level,
        "risk_score": round(total_score, 1),
        "confidence": round(min(abs(total_score - 50) * 2, 95), 1),
        "diagnosis": diagnosis,
        "analysis_method": "OpenCV LAB Color Analysis",
        "metrics": {
            "redness": round(mean_a, 1),
            "redness_std": round(std_a, 1),
            "brightness": round(mean_l, 1),
            "yellowness": round(mean_b, 1),
            "red_percentage": round(red_percentage, 1),
        },
        "recommendations": get_recommendations(risk_level, 0.7)
    }


def get_recommendations(risk_level: str, confidence: float) -> list:
    """Get care recommendations based on risk level"""
    if risk_level == "GREEN":
        return [
            "Wound is healing normally",
            "Continue keeping the wound clean and dry",
            "Change dressing as prescribed",
            "Take next photo in 24-48 hours for comparison"
        ]
    elif risk_level == "YELLOW":
        return [
            "Mild signs of concern detected",
            "Monitor wound closely for changes",
            "Keep wound clean, apply prescribed ointment",
            "Take photos every 12-24 hours",
            "Contact your doctor if symptoms worsen",
            "Watch for: increased redness, swelling, warmth, discharge"
        ]
    else:  # RED
        recommendations = [
            "WARNING: Signs of possible infection detected",
            "Contact your doctor or surgeon immediately",
            "Do not attempt to treat at home without medical advice",
            "Keep wound clean but avoid disturbing it",
            "Note any fever, chills, or increasing pain",
            "Seek emergency care if fever > 101°F (38.3°C)"
        ]
        if confidence > 0.9:
            recommendations.insert(1, "HIGH CONFIDENCE: Urgent medical review recommended")
        return recommendations


def analyze_wound(image_path: str) -> dict:
    """
    Main entry point - analyzes wound image
    Uses ML model if available, falls back to OpenCV
    """
    global USE_ML

    # Load model on first call
    if ML_MODEL is None and not USE_ML:
        load_model()

    if USE_ML and ML_MODEL is not None:
        try:
            return analyze_wound_ml(image_path)
        except Exception as e:
            print(f"[WoundWatch] ML analysis failed: {e}, falling back to OpenCV")
            return analyze_wound_opencv(image_path)
    else:
        return analyze_wound_opencv(image_path)


# For backward compatibility with existing backend
def analyze_wound_photo(image_path: str) -> dict:
    """Alias for analyze_wound - backward compatible"""
    return analyze_wound(image_path)
