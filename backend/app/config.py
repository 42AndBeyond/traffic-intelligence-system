import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)

MODEL_PATH = os.path.join(ROOT_DIR, "models", "yolov8n.pt")
UPLOAD_DIR = os.path.join(ROOT_DIR, "uploads")
SNAPSHOT_DIR = os.path.join(ROOT_DIR, "snapshots")

# COCO class IDs we care about
CLASSES = {
    0: "pedestrian",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
VEHICLE_IDS = {1, 2, 3, 5, 7}

CONF_THRESHOLD = 0.35

# Traffic density thresholds (configurable)
# Image mode: based on vehicle count + occupied area ratio
DENSITY = {
    "moderate_count": 6,
    "high_count": 15,
    "moderate_area": 0.15,
    "high_area": 0.35,
}

MAX_IMAGE_MB = 10
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

REPORT_DIR = os.path.join(ROOT_DIR, "uploads", "reports")

MAX_VIDEO_MB = 100
ALLOWED_VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv"}

# 1 = process every frame. Use 2 if processing is too slow on your PC.
FRAME_STRIDE = 1

# Video density: count + area + movement (speed in frame-widths per second)
VIDEO_DENSITY = {
    "moderate_count": 5,
    "high_count": 12,
    "moderate_area": 0.12,
    "high_area": 0.30,
    "slow_speed": 0.04,
}