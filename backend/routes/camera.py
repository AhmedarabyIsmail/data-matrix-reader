from __future__ import annotations

import os
import threading
import time
from typing import Any, Optional

import cv2
from fastapi import APIRouter, HTTPException

from services.detection import detect_from_template
from services.gs1_parser import parse_gs1_datamatrix
from services.template_manager import TemplateManager
from utils.image_processing import resize_keep_scale
from utils.timer import PerfTimer

router = APIRouter(prefix="/camera", tags=["camera"])
template_manager = TemplateManager()

_running = False
_worker: Optional[threading.Thread] = None
_last_result: dict[str, Any] = {}


def _camera_loop(camera_url: str, template_id: Optional[str]) -> None:
    global _running, _last_result
    cap = cv2.VideoCapture(camera_url)
    frame_count = 0
    while _running and cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.01)
            continue

        frame_count += 1
        if frame_count % 2 != 0:
            continue

        template = template_manager.get_template(template_id)
        if template is None:
            _last_result = {"status": "BAD", "message": "No template loaded."}
            continue

        timer = PerfTimer()
        resized, _, _ = resize_keep_scale(frame)
        detection = detect_from_template(resized, template)
        _last_result = {
            "decoded_data": detection.decoded_data,
            "parsed_data": parse_gs1_datamatrix(detection.decoded_data),
            "bounding_box": detection.bounding_box,
            "confidence_score": detection.confidence_score,
            "processing_time_ms": round(timer.elapsed_ms(), 2),
            "status": detection.status,
        }

    cap.release()


@router.get("/start")
def start_camera(template_id: Optional[str] = None):
    global _running, _worker
    if _running:
        return {"message": "Camera already running."}

    camera_url = os.getenv("CAMERA_URL", "0")
    _running = True
    _worker = threading.Thread(target=_camera_loop, args=(camera_url, template_id), daemon=True)
    _worker.start()
    return {"message": "Camera started.", "camera_url": camera_url}


@router.get("/stop")
def stop_camera():
    global _running
    _running = False
    return {"message": "Camera stopped."}


@router.get("/status")
def camera_status():
    if not _running:
        raise HTTPException(status_code=400, detail="Camera is not running.")
    return _last_result
