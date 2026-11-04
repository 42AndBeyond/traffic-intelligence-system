import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AAPP Traffic Intelligence API", version="0.1.0")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("../snapshots", exist_ok=True)
os.makedirs("../uploads", exist_ok=True)
app.mount("/snapshots", StaticFiles(directory="../snapshots"), name="snapshots")


@app.get("/health")
def health():
    return {"status": "ok"}
