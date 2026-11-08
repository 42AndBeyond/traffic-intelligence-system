
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

# Detection confidence
# Temporarily lowered to improve detection of vehicles in difficult footage.
CONF_THRESHOLD = 0.20

# Image traffic density thresholds
DENSITY = {
    "moderate_count": 6,
    "high_count": 15,
    "moderate_area": 0.15,
    "high_area": 0.35,
}

MAX_IMAGE_MB = 10
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

# Video settings
MAX_VIDEO_MB = 100

ALLOWED_VIDEO_EXT = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
}

REPORT_DIR = os.path.join(ROOT_DIR, "uploads", "reports")

# Process every frame
FRAME_STRIDE = 1

# Video traffic density thresholds
# Speed is relative and measured in frame-widths per second.
VIDEO_DENSITY = {
    "moderate_count": 5,
    "high_count": 12,
    "moderate_area": 0.12,
    "high_area": 0.30,
    "slow_speed": 0.04,
}

# Risk engine
# Distances are measured in approximate object-widths.
# Speeds and TTC are uncalibrated relative estimates.
RISK = {
    "max_gap": 4.0,
    "min_closing": 0.3,
    "close_gap": 1.2,
    "near_gap": 2.5,

    "ttc_critical": 1.0,
    "ttc_high": 2.0,
    "ttc_warn": 3.5,

    "fast_closing": 1.5,

    "brake_min_speed": 0.5,
    "brake_ratio": 0.35,

    "moderate": 40,
    "high": 60,
    "critical": 80,

    "event_cooldown": 3.0,
}
