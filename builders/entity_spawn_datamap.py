import os
import sys
import json
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText
from utils.location_utils import convert_location_to_datamap_xy, dedupe_xy_points

#Paths
PALDEX_DISTRIBUTION_PATH = os.path.join(constants.INPUT_DIRECTORY, "UI", "DT_PaldexDistributionData.json")


PaldexDistributionMapModel = Dict[str, Any]

def _load_datatable_rows(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    rows = extract_datatable_rows(raw)
    if isinstance(rows, dict):
        return rows

    return {}

def build_paldex_distribution_map_model(
    pal_id: str,
    row: Dict[str, Any],
    *,
    en: EnglishText,
) -> Optional[PaldexDistributionMapModel]:
    pal_id_l = (pal_id or "").strip().lower()
    if pal_id_l.startswith("boss_") or pal_id_l.startswith("predator_"):
        return None

    base_id = pal_id.split("_", 1)[1] if "_" in pal_id else pal_id
    base_name = en.get_pal_name(base_id) or base_id
    base_name = str(base_name or "").strip()
    if base_name == "":
        return None

    day = row.get("dayTimeLocations", {}).get("locations") or []
    night = row.get("nightTimeLocations", {}).get("locations") or []

    day_pts: List[Dict[str, float]] = []
    night_pts: List[Dict[str, float]] = []

    for l in day:
        if not isinstance(l, dict):
            continue
        pt = convert_location_to_datamap_xy(l)
        if pt:
            day_pts.append(pt)

    for l in night:
        if not isinstance(l, dict):
            continue
        pt = convert_location_to_datamap_xy(l)
        if pt:
            night_pts.append(pt)

    day_pts = dedupe_xy_points(day_pts)
    night_pts = dedupe_xy_points(night_pts)

    if not day_pts and not night_pts:
        return None

    markers: Dict[str, Any] = {}
    if day_pts:
        markers[f"{base_name}_day"] = day_pts
    if night_pts:
        markers[f"{base_name}_night"] = night_pts

    return {
        "pal_id": pal_id,
        "pal_name": base_name,
        "markers": markers,
    }

def build_all_paldex_distribution_map_models() -> List[Tuple[str, PaldexDistributionMapModel]]:
    rows = _load_datatable_rows(PALDEX_DISTRIBUTION_PATH)
    en = EnglishText()

    out: List[Tuple[str, PaldexDistributionMapModel]] = []
    for pal_id, row in rows.items():
        if not isinstance(row, dict):
            continue
        model = build_paldex_distribution_map_model(str(pal_id), row, en=en)
        if model:
            out.append((str(pal_id), model))

    return out
