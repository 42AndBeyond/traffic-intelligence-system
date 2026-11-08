
import os
import json
import math
import cv2
from collections import defaultdict, deque, Counter
from ultralytics import YOLO

from app.config import (
    MODEL_PATH,
    CLASSES,
    VEHICLE_IDS,
    CONF_THRESHOLD,
    VIDEO_DENSITY,
    FRAME_STRIDE,
    REPORT_DIR,
    SNAPSHOT_DIR,
)
from app.services.risk import RiskEngine


JOBS = {}
LEVELS = ["LOW", "MODERATE", "HIGH"]
MIN_TRACK_FRAMES = 5
FONT = cv2.FONT_HERSHEY_SIMPLEX
SNAP_WIDTH = 640


def classify(count, area_ratio, avg_speed):
    d = VIDEO_DENSITY

    if count >= d["high_count"] or area_ratio >= d["high_area"]:
        idx = 2
    elif count >= d["moderate_count"] or area_ratio >= d["moderate_area"]:
        idx = 1
    else:
        idx = 0

    if idx >= 1 and avg_speed is not None and avg_speed < d["slow_speed"]:
        idx = min(2, idx + 1)

    return LEVELS[idx]


def scale_objs(objs, sc):
    return {
        tid: (
            int(o["bbox"][0] * sc),
            int(o["bbox"][1] * sc),
            int(o["bbox"][2] * sc),
            int(o["bbox"][3] * sc),
            o["cat"],
        )
        for tid, o in objs.items()
    }


def draw_snapshot(img, objs, ids, t, label):
    for tid, (x1, y1, x2, y2, cat) in objs.items():
        involved = tid in ids
        color = (0, 0, 255) if involved else (150, 150, 150)

        cv2.rectangle(
            img,
            (x1, y1),
            (x2, y2),
            color,
            3 if involved else 1,
        )

        if involved:
            cv2.putText(
                img,
                f"#{tid} {cat}",
                (x1, max(40, y1 - 6)),
                FONT,
                0.6,
                color,
                2,
            )

    cv2.rectangle(
        img,
        (0, 0),
        (img.shape[1], 26),
        (0, 0, 0),
        -1,
    )

    cv2.putText(
        img,
        f"{label} | video time {t:.2f}s",
        (8, 18),
        FONT,
        0.55,
        (255, 255, 255),
        1,
    )

    return img


