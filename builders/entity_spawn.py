import os
import sys
import json
import re
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText
from utils.location_utils import (convert_location_to_datamap_xy,  convert_location_to_wiki_coords,  dedupe_strings)

#Paths
BOSS_SPAWNER_PATH = os.path.join(constants.INPUT_DIRECTORY, "UI", "DT_BossSpawnerLoactionData.json")
PALDEX_DISTRIBUTION_PATH = os.path.join(constants.INPUT_DIRECTORY, "UI", "DT_PaldexDistributionData.json")


_BOSS_PREFIX_RE = re.compile(r"^(?:boss_|BOSS_)", re.IGNORECASE)

SpawnPointModel = Dict[str, Any]

def _load_datatable_rows(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    rows = extract_datatable_rows(raw)
    if isinstance(rows, dict):
        return rows

    return {}

def _load_rows_raw_rows_key(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list) and raw:
        first = raw[0]
        if isinstance(first, dict):
            rows = first.get("Rows")
            if isinstance(rows, dict):
                return rows

    if isinstance(raw, dict):
        rows = raw.get("Rows")
        if isinstance(rows, dict):
            return rows

    return {}

def _normalize_boss_character_id(character_id: str) -> str:
    s = (character_id or "").strip()
    if s == "":
        return ""
    return _BOSS_PREFIX_RE.sub("", s).strip()

def _load_human_production_name_map() -> Dict[str, str]:
    rows = _load_rows_raw_rows_key(constants.EN_HUMAN_NAME_FILE)
    out: Dict[str, str] = {}

    for key, row in rows.items():
        if not isinstance(row, dict):
            continue

        text_data = row.get("TextData")
        if not isinstance(text_data, dict):
            continue

        name = text_data.get("LocalizedString") or text_data.get("SourceString") or ""
        name = str(name).strip()
        if name:
            out[str(key)] = name

    return out

def _level_to_int(v: Any) -> Optional[int]:
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    try:
        if v is None:
            return None
        return int(float(str(v)))
    except Exception:
        return None

def build_all_spawn_point_models() -> List[SpawnPointModel]:
    en = EnglishText()
    human_name_map = _load_human_production_name_map()

    out: List[SpawnPointModel] = []

    boss_rows = _load_datatable_rows(BOSS_SPAWNER_PATH)
    for _, row in boss_rows.items():
        if not isinstance(row, dict):
            continue

        character_id = str(row.get("CharacterID") or "").strip()
        if character_id == "":
            continue

        loc = row.get("Location")
        if not isinstance(loc, dict):
            continue

        datamap_pt = convert_location_to_datamap_xy(loc)
        wiki_coords = convert_location_to_wiki_coords(loc)
        if not datamap_pt or not wiki_coords:
            continue

        level_int = _level_to_int(row.get("Level"))

        if character_id.strip().lower() == "human":
            spawner_id = str(row.get("SpawnerID") or "").strip()
            if spawner_id == "":
                continue

            name_key = f"NAME_{spawner_id}"
            production_name = str(human_name_map.get(name_key) or "").strip()
            if production_name == "":
                continue

            out.append(
                {
                    "source": "boss_spawner",
                    "variant": "Bounty Target",
                    "name": production_name,
                    "level": level_int,
                    "coords": wiki_coords,
                    "datamap_x": datamap_pt["x"],
                    "datamap_y": datamap_pt["y"],
                }
            )
            continue

        base_id = _normalize_boss_character_id(character_id)
        base_name = en.get_pal_name(base_id) or base_id
        base_name = str(base_name or "").strip()
        if base_name == "":
            continue

        out.append(
            {
                "source": "boss_spawner",
                "variant": "Alpha",
                "name": base_name,
                "level": level_int,
                "coords": wiki_coords,
                "datamap_x": datamap_pt["x"],
                "datamap_y": datamap_pt["y"],
            }
        )

    paldex_rows = _load_datatable_rows(PALDEX_DISTRIBUTION_PATH)
    for pal_id, row in paldex_rows.items():
        pal_id_str = str(pal_id or "").strip()
        if pal_id_str == "":
            continue

        if not pal_id_str.lower().startswith("predator_"):
            continue

        if not isinstance(row, dict):
            continue

        base_id = pal_id_str.split("_", 1)[1] if "_" in pal_id_str else pal_id_str
        base_name = en.get_pal_name(base_id) or base_id
        base_name = str(base_name or "").strip()
        if base_name == "":
            continue

        day = row.get("dayTimeLocations", {}).get("locations") or []
        night = row.get("nightTimeLocations", {}).get("locations") or []

        coords_list: List[str] = []
        datamap_points: List[Dict[str, float]] = []

        for l in day:
            if not isinstance(l, dict):
                continue
            c = convert_location_to_wiki_coords(l)
            pt = convert_location_to_datamap_xy(l)
            if c and pt:
                coords_list.append(c)
                datamap_points.append(pt)

        for l in night:
            if not isinstance(l, dict):
                continue
            c = convert_location_to_wiki_coords(l)
            pt = convert_location_to_datamap_xy(l)
            if c and pt:
                coords_list.append(c)
                datamap_points.append(pt)

        coords_list = dedupe_strings(coords_list)
        if not coords_list:
            continue

        pt_by_coords: Dict[str, Dict[str, float]] = {}
        for l in day + night:
            if not isinstance(l, dict):
                continue
            c = convert_location_to_wiki_coords(l)
            pt = convert_location_to_datamap_xy(l)
            if c and pt and c not in pt_by_coords:
                pt_by_coords[c] = pt

        for c in coords_list:
            pt = pt_by_coords.get(c)
            if not pt:
                continue

            out.append(
                {
                    "source": "paldex_distribution",
                    "variant": "Predator",
                    "name": base_name,
                    "level": None,
                    "coords": c,
                    "datamap_x": pt["x"],
                    "datamap_y": pt["y"],
                }
            )

    return out
