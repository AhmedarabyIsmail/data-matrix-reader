from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DetectionConfig:
    match_threshold: float = 0.45
    high_confidence_threshold: float = 0.9
    decode_attempt_scale_up: float = 1.5
    max_roi_padding: int = 10
    template_scales: tuple = (0.85, 1.0, 1.15)


DEFAULT_CONFIG = DetectionConfig()
