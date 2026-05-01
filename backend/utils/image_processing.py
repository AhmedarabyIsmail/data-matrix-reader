from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np


TARGET_SIZE: Tuple[int, int] = (640, 480)


@dataclass
class Roi:
    x: int
    y: int
    width: int
    height: int

    def clamp(self, max_w: int, max_h: int) -> "Roi":
        x = max(0, min(self.x, max_w - 1))
        y = max(0, min(self.y, max_h - 1))
        width = max(1, min(self.width, max_w - x))
        height = max(1, min(self.height, max_h - y))
        return Roi(x=x, y=y, width=width, height=height)


def decode_upload_to_bgr(file_bytes: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(file_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Invalid image data.")
    return image


def resize_keep_scale(image: np.ndarray, size: Tuple[int, int] = TARGET_SIZE) -> tuple[np.ndarray, float, float]:
    src_h, src_w = image.shape[:2]
    dst_w, dst_h = size
    resized = cv2.resize(image, (dst_w, dst_h), interpolation=cv2.INTER_AREA)
    scale_x = dst_w / float(src_w)
    scale_y = dst_h / float(src_h)
    return resized, scale_x, scale_y


def to_gray(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def roi_crop(image: np.ndarray, roi: Roi) -> np.ndarray:
    return image[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width].copy()


def canny_edges(gray: np.ndarray) -> np.ndarray:
    return cv2.Canny(gray, 80, 180)


def preprocess_for_decode(gray_roi: np.ndarray) -> np.ndarray:
    denoised = cv2.GaussianBlur(gray_roi, (3, 3), 0)
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary
