from __future__ import annotations

from typing import Iterable, Optional, Tuple

import cv2
import numpy as np
from pylibdmtx.pylibdmtx import decode


def _as_rgb(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def _decode_once(image: np.ndarray, timeout_ms: int = 10) -> Optional[str]:
    if image is None or image.size == 0:
        return None
    decoded_items = decode(_as_rgb(image), timeout=timeout_ms)
    if not decoded_items:
        return None
    return decoded_items[0].data.decode("utf-8", errors="ignore")


def _order_points(points: np.ndarray) -> np.ndarray:
    pts = points.astype(np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = pts[np.argmin(s)]
    ordered[2] = pts[np.argmax(s)]
    ordered[1] = pts[np.argmin(diff)]
    ordered[3] = pts[np.argmax(diff)]
    return ordered


def _perspective_rectify(gray: np.ndarray) -> Optional[np.ndarray]:
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 60, 180)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    img_area = gray.shape[0] * gray.shape[1]
    best_quad = None
    best_area = 0.0

    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        area = cv2.contourArea(approx)
        if area < img_area * 0.04:
            continue
        if area > best_area:
            best_area = area
            best_quad = approx.reshape(4, 2)

    if best_quad is None:
        return None

    src = _order_points(best_quad)
    width_a = np.linalg.norm(src[2] - src[3])
    width_b = np.linalg.norm(src[1] - src[0])
    height_a = np.linalg.norm(src[1] - src[2])
    height_b = np.linalg.norm(src[0] - src[3])
    max_w = int(max(width_a, width_b))
    max_h = int(max(height_a, height_b))
    if max_w < 12 or max_h < 12:
        return None

    dst = np.array([[0, 0], [max_w - 1, 0], [max_w - 1, max_h - 1], [0, max_h - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(gray, matrix, (max_w, max_h))
    return warped


def _variant_images(gray: np.ndarray) -> Iterable[Tuple[str, np.ndarray]]:
    yield "gray", gray
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    yield "otsu", otsu
    yield "otsu_invert", cv2.bitwise_not(otsu)
    yield "adaptive", cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
    yield "gaussian", cv2.GaussianBlur(gray, (3, 3), 0)
    rectified = _perspective_rectify(gray)
    if rectified is not None:
        yield "perspective_rectified", rectified
        _, rect_otsu = cv2.threshold(rectified, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        yield "perspective_rectified_otsu", rect_otsu


def decode_datamatrix_debug(gray_or_binary: np.ndarray) -> tuple[Optional[str], list[dict]]:
    if gray_or_binary is None or gray_or_binary.size == 0:
        return None, [{"variant": "input", "success": False, "reason": "empty_image"}]

    gray = (
        gray_or_binary
        if len(gray_or_binary.shape) == 2
        else cv2.cvtColor(gray_or_binary, cv2.COLOR_BGR2GRAY)
    )
    attempts = []
    for name, variant in _variant_images(gray):
        decoded = _decode_once(variant, timeout_ms=8)
        success = decoded is not None
        attempts.append({"variant": name, "scale": 1.0, "success": success})
        if success:
            return decoded, attempts

    upscaled = cv2.resize(gray, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
    for name, variant in _variant_images(upscaled):
        decoded = _decode_once(variant, timeout_ms=12)
        success = decoded is not None
        attempts.append({"variant": name, "scale": 1.8, "success": success})
        if success:
            return decoded, attempts
    return None, attempts


def decode_datamatrix_with_location(gray_or_binary: np.ndarray) -> tuple[Optional[str], Optional[dict], list[dict]]:
    if gray_or_binary is None or gray_or_binary.size == 0:
        return None, None, [{"variant": "input", "success": False, "reason": "empty_image"}]

    gray = (
        gray_or_binary
        if len(gray_or_binary.shape) == 2
        else cv2.cvtColor(gray_or_binary, cv2.COLOR_BGR2GRAY)
    )
    attempts = []
    for scale, source in ((1.0, gray), (1.8, cv2.resize(gray, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC))):
        for name, variant in _variant_images(source):
            timeout_ms = 10 if scale == 1.0 else 15
            items = decode(_as_rgb(variant), timeout=timeout_ms)
            success = len(items) > 0
            attempts.append({"variant": name, "scale": scale, "success": success})
            if success:
                first = items[0]
                text = first.data.decode("utf-8", errors="ignore")
                rect = first.rect
                rect_data = {
                    "x": int(rect.left / scale),
                    "y": int(rect.top / scale),
                    "width": int(rect.width / scale),
                    "height": int(rect.height / scale),
                }
                return text, rect_data, attempts
    return None, None, attempts


def decode_datamatrix_fast(gray_or_binary: np.ndarray) -> Optional[str]:
    if gray_or_binary is None or gray_or_binary.size == 0:
        return None

    gray = (
        gray_or_binary
        if len(gray_or_binary.shape) == 2
        else cv2.cvtColor(gray_or_binary, cv2.COLOR_BGR2GRAY)
    )
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    for candidate in (gray, otsu):
        decoded = _decode_once(candidate, timeout_ms=6)
        if decoded is not None:
            return decoded

    upscaled = cv2.resize(otsu, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    return _decode_once(upscaled, timeout_ms=8)


def decode_datamatrix(gray_or_binary: np.ndarray) -> Optional[str]:
    decoded, _ = decode_datamatrix_debug(gray_or_binary)
    return decoded
