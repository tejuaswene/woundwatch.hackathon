"""
WoundWatch - PyTorch EfficientNetB4 Wound Analyzer
====================================================
Uses trained wound_model.pth for inference.
Falls back to OpenCV LAB color analysis if model not found.
Includes image validation to reject non-wound photos.
"""

import os
import json
import numpy as np
from pathlib import Path

# Global model state
ML_MODEL = None
LABELS_CONFIG = None
USE_ML = False
DEVICE = None

def load_model():
    """Load the trained PyTorch model on first use"""
    global ML_MODEL, LABELS_CONFIG, USE_ML, DEVICE

    model_path = Path(__file__).parent / "wound_model.pth"
    labels_path = Path(__file__).parent / "wound_labels.json"

    if model_path.exists() and labels_path.exists():
        try:
            import torch
            from torchvision.models import efficientnet_b4
            import torch.nn as nn

            # Load labels config
            with open(labels_path, "r") as f:
                LABELS_CONFIG = json.load(f)

            # Set device (CPU for inference - fast enough)
            DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

            # Rebuild model architecture
            model = efficientnet_b4(weights=None)
            in_features = model.classifier[1].in_features
            model.classifier = nn.Sequential(
                nn.Dropout(0.4),
                nn.Linear(in_features, 256),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(128, LABELS_CONFIG.get("num_classes", 3)),
            )

            # Load trained weights
            state_dict = torch.load(str(model_path), map_location=DEVICE)
            model.load_state_dict(state_dict)
            model.to(DEVICE)
            model.eval()

            ML_MODEL = model
            USE_ML = True
            print(f"[WoundWatch] ML model loaded (EfficientNetB4 on {DEVICE})")
        except Exception as e:
            print(f"[WoundWatch] ML model failed to load: {e}")
            print(f"[WoundWatch] Falling back to OpenCV analysis")
            USE_ML = False
    else:
        missing = []
        if not model_path.exists(): missing.append("wound_model.pth")
        if not labels_path.exists(): missing.append("wound_labels.json")
        print(f"[WoundWatch] Missing: {', '.join(missing)}")
        print(f"[WoundWatch] Using OpenCV color analysis (fallback)")
        USE_ML = False


