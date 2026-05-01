from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from services.detection import detect_from_template, detect_from_template_with_debug
from services.gs1_parser import parse_gs1_datamatrix
from services.template_manager import TemplateManager
from utils.image_processing import decode_upload_to_bgr, resize_keep_scale
from utils.timer import PerfTimer

router = APIRouter(prefix="/detect", tags=["detect"])
template_manager = TemplateManager()


@router.post("")
async def detect(image: UploadFile = File(...), template_id: Optional[str] = Query(default=None)):
    template = template_manager.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="No template found. Teach first.")

    try:
        timer = PerfTimer()
        frame = decode_upload_to_bgr(await image.read())
        resized, _, _ = resize_keep_scale(frame)
        result = detect_from_template(resized, template)
        return {
            "decoded_data": result.decoded_data,
            "parsed_data": parse_gs1_datamatrix(result.decoded_data),
            "bounding_box": result.bounding_box,
            "confidence_score": result.confidence_score,
            "processing_time_ms": round(timer.elapsed_ms(), 2),
            "status": result.status,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/debug")
async def detect_debug(image: UploadFile = File(...), template_id: Optional[str] = Query(default=None)):
    template = template_manager.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="No template found. Teach first.")

    try:
        timer = PerfTimer()
        frame = decode_upload_to_bgr(await image.read())
        resized, _, _ = resize_keep_scale(frame)
        result, debug = detect_from_template_with_debug(resized, template)
        artifacts = debug.get("artifacts", {})
        debug["artifacts"] = {
            key: f"/{str(path).replace(chr(92), '/')}" for key, path in artifacts.items()
        }
        return {
            "decoded_data": result.decoded_data,
            "parsed_data": parse_gs1_datamatrix(result.decoded_data),
            "bounding_box": result.bounding_box,
            "confidence_score": result.confidence_score,
            "processing_time_ms": round(timer.elapsed_ms(), 2),
            "status": result.status,
            "debug": debug,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
