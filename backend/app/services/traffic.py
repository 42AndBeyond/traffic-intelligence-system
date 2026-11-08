from app.config import DENSITY, VEHICLE_IDS


def classify_density(detections, img_w, img_h):
    vehicles = [d for d in detections if d["class_id"] in VEHICLE_IDS]
    count = len(vehicles)

    img_area = img_w * img_h
    occupied = 0
    for d in vehicles:
        x1, y1, x2, y2 = d["bbox"]
        occupied += max(0, x2 - x1) * max(0, y2 - y1)
    area_ratio = occupied / img_area if img_area else 0

    if count >= DENSITY["high_count"] or area_ratio >= DENSITY["high_area"]:
        level = "HIGH"
    elif count >= DENSITY["moderate_count"] or area_ratio >= DENSITY["moderate_area"]:
        level = "MODERATE"
    else:
        level = "LOW"

    return {
        "level": level,
        "vehicle_count": count,
        "area_ratio": round(area_ratio, 3),
        "criteria": (
            f"MODERATE if vehicles >= {DENSITY['moderate_count']} or area >= "
            f"{DENSITY['moderate_area']*100:.0f}%; HIGH if vehicles >= "
            f"{DENSITY['high_count']} or area >= {DENSITY['high_area']*100:.0f}%. "
            "Single image: movement not available."
        ),
    }


def image_risk_indicators(detections):
    """Static-image hazards. NOT a collision prediction."""
    indicators = []
    people = [d for d in detections if d["category"] == "pedestrian"]
    vehicles = [d for d in detections if d["class_id"] in VEHICLE_IDS]

    for p in people:
        px1, py1, px2, py2 = p["bbox"]
        for v in vehicles:
            vx1, vy1, vx2, vy2 = v["bbox"]
            ix = max(0, min(px2, vx2) - max(px1, vx1))
            iy = max(0, min(py2, vy2) - max(py1, vy1))
            near = ix > 0 and iy > 0
            gap_x = max(0, max(px1, vx1) - min(px2, vx2))
            gap_y = max(0, max(py1, vy1) - min(py2, vy2))
            close = gap_x < (px2 - px1) and gap_y < (py2 - py1)
            if near or close:
                indicators.append({
                    "type": "pedestrian_near_vehicle",
                    "ids": [p["id"], v["id"]],
                    "message": f"Pedestrian #{p['id']} is very close to {v['category']} #{v['id']}",
                })

    for i in range(len(vehicles)):
        for j in range(i + 1, len(vehicles)):
            a, b = vehicles[i], vehicles[j]
            ax1, ay1, ax2, ay2 = a["bbox"]
            bx1, by1, bx2, by2 = b["bbox"]
            ix = max(0, min(ax2, bx2) - max(ax1, bx1))
            iy = max(0, min(ay2, by2) - max(ay1, by1))
            inter = ix * iy
            smaller = min((ax2 - ax1) * (ay2 - ay1), (bx2 - bx1) * (by2 - by1))
            if smaller > 0 and inter / smaller > 0.3:
                indicators.append({
                    "type": "vehicles_overlapping",
                    "ids": [a["id"], b["id"]],
                    "message": f"{a['category']} #{a['id']} and {b['category']} #{b['id']} are very close or overlapping",
                })
    return indicators