import os
import json
import uuid
import cv2
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.config import UPLOAD_DIR, REPORT_DIR, MAX_VIDEO_MB, ALLOWED_VIDEO_EXT
from app.services.video_processor import JOBS, run_job

router = APIRouter(prefix="/api/video", tags=["Video"])


@router.post("/upload")
async def upload_video(background: BackgroundTasks, file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_VIDEO_EXT:
        raise HTTPException(400, "Allowed video types: mp4, avi, mov, mkv")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    job_id = uuid.uuid4().hex[:10]
    path = os.path.join(UPLOAD_DIR, f"{job_id}{ext}")

    limit = MAX_VIDEO_MB * 1024 * 1024
    size, too_big = 0, False
    with open(path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                too_big = True
                break
            f.write(chunk)

    if too_big:
        os.remove(path)
        raise HTTPException(400, f"Video larger than {MAX_VIDEO_MB} MB")

    cap = cv2.VideoCapture(path)
    readable = cap.isOpened()
    cap.release()
    if not readable:
        os.remove(path)
        raise HTTPException(400, "Could not read video file")

    JOBS[job_id] = {"status": "queued", "progress": 0, "report": None, "error": None}
    background.add_task(run_job, job_id, path)
    return {"job_id": job_id, "status": "queued"}


@router.get("/{job_id}/status")
def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {"job_id": job_id, "status": job["status"],
            "progress": job["progress"], "error": job["error"]}


@router.get("/{job_id}/report")
def report(job_id: str):
    job = JOBS.get(job_id)
    if job:
        if job["status"] != "done":
            raise HTTPException(409, "Report not ready yet")
        return job["report"]
    if job_id.isalnum():
        p = os.path.join(REPORT_DIR, f"{job_id}.json")
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    raise HTTPException(404, "Report not found")