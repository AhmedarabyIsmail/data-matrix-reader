from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from utils.image_processing import Roi


TEMPLATES_DIR = Path("backend/templates")
META_FILE = TEMPLATES_DIR / "templates.json"


@dataclass
class TemplateRecord:
    template_id: str
    roi: Roi
    image_path: str
    gray_path: str
    edge_path: str
    created_at: str

    @staticmethod
    def from_dict(data: dict) -> "TemplateRecord":
        return TemplateRecord(
            template_id=data["template_id"],
            roi=Roi(**data["roi"]),
            image_path=data["image_path"],
            gray_path=data["gray_path"],
            edge_path=data["edge_path"],
            created_at=data["created_at"],
        )


class TemplateManager:
    def __init__(self) -> None:
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        if not META_FILE.exists():
            META_FILE.write_text("[]", encoding="utf-8")

    def _read_all(self) -> list[TemplateRecord]:
        rows = json.loads(META_FILE.read_text(encoding="utf-8"))
        return [TemplateRecord.from_dict(row) for row in rows]

    def _write_all(self, rows: list[TemplateRecord]) -> None:
        payload = []
        for row in rows:
            raw = asdict(row)
            raw["roi"] = asdict(row.roi)
            payload.append(raw)
        META_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def save_template(self, roi: Roi, roi_img: np.ndarray, gray: np.ndarray, edges: np.ndarray) -> TemplateRecord:
        template_id = str(uuid.uuid4())[:8]
        base = TEMPLATES_DIR / template_id
        image_path = f"{base}_roi.png"
        gray_path = f"{base}_gray.png"
        edge_path = f"{base}_edges.png"
        cv2.imwrite(image_path, roi_img)
        cv2.imwrite(gray_path, gray)
        cv2.imwrite(edge_path, edges)
        record = TemplateRecord(
            template_id=template_id,
            roi=roi,
            image_path=image_path,
            gray_path=gray_path,
            edge_path=edge_path,
            created_at=str(np.datetime64("now")),
        )
        rows = self._read_all()
        rows.append(record)
        self._write_all(rows)
        return record

    def get_template(self, template_id: Optional[str] = None) -> Optional[TemplateRecord]:
        rows = self._read_all()
        if not rows:
            return None
        if template_id is None:
            return rows[-1]
        for row in rows:
            if row.template_id == template_id:
                return row
        return None

    def list_templates(self) -> list[TemplateRecord]:
        return self._read_all()
