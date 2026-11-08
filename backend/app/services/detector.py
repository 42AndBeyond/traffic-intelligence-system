import cv2
import numpy as np
from ultralytics import YOLO
from app.config import MODEL_PATH, CLASSES, CONF_THRESHOLD

_model = None


def get_model():
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model


def detect_image(img_bgr):
    """Returns list of detections with unique IDs (per image)."""
    model = get_model()
    result = model.predict(
        img_bgr, conf=CONF_THRESHOLD, classes=list(CLASSES.keys()), verbose=False
    )[0]

    detections = []
    for i, box in enumerate(result.boxes, start=1):
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
        cls_id = int(box.cls[0])
        detections.append({
            "id": i,
            "class_id": cls_id,
            "category": CLASSES[cls_id],
            "confidence": round(float(box.conf[0]), 3),
            "bbox": [round(x1), round(y1), round(x2), round(y2)],
            "center": [round((x1 + x2) / 2), round((y1 + y2) / 2)],
        })
    return detections


COLORS = {
    "pedestrian": (0, 165, 255),
    "bicycle": (255, 200, 0),
    "car": (0, 200, 0),
    "motorcycle": (255, 0, 255),
    "bus": (0, 0, 255),
    "truck": (255, 100, 0),
}


def annotate(img_bgr, detections):
    out = img_bgr.copy()
    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        color = COLORS.get(d["category"], (255, 255, 255))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"#{d['id']} {d['category']} {d['confidence']:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(out, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(out, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return out