def validate_wound_image(image_path: str) -> dict:
    """
    Validate if uploaded image is a close-up wound/skin photo.
    Returns: {"valid": True/False, "reason": "..."}

    Checks:
    1. Image can be opened and is not corrupt
    2. Not a blank/solid color image
    3. High skin coverage (>35%) — wound photos are close-ups of skin
    4. Skin is one large connected region, not scattered (faces in a group photo)
    5. Low scene complexity — outdoor/group photos have many edges, wound close-ups don't
    6. ML model confidence check (if model loaded)
    """
    import cv2

    img = cv2.imread(image_path)
    if img is None:
        return {"valid": False, "reason": "Cannot read image. Please upload a valid photo."}

    try:
        img_resized = cv2.resize(img, (512, 512))
        hsv = cv2.cvtColor(img_resized, cv2.COLOR_BGR2HSV)

        # Check 1: Not a blank/solid color image
        std_dev = np.std(img_resized)
        if std_dev < 10:
            return {"valid": False, "reason": "Image appears blank or solid color. Please upload a wound photo."}

        # Check 2: Skin detection using HSV
        lower_skin1 = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin1 = np.array([25, 255, 255], dtype=np.uint8)
        mask1 = cv2.inRange(hsv, lower_skin1, upper_skin1)

        lower_skin2 = np.array([160, 20, 70], dtype=np.uint8)
        upper_skin2 = np.array([180, 255, 255], dtype=np.uint8)
        mask2 = cv2.inRange(hsv, lower_skin2, upper_skin2)

        lower_skin3 = np.array([0, 10, 40], dtype=np.uint8)
        upper_skin3 = np.array([30, 200, 255], dtype=np.uint8)
        mask3 = cv2.inRange(hsv, lower_skin3, upper_skin3)

        skin_mask = cv2.bitwise_or(mask1, mask2)
        skin_mask = cv2.bitwise_or(skin_mask, mask3)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

        skin_pixels = cv2.countNonZero(skin_mask)
        total_pixels = img_resized.shape[0] * img_resized.shape[1]
        skin_percentage = (skin_pixels / total_pixels) * 100

        # Wound close-ups should have at least 35% skin (stricter than before)
        if skin_percentage < 35:
            return {
                "valid": False,
                "reason": "This doesn't look like a close-up wound photo. Please take a close-up photo of your surgical wound area."
            }

        # Check 3: Skin should be one large connected region (not scattered faces)
        contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            largest_area = cv2.contourArea(largest_contour)
            largest_percentage = (largest_area / total_pixels) * 100

            # The biggest skin blob should be at least 25% of image
            # Group photos have many small skin regions (faces), wound photos have one big one
            if largest_percentage < 25:
                return {
                    "valid": False,
                    "reason": "No large skin/wound area found. Please upload a close-up photo of your wound, not a full-body or group photo."
                }

        # Check 4: Scene complexity — outdoor/group photos have many edges
        gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_percentage = (cv2.countNonZero(edges) / total_pixels) * 100

        # Wound close-ups are relatively smooth skin; busy scenes have >15% edges
        if edge_percentage > 15:
            return {
                "valid": False,
                "reason": "Image appears to be an outdoor or complex scene. Please upload a close-up photo of your wound only."
            }

        # Check 5: Color diversity — wound photos have limited color palette
        # Outdoor/scenic photos have many distinct colors
        small = cv2.resize(img_resized, (64, 64))
        pixels = small.reshape(-1, 3).astype(np.float32)
        # Count unique colors (quantized to reduce noise)
        quantized = (pixels // 32).astype(np.uint8)
        unique_colors = len(np.unique(quantized.reshape(-1, 3), axis=0))

        # Wound photos typically have < 80 quantized colors; scenic photos have 150+
        if unique_colors > 120:
            return {
                "valid": False,
                "reason": "Image has too many colors for a wound photo. Please upload a close-up of your surgical wound."
            }

        # Check 6: If ML model is loaded, verify confidence
        if USE_ML and ML_MODEL is not None:
            try:
                import torch
                from torchvision import transforms
                from PIL import Image

                img_size = LABELS_CONFIG.get("img_size", 380)
                transform = transforms.Compose([
                    transforms.Resize((img_size, img_size)),
                    transforms.ToTensor(),
                    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
                ])

                pil_img = Image.open(image_path).convert("RGB")
                img_tensor = transform(pil_img).unsqueeze(0).to(DEVICE)

                with torch.no_grad():
                    outputs = ML_MODEL(img_tensor)
                    probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]

                max_confidence = float(torch.max(probabilities))

                if max_confidence < 0.50:
                    return {
                        "valid": False,
                        "reason": "This doesn't appear to be a wound photo. Please upload a clear, close-up photo of your surgical wound."
                    }
            except Exception:
                pass

        return {"valid": True, "reason": "Image validated"}

    except Exception as e:
        print(f"[WoundWatch] Validation error: {e}")
        return {"valid": True, "reason": "Validation skipped"}


def analyze_wound_ml(image_path: str) -> dict:
    """Analyze wound using trained PyTorch EfficientNetB4 model"""
    import torch
    from torchvision import transforms
    from PIL import Image

    img_size = LABELS_CONFIG.get("img_size", 380)

    # Preprocess image (same transforms as training validation)
    transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    img = Image.open(image_path).convert("RGB")
    img_tensor = transform(img).unsqueeze(0).to(DEVICE)

    # Predict
    with torch.no_grad():
        outputs = ML_MODEL(img_tensor)
        probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]

    # Get class with highest confidence
    predicted_idx = int(torch.argmax(probabilities))
    confidence = float(probabilities[predicted_idx])

    # Map to class name
    idx_to_class = LABELS_CONFIG.get("idx_to_class", {})
    risk_mapping = LABELS_CONFIG.get("risk_mapping", {})

    class_name = idx_to_class.get(str(predicted_idx), "unknown")
    risk_info = risk_mapping.get(class_name, {"risk": "YELLOW", "label": "Unknown"})

    # Build class probabilities
    class_probs = {}
    for idx in range(len(probabilities)):
        cls = idx_to_class.get(str(idx), f"class_{idx}")
        class_probs[cls] = round(float(probabilities[idx]) * 100, 1)

    # Map to GREEN/YELLOW/RED
    risk_level = risk_info["risk"]

    # Generate risk score (0-1 scale matching original API)
    if risk_level == "GREEN":
        risk_score = round((1 - confidence) * 0.30, 3)
    elif risk_level == "YELLOW":
        risk_score = round(0.30 + confidence * 0.35, 3)
    else:  # RED
        risk_score = round(0.65 + confidence * 0.35, 3)

    # Recommendations
    if risk_level == "GREEN":
        recommendation = ("Wound appears to be healing normally. "
                          "Continue your prescribed care routine. "
                          "Upload another photo tomorrow.")
    elif risk_level == "YELLOW":
        recommendation = ("Some changes detected that need monitoring. "
                          "Keep the wound clean and dry. "
                          "If you notice increased pain, swelling, or discharge, "
                          "contact your doctor. Upload another photo in 12 hours.")
    else:
        recommendation = ("Significant changes detected that may indicate infection. "
                          "Please contact your doctor within 24 hours or visit the "
                          "hospital if you have fever, increasing pain, or pus discharge.")

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "redness_index": class_probs.get("infected", 0),
        "swelling_score": class_probs.get("mild_risk", 0),
        "color_deviation": round(100 - class_probs.get("healthy", 0), 1),
        "recommendation": recommendation,
        "analysis_details": {
            "model": "EfficientNetB4",
            "confidence": round(confidence * 100, 1),
            "class_probabilities": class_probs,
            "diagnosis": risk_info["label"],
            "device": str(DEVICE),
        }
    }


