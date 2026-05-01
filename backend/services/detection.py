from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2

from services.decoding import (
    decode_datamatrix,
    decode_datamatrix_debug,
    decode_datamatrix_fast,
    decode_datamatrix_with_location,
)
from services.optimization import DEFAULT_CONFIG
from services.template_manager import TemplateRecord
from utils.image_processing import Roi, canny_edges, preprocess_for_decode, roi_crop, to_gray


@dataclass
class DetectionResult:
    bounding_box: dict
    confidence_score: float
    decoded_data: Optional[str]
    status: str


def _localize(image_bgr: np.ndarray, template: TemplateRecord) -> tuple[dict, np.ndarray, np.ndarray]:
    gray = to_gray(image_bgr)
    template_edges = cv2.imread(template.edge_path, cv2.IMREAD_GRAYSCALE)
    if template_edges is None:
        raise RuntimeError("Template edges are missing.")

    frame_edges = canny_edges(gray)
    base_match = cv2.matchTemplate(frame_edges, template_edges, cv2.TM_CCOEFF_NORMED)
    _, base_score, _, base_loc = cv2.minMaxLoc(base_match)
    best = {
        "score": float(base_score),
        "x": int(base_loc[0]),
        "y": int(base_loc[1]),
        "w": template.roi.width,
        "h": template.roi.height,
    }

    # Keep the common case fast: only trigger multi-scale search when confidence is weak.
    if best["score"] < DEFAULT_CONFIG.match_threshold:
        for scale in DEFAULT_CONFIG.template_scales:
            if scale == 1.0:
                continue
            scaled_w = max(8, int(template.roi.width * scale))
            scaled_h = max(8, int(template.roi.height * scale))
            scaled_template = cv2.resize(template_edges, (scaled_w, scaled_h), interpolation=cv2.INTER_NEAREST)
            if scaled_template.shape[0] >= frame_edges.shape[0] or scaled_template.shape[1] >= frame_edges.shape[1]:
                continue
            result = cv2.matchTemplate(frame_edges, scaled_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best["score"]:
                best = {
                    "score": float(max_val),
                    "x": int(max_loc[0]),
                    "y": int(max_loc[1]),
                    "w": scaled_w,
                    "h": scaled_h,
                }

    return best, gray, frame_edges


def detect_from_template(image_bgr: np.ndarray, template: TemplateRecord) -> DetectionResult:
    best, gray, _ = _localize(image_bgr, template)
    x, y = best["x"], best["y"]
    w, h = best["w"], best["h"]
    padded_roi = Roi(
        x=max(0, x - DEFAULT_CONFIG.max_roi_padding),
        y=max(0, y - DEFAULT_CONFIG.max_roi_padding),
        width=min(gray.shape[1] - max(0, x - DEFAULT_CONFIG.max_roi_padding), w + 2 * DEFAULT_CONFIG.max_roi_padding),
        height=min(gray.shape[0] - max(0, y - DEFAULT_CONFIG.max_roi_padding), h + 2 * DEFAULT_CONFIG.max_roi_padding),
    )

    detected = roi_crop(gray, padded_roi)
    decoded = decode_datamatrix_fast(detected)
    if decoded is None:
        prepared = preprocess_for_decode(detected)
        decoded = decode_datamatrix_fast(prepared)
        if decoded is None:
            upscaled = cv2.resize(
                prepared,
                None,
                fx=DEFAULT_CONFIG.decode_attempt_scale_up,
                fy=DEFAULT_CONFIG.decode_attempt_scale_up,
                interpolation=cv2.INTER_CUBIC,
            )
            decoded = decode_datamatrix_fast(upscaled)

    bbox = {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}
    # Heavy fallback is only worth paying for ambiguous/low-confidence matches.
    if decoded is None and best["score"] < DEFAULT_CONFIG.high_confidence_threshold:
        decoded = decode_datamatrix(detected)
    if decoded is None:
        full_decoded, full_rect, _ = decode_datamatrix_with_location(gray)
        if full_decoded is not None and full_rect is not None:
            decoded = full_decoded
            bbox = full_rect

    status = "GOOD" if decoded is not None else "BAD"
    return DetectionResult(
        bounding_box=bbox,
        confidence_score=float(best["score"]),
        decoded_data=decoded,
        status=status,
    )


def detect_from_template_with_debug(image_bgr: np.ndarray, template: TemplateRecord) -> tuple[DetectionResult, dict]:
    best, gray, frame_edges = _localize(image_bgr, template)
    x, y = best["x"], best["y"]
    w, h = best["w"], best["h"]
    padded_roi = Roi(
        x=max(0, x - DEFAULT_CONFIG.max_roi_padding),
        y=max(0, y - DEFAULT_CONFIG.max_roi_padding),
        width=min(gray.shape[1] - max(0, x - DEFAULT_CONFIG.max_roi_padding), w + 2 * DEFAULT_CONFIG.max_roi_padding),
        height=min(gray.shape[0] - max(0, y - DEFAULT_CONFIG.max_roi_padding), h + 2 * DEFAULT_CONFIG.max_roi_padding),
    )
    detected = roi_crop(gray, padded_roi)
    prepared = preprocess_for_decode(detected)
    decoded, roi_raw_attempts = decode_datamatrix_debug(detected)
    roi_preprocessed_attempts = []
    fallback_attempts = []
    fallback_rect = None
    if decoded is None:
        decoded, roi_preprocessed_attempts = decode_datamatrix_debug(prepared)
    if decoded is None:
        full_decoded, full_rect, full_attempts = decode_datamatrix_with_location(gray)
        fallback_attempts = full_attempts
        if full_decoded is not None:
            decoded = full_decoded
            fallback_rect = full_rect
    status = "GOOD" if decoded is not None else "BAD"

    debug_dir = Path("uploads/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(debug_dir / "last_frame_edges.png"), frame_edges)
    cv2.imwrite(str(debug_dir / "last_detected_roi_gray.png"), detected)
    cv2.imwrite(str(debug_dir / "last_detected_roi_preprocessed.png"), prepared)

    result_box = fallback_rect if fallback_rect is not None else {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}
    result = DetectionResult(
        bounding_box=result_box,
        confidence_score=float(best["score"]),
        decoded_data=decoded,
        status=status,
    )
    debug_data = {
        "match": best,
        "padded_roi": {
            "x": padded_roi.x,
            "y": padded_roi.y,
            "width": padded_roi.width,
            "height": padded_roi.height,
        },
        "decode_attempts_raw_roi": roi_raw_attempts,
        "decode_attempts_preprocessed_roi": roi_preprocessed_attempts,
        "full_frame_decode_attempts": fallback_attempts,
        "full_frame_decode_bbox": fallback_rect,
        "artifacts": {
            "frame_edges": str(debug_dir / "last_frame_edges.png"),
            "detected_roi_gray": str(debug_dir / "last_detected_roi_gray.png"),
            "detected_roi_preprocessed": str(debug_dir / "last_detected_roi_preprocessed.png"),
        },
    }
    return result, debug_data
