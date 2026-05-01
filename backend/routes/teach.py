from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.template_manager import TemplateManager
from utils.image_processing import Roi, canny_edges, decode_upload_to_bgr, resize_keep_scale, roi_crop, to_gray

router = APIRouter(prefix="/teach", tags=["teach"])
template_manager = TemplateManager()


@router.post("")
async def teach(
    image: UploadFile = File(...),
    x: int = Form(...),
    y: int = Form(...),
    width: int = Form(...),
    height: int = Form(...),
):
    try:
        file_bytes = await image.read()
        frame = decode_upload_to_bgr(file_bytes)
        resized, _, _ = resize_keep_scale(frame)
        roi = Roi(x=x, y=y, width=width, height=height).clamp(resized.shape[1], resized.shape[0])
        roi_img = roi_crop(resized, roi)
        gray = to_gray(roi_img)
        edges = canny_edges(gray)
        record = template_manager.save_template(roi=roi, roi_img=roi_img, gray=gray, edges=edges)
        return {
            "template_id": record.template_id,
            "message": "Template saved successfully.",
            "roi": {"x": roi.x, "y": roi.y, "width": roi.width, "height": roi.height},
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
