import os
import uuid
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import (SNAPSHOT_DIR, MAX_IMAGE_MB, ALLOWED_IMAGE_TYPES)
from app.services.detector import detect_image, annotate
from app.services.traffic import classify_density, image_risk_indicators

router = APIRouter(prefix="/api/image", tags=["Image"])


@router.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Only JPG, PNG or WEBP images are allowed")

    data = await file.read()
    if len(data) > MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(400, f"Image larger than {MAX_IMAGE_MB} MB")

    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not read image file")

    h, w = img.shape[:2]
    detections = detect_image(img)
    traffic = classify_density(detections, w, h)
    indicators = image_risk_indicators(detections)
    annotated = annotate(img, detections)

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    name = f"img_{uuid.uuid4().hex[:10]}.jpg"
    cv2.imwrite(os.path.join(SNAPSHOT_DIR, name), annotated)

    counts = {}
    for d in detections:
        counts[d["category"]] = counts.get(d["category"], 0) + 1

    return {
        "image_size": {"width": w, "height": h},
        "total_objects": len(detections),
        "counts": counts,
        "detections": detections,
        "traffic": traffic,
        "risk_indicators": indicators,
        "risk_note": "Single image: these are visible hazard indicators, not a collision prediction.",
        "annotated_url": f"/snapshots/{name}",
    }