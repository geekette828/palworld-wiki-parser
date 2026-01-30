import os
import sys
import json
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.json_datatable_utils import extract_datatable_rows


field_lottery_input_file = os.path.join(constants.INPUT_DIRECTORY, "Common", "DT_FieldLotteryNameDataTable.json")
item_lottery_input_file = os.path.join(constants.INPUT_DIRECTORY, "Item", "DT_ItemLotteryDataTable.json")
dungeon_item_lottery_input_file = os.path.join(constants.INPUT_DIRECTORY, "Dungeon", "DT_DungeonItemLotteryDataTable.json")

def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _to_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

def _load_rows(path: str) -> Dict[str, Any]:
    raw = _load_json(path)
    return extract_datatable_rows(raw, source=os.path.basename(path)) or {}

def build_chest_related_field_names() -> set[str]:
    allowed: set[str] = set()

    # EnemyCamp_* from item lottery
    item_rows = _load_rows(item_lottery_input_file)
    for _, r in item_rows.items():
        if not isinstance(r, dict):
            continue
        field_name = str(r.get("FieldName") or "").strip()
        if field_name.startswith("EnemyCamp_") or field_name.startswith("Oilrig_"):
            allowed.add(field_name)

    # Dungeon spawner names (ItemFieldLotteryName) excluding TestDebug*
    dungeon_rows = _load_rows(dungeon_item_lottery_input_file)
    for _, r in dungeon_rows.items():
        if not isinstance(r, dict):
            continue
        spawn_area = str(r.get("SpawnAreaId") or "").strip()
        if spawn_area.startswith("TestDebug"):
            continue
        item_field = str(r.get("ItemFieldLotteryName") or "").strip()
        if item_field:
            allowed.add(item_field)

    return allowed

def build_field_lottery_slot_chances_json(
    *,
    input_path: str = field_lottery_input_file,
    chest_only: bool = True,
) -> Dict[str, Dict[str, float]]:
    raw = _load_json(input_path)
    rows = extract_datatable_rows(raw, source=os.path.basename(input_path)) or {}

    allowed = build_chest_related_field_names() if chest_only else None

    out: Dict[str, Dict[str, float]] = {}

    for field_name in sorted(rows.keys(), key=str.casefold):
        if allowed is not None and field_name not in allowed:
            continue

        row = rows.get(field_name)
        if not isinstance(row, dict):
            continue

        slot_map: Dict[str, float] = {}

        for slot_no in range(1, 16):
            key = f"ItemSlot{slot_no}_ProbabilityPercent"
            if key not in row:
                continue
            prob = _to_float(row.get(key))
            slot_map[str(slot_no)] = prob

        if slot_map:
            out[field_name] = slot_map

    return out


def build_field_lottery_slot_chances_json_text(
    *,
    input_path: str = field_lottery_input_file,
    chest_only: bool = True,
    indent: int = 2,
) -> str:
    data = build_field_lottery_slot_chances_json(
        input_path=input_path,
        chest_only=chest_only,
    )

    # Stable, paste-friendly JSON for Data: namespace
    text = json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=True)
    return text.rstrip() + "\n"