def analyze_wound_opencv(image_path: str) -> dict:
    """Fallback: OpenCV LAB color space analysis"""
    import cv2

    img = cv2.imread(image_path)
    if img is None:
        return _fallback_result("Could not read image")

    try:
        img = cv2.resize(img, (512, 512))
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Skin detection
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([25, 255, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)

        lower_skin2 = np.array([160, 20, 70], dtype=np.uint8)
        upper_skin2 = np.array([180, 255, 255], dtype=np.uint8)
        skin_mask2 = cv2.inRange(hsv, lower_skin2, upper_skin2)
        skin_mask = cv2.bitwise_or(skin_mask, skin_mask2)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

        skin_pixels = cv2.countNonZero(skin_mask)
        total_pixels = img.shape[0] * img.shape[1]

        if skin_pixels < total_pixels * 0.05:
            return _fallback_result("Could not detect skin region")

        l_channel, a_channel, b_channel = cv2.split(lab)
        skin_a = a_channel[skin_mask > 0]
        skin_b = b_channel[skin_mask > 0]
        skin_l = l_channel[skin_mask > 0]

        mean_a = float(np.mean(skin_a))
        std_a = float(np.std(skin_a))
        mean_l = float(np.mean(skin_l))
        std_l = float(np.std(skin_l))
        mean_b = float(np.mean(skin_b))
        std_b = float(np.std(skin_b))

        redness_raw = mean_a - 128
        redness_index = min(100, max(0, (redness_raw + 10) * 3))

        texture_score = std_l / (mean_l + 1) * 100
        swelling_score = min(100, max(0, (50 - texture_score) * 2))

        color_deviation = min(100, max(0, (std_a + std_b - 15) * 2))

        risk_score = (redness_index * 0.45 + swelling_score * 0.25 + color_deviation * 0.30) / 100
        risk_score = min(1.0, max(0.0, risk_score))

        if risk_score < 0.35:
            risk_level = "GREEN"
            recommendation = "Wound appears to be healing normally. Continue your prescribed care routine. Upload another photo tomorrow."
        elif risk_score < 0.65:
            risk_level = "YELLOW"
            recommendation = "Some color changes detected that need monitoring. Keep the wound clean and dry. If you notice increased pain, swelling, or discharge, contact your doctor. Upload another photo in 12 hours."
        else:
            risk_level = "RED"
            recommendation = "Significant color changes detected that may indicate infection. Please contact your doctor within 24 hours or visit the hospital if you have fever, increasing pain, or pus discharge."

        return {
            "risk_level": risk_level,
            "risk_score": round(risk_score, 3),
            "redness_index": round(redness_index, 1),
            "swelling_score": round(swelling_score, 1),
            "color_deviation": round(color_deviation, 1),
            "recommendation": recommendation,
            "analysis_details": {
                "model": "OpenCV (fallback)",
                "mean_a": round(mean_a, 2),
                "mean_b": round(mean_b, 2),
                "mean_l": round(mean_l, 2),
                "skin_coverage": round(skin_pixels / total_pixels * 100, 1)
            }
        }
    except Exception as e:
        return _fallback_result(f"Analysis error: {str(e)}")


def _fallback_result(reason: str) -> dict:
    """Return safe fallback when analysis fails"""
    return {
        "risk_level": "YELLOW",
        "risk_score": 0.5,
        "redness_index": 50.0,
        "swelling_score": 50.0,
        "color_deviation": 50.0,
        "recommendation": f"Automated analysis could not complete ({reason}). Please have your doctor review this photo manually.",
        "analysis_details": {"error": reason}
    }


def analyze_wound(image_path: str) -> dict:
    """
    Main entry point - analyzes wound image.
    Uses PyTorch ML model if available, falls back to OpenCV.
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


def generate_heatmap(image_path: str, output_path: str) -> bool:
    """
    Generate a wound heatmap overlay highlighting areas of concern.
    Red = high risk (infection/redness), Yellow = mild risk, Blue/Green = healthy.
    Returns True if heatmap was generated successfully.
    """
    import cv2

    img = cv2.imread(image_path)
    if img is None:
        return False

    try:
        img = cv2.resize(img, (512, 512))
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Detect skin region
        lower_skin1 = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin1 = np.array([25, 255, 255], dtype=np.uint8)
        mask1 = cv2.inRange(hsv, lower_skin1, upper_skin1)

        lower_skin2 = np.array([160, 20, 70], dtype=np.uint8)
        upper_skin2 = np.array([180, 255, 255], dtype=np.uint8)
        mask2 = cv2.inRange(hsv, lower_skin2, upper_skin2)

        lower_skin3 = np.array([0, 10, 40], dtype=np.uint8)
        upper_skin3 = np.array([30, 200, 255], dtype=np.uint8)
        mask3 = cv2.inRange(hsv, lower_skin3, upper_skin3)

        skin_mask = cv2.bitwise_or(mask1, mask2)
        skin_mask = cv2.bitwise_or(skin_mask, mask3)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

        # Extract LAB channels for skin area
        l_ch, a_ch, b_ch = cv2.split(lab)

        # Create risk score per pixel based on redness (a-channel)
        # Higher a-channel = more red = higher risk
        # a-channel: 0-255, center=128, >128 = red, <128 = green
        risk_map = np.zeros((512, 512), dtype=np.float32)

        # Redness component (a-channel deviation from neutral)
        redness = (a_ch.astype(np.float32) - 128) / 127  # -1 to 1
        redness = np.clip(redness, 0, 1)  # only positive (red) matters

        # Darkness component (darker areas may indicate bruising/necrosis)
        darkness = 1.0 - (l_ch.astype(np.float32) / 255)
        darkness = np.clip(darkness * 1.5 - 0.3, 0, 1)

        # Yellowness (b-channel - pus/discharge indicator)
        yellowness = (b_ch.astype(np.float32) - 128) / 127
        yellowness = np.clip(yellowness, 0, 1)

        # Combined risk score
        risk_map = redness * 0.50 + darkness * 0.25 + yellowness * 0.25
        risk_map = np.clip(risk_map, 0, 1)

        # Only apply to skin area
        risk_map[skin_mask == 0] = 0

        # Smooth the heatmap
        risk_map = cv2.GaussianBlur(risk_map, (21, 21), 0)

        # Convert to colormap (BLUE=safe → GREEN=ok → YELLOW=caution → RED=danger)
        heatmap_colored = cv2.applyColorMap(
            (risk_map * 255).astype(np.uint8),
            cv2.COLORMAP_JET
        )

        # Non-skin areas stay as original image
        heatmap_colored[skin_mask == 0] = img[skin_mask == 0]

        # Blend heatmap with original (60% heatmap, 40% original for skin areas)
        blended = img.copy()
        skin_area = skin_mask > 0
        blended[skin_area] = cv2.addWeighted(
            img[skin_area], 0.4,
            heatmap_colored[skin_area], 0.6,
            0
        )

        # Resize back to original and save
        original = cv2.imread(image_path)
        h, w = original.shape[:2]
        blended = cv2.resize(blended, (w, h))

        cv2.imwrite(output_path, blended)
        print(f"[WoundWatch] Heatmap saved: {output_path}")
        return True

    except Exception as e:
        print(f"[WoundWatch] Heatmap generation failed: {e}")
        return False