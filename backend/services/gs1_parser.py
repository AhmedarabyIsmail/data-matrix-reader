from __future__ import annotations

from datetime import date
from typing import Optional


GROUP_SEPARATOR = "\x1d"


def _format_yy_mm_dd(raw: str) -> Optional[str]:
    if len(raw) != 6 or not raw.isdigit():
        return None
    yy = int(raw[0:2])
    mm = int(raw[2:4])
    dd = int(raw[4:6])
    yyyy = 2000 + yy
    # GS1 allows day=00 to indicate unknown day in month.
    if dd == 0 and 1 <= mm <= 12:
        return f"{yyyy:04d}-{mm:02d}"
    try:
        return date(yyyy, mm, dd).isoformat()
    except ValueError:
        return None


def parse_gs1_datamatrix(decoded: Optional[str]) -> dict:
    fields = {
        "raw": decoded,
        "gtin": None,
        "expiry_date": None,
        "manufacture_date": None,
        "lot_batch": None,
        "serial": None,
    }
    if not decoded:
        return fields

    i = 0
    payload = decoded
    n = len(payload)

    while i < n:
        if payload[i] == GROUP_SEPARATOR:
            i += 1
            continue

        # Fixed length AIs
        if payload.startswith("01", i) and i + 16 <= n:
            fields["gtin"] = payload[i + 2 : i + 16]
            i += 16
            continue
        if payload.startswith("17", i) and i + 8 <= n:
            fields["expiry_date"] = _format_yy_mm_dd(payload[i + 2 : i + 8])
            i += 8
            continue
        if payload.startswith("11", i) and i + 8 <= n:
            fields["manufacture_date"] = _format_yy_mm_dd(payload[i + 2 : i + 8])
            i += 8
            continue

        # Variable length AIs (terminated by GS separator or end of payload)
        if payload.startswith("10", i) or payload.startswith("21", i):
            ai = payload[i : i + 2]
            j = i + 2
            while j < n and payload[j] != GROUP_SEPARATOR:
                # Heuristic for no separator case when next known AI appears
                if (
                    payload.startswith("17", j)
                    or payload.startswith("11", j)
                    or payload.startswith("10", j)
                    or payload.startswith("21", j)
                ):
                    break
                j += 1
            value = payload[i + 2 : j]
            if ai == "10":
                fields["lot_batch"] = value
            else:
                fields["serial"] = value
            i = j
            continue

        # Unknown segment, move forward safely.
        i += 1

    return fields
