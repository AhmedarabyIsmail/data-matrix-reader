from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes.camera import router as camera_router
from routes.detect import router as detect_router
from routes.teach import router as teach_router

app = FastAPI(title="Vision Inspection AI Trainer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(teach_router)
app.include_router(detect_router)
app.include_router(camera_router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health")
def health():
    return {"ok": True}