def save_snapshots(job_id, ev, buffer, cur):
    """Save frames from before and at the predicted risk event."""

    older = [
        b for b in buffer
        if cur["t"] - b["t"] >= 0.5
    ]

    picks = []

    if older:
        picks.append((older[0], "pre-event"))

        if len(older) > 2:
            picks.append((older[len(older) // 2], "pre-event"))

    picks.append((cur, "risk detected"))

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    for k, (p, label) in enumerate(picks, start=1):
        img = draw_snapshot(
            p["frame"].copy(),
            p["objs"],
            ev["ids"],
            p["t"],
            label,
        )

        name = f"ev_{job_id}_{ev['event_id']}_{k}.jpg"
        filepath = os.path.join(SNAPSHOT_DIR, name)

        if cv2.imwrite(filepath, img):
            ev["snapshots"].append({
                "url": f"/snapshots/{name}",
                "timestamp_sec": round(p["t"], 2),
                "label": label,
            })


def process_video(job_id, path):
    job = JOBS[job_id]

    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        cap.release()
        raise RuntimeError("Could not open the uploaded video.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if w <= 0 or h <= 0:
        cap.release()
        raise RuntimeError("The uploaded video has invalid dimensions.")

    sc = min(1.0, SNAP_WIDTH / w) if w else 1.0

    model = YOLO(MODEL_PATH)
    engine = RiskEngine()

    buffer = deque(maxlen=10)
    last_buf_t = -1.0

    history = defaultdict(lambda: deque(maxlen=10))
    info = {}
    timeline = {}

    frame_idx = 0
    processed = 0

    try:
        while True:
            ok, frame = cap.read()

            if not ok:
                break

            t = frame_idx / fps

            if frame_idx % FRAME_STRIDE == 0:
                res = model.track(
                    frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    conf=CONF_THRESHOLD,
                    classes=list(CLASSES.keys()),
                    verbose=False,
                )[0]

                vehicle_count = 0
                area = 0.0
                speeds = []

                objs = {}

                if res.boxes is not None and res.boxes.id is not None:
                    ids = res.boxes.id.int().tolist()
                    clss = res.boxes.cls.int().tolist()
                    boxes = res.boxes.xyxy.tolist()

                    for tid, c, (x1, y1, x2, y2) in zip(
                        ids, clss, boxes
                    ):
                        category = CLASSES[c]

                        objs[tid] = {
                            "bbox": (x1, y1, x2, y2),
                            "cat": category,
                        }

                        cx = (x1 + x2) / 2
                        cy = (y1 + y2) / 2

                        rec = info.setdefault(
                            tid,
                            {
                                "cats": Counter(),
                                "first": t,
                                "last": t,
                                "frames": 0,
                            },
                        )

                        rec["cats"][category] += 1
                        rec["last"] = t
                        rec["frames"] += 1

                        hist = history[tid]
                        hist.append((t, cx, cy))

                        if c in VEHICLE_IDS:
                            vehicle_count += 1
                            area += (x2 - x1) * (y2 - y1)

                            if len(hist) >= 5:
                                dt = hist[-1][0] - hist[0][0]

                                if dt > 0:
                                    dist = math.hypot(
                                        hist[-1][1] - hist[0][1],
                                        hist[-1][2] - hist[0][2],
                                    )

                                    speeds.append(dist / dt / w)

                # ---------- Risk engine ----------
                small = None

                for ev, is_new in engine.update(t, objs):
                    if is_new:
                        if small is None:
                            small = cv2.resize(
                                frame,
                                (int(w * sc), int(h * sc)),
                            )

                        cur = {
                            "t": t,
                            "frame": small,
                            "objs": scale_objs(objs, sc),
                        }

                        save_snapshots(
                            job_id,
                            ev,
                            buffer,
                            cur,
                        )

                # Maintain approximately 2.5 seconds of
                # previous snapshots, sampling every 0.25 seconds.
                if t - last_buf_t >= 0.25:
                    if small is None:
                        small = cv2.resize(
                            frame,
                            (int(w * sc), int(h * sc)),
                        )

                    buffer.append({
                        "t": t,
                        "frame": small,
                        "objs": scale_objs(objs, sc),
                    })

                    last_buf_t = t

                # ---------- Traffic density ----------
                avg_speed = (
                    sum(speeds) / len(speeds)
                    if speeds else None
                )

                area_ratio = area / (w * h) if w * h else 0

                level = classify(
                    vehicle_count,
                    area_ratio,
                    avg_speed,
                )

                sec = int(t)

                timeline[sec] = {
                    "time": sec,
                    "level": level,
                    "vehicles": vehicle_count,
                    "avg_speed": (
                        round(avg_speed, 3)
                        if avg_speed is not None
                        else None
                    ),
                }

                processed += 1

            frame_idx += 1

            if frame_idx % 10 == 0 and total:
                job["progress"] = min(
                    99,
                    int(frame_idx / total * 100),
                )

    finally:
        cap.release()

    # ---------- Build tracking report ----------
    tracks = []

    for tid, rec in info.items():
        if rec["frames"] < MIN_TRACK_FRAMES:
            continue

        tracks.append({
            "id": tid,
            "category": rec["cats"].most_common(1)[0][0],
            "first_seen": round(rec["first"], 2),
            "last_seen": round(rec["last"], 2),
            "frames": rec["frames"],
        })

    tracks.sort(key=lambda x: x["id"])

    by_cat = Counter(t["category"] for t in tracks)

    tl = [
        timeline[k]
        for k in sorted(timeline)
    ]

    level_counts = Counter(x["level"] for x in tl)
    n = len(tl) or 1

    summary = {
        lv: round(level_counts.get(lv, 0) / n * 100)
        for lv in LEVELS
    }

    overall = (
        max(LEVELS, key=lambda lv: level_counts.get(lv, 0))
        if tl else "LOW"
    )

    # ---------- Build risk report ----------
    events = engine.public_events()

    risk_summary = {
        "total_events": len(events),
        "MODERATE": sum(
            e["severity"] == "MODERATE" for e in events
        ),
        "HIGH": sum(
            e["severity"] == "HIGH" for e in events
        ),
        "CRITICAL": sum(
            e["severity"] == "CRITICAL" for e in events
        ),
    }

    report = {
        "job_id": job_id,
        "frames_read": frame_idx,
        "frames_processed": processed,
        "fps": round(fps, 2),
        "duration_sec": round(frame_idx / fps, 2),
        "resolution": {
            "width": w,
            "height": h,
        },
        "unique_objects": len(tracks),
        "objects_by_category": dict(by_cat),
        "tracks": tracks,
        "density_timeline": tl,
        "density_summary_percent": summary,
        "overall_density": overall,
        "density_criteria": (
            f"MODERATE: >= {VIDEO_DENSITY['moderate_count']} vehicles or "
            f">= {VIDEO_DENSITY['moderate_area']*100:.0f}% area; HIGH: >= "
            f"{VIDEO_DENSITY['high_count']} vehicles or >= "
            f"{VIDEO_DENSITY['high_area']*100:.0f}% area. Level goes up one step when "
            "average vehicle speed is slow (relative, in-frame speed)."
        ),
        "risk_events": events,
        "risk_summary": risk_summary,
        "risk_note": (
            "Predicted risks are rule-based estimates from tracked motion. "
            "Distances, speeds and time-to-collision are uncalibrated and relative. "
            "They do not guarantee that an accident will occur. "
            "Accident detection is not performed."
        ),
    }

    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    with open(os.path.join(REPORT_DIR, f"{job_id}.json"), "w") as f:
        json.dump(report, f, indent=2)

    return report


def run_job(job_id, path):
    job = JOBS[job_id]
    job["status"] = "processing"

    try:
        report = process_video(job_id, path)

        job.update(
            status="done",
            progress=100,
            report=report,
        )

    except Exception as e:
        job.update(
            status="error",
            error=str(e),
        )

    finally:
        try:
            os.remove(path)
        except OSError:
            pass
