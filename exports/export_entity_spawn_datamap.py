import os
import sys
import json
import re
from typing import Any, Dict, List, Tuple, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.entity_spawn import build_all_spawn_point_models, SpawnPointModel
from builders.entity_spawn_datamap import (build_all_paldex_distribution_map_models, PaldexDistributionMapModel)
force_utf8_stdout()

#Paths
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Paldex Distribution")

ALPHA_FILE_PATH = os.path.join(output_directory, "paldex_distribution_markers_alpha.json")
PREDATOR_FILE_PATH = os.path.join(output_directory, "paldex_distribution_markers_predator.json")
STANDARD_FILE_PATH = os.path.join(output_directory, "paldex_distribution_markers_standard.json")
BOUNTY_FILE_PATH = os.path.join(output_directory, "paldex_distribution_markers_bounty.json")


_KEY_SAFE_RE = re.compile(r"[^A-Za-z0-9_]+")


def write_json(path: str, data: Any) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write("\n")

def _make_title_id_from_name(name: str) -> str:
    s = str(name or "").strip()
    if s == "":
        return ""
    s = s.replace(" ", "_")
    s = _KEY_SAFE_RE.sub("", s)
    return s.strip("_")

def _spawn_xy(model: SpawnPointModel) -> Optional[Tuple[float, float]]:
    x = model.get("datamap_x")
    y = model.get("datamap_y")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return None
    return float(x), float(y)

def render_alpha_datamap(spawn_points: List[SpawnPointModel]) -> Dict[str, Any]:
    markers_out: List[Dict[str, Any]] = []
    used_id_counts: Dict[str, int] = {}

    for model in spawn_points:
        if str(model.get("variant") or "") != "Alpha":
            continue

        base_name = str(model.get("name") or "").strip()
        if base_name == "":
            continue

        xy = _spawn_xy(model)
        if not xy:
            continue
        x, y = xy

        level = model.get("level")
        level_int: Optional[int] = level if isinstance(level, int) else None

        base_marker_id = "Alpha_" + _make_title_id_from_name(base_name)
        if base_marker_id == "Alpha_":
            continue

        n = used_id_counts.get(base_marker_id, 0) + 1
        used_id_counts[base_marker_id] = n
        marker_id = base_marker_id if n == 1 else f"{base_marker_id}_{n}"

        desc = f"Lv. {level_int}" if level_int is not None else ""

        markers_out.append(
            {
                "id": marker_id,
                "x": round(x, 4),
                "y": round(y, 4),
                "name": f"Alpha {base_name}",
                "article": base_name,
                "icon": f"{base_name} icon.png",
                "description": [desc],
            }
        )

    return {
        "$schema": "https://palworld.wiki.gg/extensions/DataMaps/schemas/v17.3.json",
        "$fragment": True,
        "groups": {
            "alpha_pals": {
                "name": "Alpha Pals",
                "icon": "Alpha icon.png",
                "size": [40, 40],
                "article": "Alpha Pals",
                "isCollectible": True,
            }
        },
        "markers": {
            "alpha_pals": markers_out
        },
    }

def render_bounty_datamap(spawn_points: List[SpawnPointModel]) -> Dict[str, Any]:
    markers_out: List[Dict[str, Any]] = []
    used_id_counts: Dict[str, int] = {}

    for model in spawn_points:
        if str(model.get("variant") or "") != "Bounty Target":
            continue

        production_name = str(model.get("name") or "").strip()
        if production_name == "":
            continue

        xy = _spawn_xy(model)
        if not xy:
            continue
        x, y = xy

        level = model.get("level")
        level_int: Optional[int] = level if isinstance(level, int) else None
        desc = f"Lv. {level_int}" if level_int is not None else ""

        base_id = _make_title_id_from_name(production_name)
        if base_id == "":
            continue

        n = used_id_counts.get(base_id, 0) + 1
        used_id_counts[base_id] = n
        marker_id = base_id if n == 1 else f"{base_id}_{n}"

        markers_out.append(
            {
                "id": marker_id,
                "x": round(x, 4),
                "y": round(y, 4),
                "name": production_name,
                "article": production_name,
                "icon": f"{production_name} icon.png",
                "description": [desc],
            }
        )

    return {
        "groups": {
            "bounties": {
                "name": "Bounties",
                "icon": "Compass Bounty icon.png",
                "size": [75, 75],
                "article": "Bounty Targets",
            }
        },
        "markers": {
            "bounties": markers_out
        },
    }

def render_predator_datamap(spawn_points: List[SpawnPointModel]) -> Dict[str, Any]:
    markers_out: List[Dict[str, Any]] = []
    used_id_counts: Dict[str, int] = {}

    for model in spawn_points:
        if str(model.get("variant") or "") != "Predator":
            continue

        base_name = str(model.get("name") or "").strip()
        if base_name == "":
            continue

        xy = _spawn_xy(model)
        if not xy:
            continue
        x, y = xy

        base_id = "Predator_" + _make_title_id_from_name(base_name)
        if base_id == "Predator_":
            continue

        n = used_id_counts.get(base_id, 0) + 1
        used_id_counts[base_id] = n
        marker_id = base_id if n == 1 else f"{base_id}_{n}"

        markers_out.append(
            {
                "id": marker_id,
                "x": round(x, 4),
                "y": round(y, 4),
                "name": f"Predator {base_name}",
                "article": f"{base_name} (Predator)",
                "icon": f"{base_name} icon.png",
                "description": [""],
            }
        )

    return {
        "groups": {
            "predator_pals": {
                "name": "Predator Pals",
                "icon": "Predator icon.png",
                "size": [40, 40],
                "article": "Predator Pals",
            }
        },
        "markers": {
            "predator_pals": markers_out
        },
    }

def render_standard_distribution_datamap(
    items: List[Tuple[str, PaldexDistributionMapModel]],
) -> Dict[str, Any]:
    markers: Dict[str, Any] = {}

    for _, model in items:
        for marker_key, marker_list in (model.get("markers") or {}).items():
            markers[marker_key] = marker_list

    return {
        "markers": markers
    }

def main() -> None:
    print("🔄 Building paldex distribution marker exports...")

    spawn_points = build_all_spawn_point_models()
    print(f"🔍 Loaded {len(spawn_points)} spawn points (special)")

    standard_items = build_all_paldex_distribution_map_models()
    print(f"🔍 Loaded {len(standard_items)} pal models (standard distribution)")

    alpha_data = render_alpha_datamap(spawn_points)
    bounty_data = render_bounty_datamap(spawn_points)
    predator_data = render_predator_datamap(spawn_points)
    standard_data = render_standard_distribution_datamap(standard_items)

    write_json(ALPHA_FILE_PATH, alpha_data)
    write_json(BOUNTY_FILE_PATH, bounty_data)
    write_json(PREDATOR_FILE_PATH, predator_data)
    write_json(STANDARD_FILE_PATH, standard_data)

    print("✅ Wrote:")
    print(f"   - {ALPHA_FILE_PATH}")
    print(f"   - {BOUNTY_FILE_PATH}")
    print(f"   - {PREDATOR_FILE_PATH}")
    print(f"   - {STANDARD_FILE_PATH}")


if __name__ == "__main__":
    main()
