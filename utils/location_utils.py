from typing import Any, Dict, List, Optional


_CONVERT_X_OFFSET = 158000.0
_CONVERT_Y_OFFSET = 123888.0
_CONVERT_DIVISOR = 459.0


def safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None


def convert_location_to_datamap_xy(loc: Dict[str, Any]) -> Optional[Dict[str, float]]:
    if not isinstance(loc, dict):
        return None

    data_x = safe_float(loc.get("Y"))
    data_y = safe_float(loc.get("X"))

    if data_x is None or data_y is None:
        return None

    return {
        "x": round((data_x - _CONVERT_X_OFFSET) / _CONVERT_DIVISOR, 4),
        "y": round((data_y + _CONVERT_Y_OFFSET) / _CONVERT_DIVISOR, 4),
    }


def convert_location_to_wiki_coords(loc: Dict[str, Any]) -> Optional[str]:
    pt = convert_location_to_datamap_xy(loc)
    if not pt:
        return None

    x = int(round(pt["x"]))
    y = int(round(pt["y"]))
    return f"({x}, {y})"


def dedupe_xy_points(points: List[Dict[str, float]]) -> List[Dict[str, float]]:
    seen = set()
    out: List[Dict[str, float]] = []

    for p in points:
        x = p.get("x")
        y = p.get("y")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue

        key = (float(x), float(y))
        if key in seen:
            continue
        seen.add(key)
        out.append({"x": float(x), "y": float(y)})

    return out


def dedupe_strings(values: List[str]) -> List[str]:
    seen = set()
    out = []
    for v in values:
        s = str(v or "").strip()
        if s == "":
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out
