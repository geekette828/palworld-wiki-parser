import os
import re
import sys
import json
from typing import Any, Dict, List, Optional, Tuple, TypedDict, DefaultDict
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText


item_lottery_input_file = os.path.join(constants.INPUT_DIRECTORY, "Item", "DT_ItemLotteryDataTable.json")
dungeon_item_lottery_input_file = os.path.join(constants.INPUT_DIRECTORY, "Dungeon", "DT_DungeonItemLotteryDataTable.json")


ENEMY_BASE_BIOME_TO_FACTION = {
    "Volcano": "Brothers of the Eternal Pyre",
    "Grass": "Rayne Syndicate",
    "Sakurajima": "Moonflower Clan",
    "Snow": "Pal Genetic Research Unit",
    "Forest": "Free Pal Alliance",
}

HARDCODED_ITEM_NAME_OVERRIDES = {
    "TreasureMap02": "Treasure Map (Uncommon)",
    "TreasureMap03": "Treasure Map (Rare)",
    "TreasureMap04": "Treasure Map (Epic)",
}

_GRADE_NUM_RE = re.compile(r"::\s*Grade\s*(\d+)\s*$", re.IGNORECASE)
_ENUM_LEAF_RE = re.compile(r"::\s*([A-Za-z0-9_]+)\s*$")
_ENEMY_CAMP_NAME_RE = re.compile(
    r"^EnemyCamp_(?P<biome>Volcano|Grass|Sakurajima|Snow|Forest)"
    r"(?P<goal>Goal)?"
    r"(?P<tier>01|02)?"
    r"(?P<hi>_02)?$"
)

class ItemLotteryRow(TypedDict, total=False):
    FieldName: str
    SlotNo: Any
    WeightInSlot: Any
    StaticItemId: str
    MinNum: Any
    MaxNum: Any
    NumUnit: Any
    TreasureBoxGrade: str


class DungeonItemLotteryRow(TypedDict, total=False):
    SpawnAreaId: str
    Type: str
    ItemFieldLotteryName: str


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _trim(v: Any) -> str:
    return str(v or "").strip()


def _to_int(v: Any) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _to_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _parse_enum_leaf(v: Any) -> str:
    s = _trim(v)
    if not s:
        return ""
    m = _ENUM_LEAF_RE.search(s)
    if m:
        return m.group(1)
    # Fallback: if someone already gave "Normal" without namespace
    return s


def _parse_grade_number(treasure_box_grade: Any) -> str:
    s = _trim(treasure_box_grade)
    if not s:
        return ""

    m = _GRADE_NUM_RE.search(s)
    if m:
        return m.group(1)

    digits = re.findall(r"(\d+)", s)
    return digits[-1] if digits else ""

def build_enemy_base_location(field_name: str, grade_number: str) -> str:
    m = _ENEMY_CAMP_NAME_RE.match(field_name or "")
    if not m:
        return ""

    biome = m.group("biome")
    goal = m.group("goal") is not None
    tier = m.group("tier") or ""
    hi = m.group("hi") is not None

    # "02" tier OR explicit "_02" suffix means Level 60+ per your rules.
    is_level_60_plus = hi or (tier == "02")

    faction = ENEMY_BASE_BIOME_TO_FACTION.get(biome)
    if not faction:
        return ""

    chest_kind = "Golden Chest" if goal else "Generic Chest"
    prefix = "Level 60+ " if is_level_60_plus else ""
    return f"{prefix}{faction} Enemy Base ({chest_kind}: Grade {grade_number})"


def _get_item_display_name(en: EnglishText, static_item_id: Any) -> str:
    internal = _trim(static_item_id)
    if not internal:
        return ""

    if internal in HARDCODED_ITEM_NAME_OVERRIDES:
        return HARDCODED_ITEM_NAME_OVERRIDES[internal]

    name = en.get_item_name(internal)
    return name or internal


def _load_item_lottery_rows(*, input_path: str) -> Dict[str, ItemLotteryRow]:
    raw = _load_json(input_path)
    rows = extract_datatable_rows(raw, source=os.path.basename(input_path)) or {}
    out: Dict[str, ItemLotteryRow] = {}
    for row_id, row in rows.items():
        if isinstance(row, dict):
            out[str(row_id)] = row  # type: ignore[assignment]
    return out


def _load_dungeon_item_lottery_rows(*, input_path: str) -> Dict[str, DungeonItemLotteryRow]:
    raw = _load_json(input_path)
    rows = extract_datatable_rows(raw, source=os.path.basename(input_path)) or {}
    out: Dict[str, DungeonItemLotteryRow] = {}
    for row_id, row in rows.items():
        if isinstance(row, dict):
            out[str(row_id)] = row  # type: ignore[assignment]
    return out


def _format_chest_drop_block(
    *,
    chest_name: str,
    grade_number: str,
    location: str,
    rows: List[ItemLotteryRow],
    en: EnglishText,
) -> str:
    by_slot: DefaultDict[int, List[ItemLotteryRow]] = defaultdict(list)
    for r in rows:
        slot = _to_int(r.get("SlotNo"))
        by_slot[slot].append(r)

    lines: List[str] = []
    lines.append("{{Chest Drop")
    lines.append(f"|chestName = {chest_name}")
    lines.append(f"|grade = {grade_number}")
    lines.append(f"|location = {location}".rstrip())

    for slot in sorted(by_slot.keys()):
        slot_rows = by_slot[slot]

        def sort_key(rr: ItemLotteryRow) -> Tuple[float, str]:
            w = _to_float(rr.get("WeightInSlot"))
            name = _get_item_display_name(en, rr.get("StaticItemId"))
            return (-w, name.casefold())

        slot_rows_sorted = sorted(slot_rows, key=sort_key)

        idx = 0
        for rr in slot_rows_sorted:
            idx += 1

            item_name = _get_item_display_name(en, rr.get("StaticItemId"))
            min_num = _to_int(rr.get("MinNum"))
            max_num = _to_int(rr.get("MaxNum"))
            weight = _to_float(rr.get("WeightInSlot"))

            key_prefix = f"{slot}_{idx}"
            lines.append(f"  |{key_prefix}_name = {item_name}")
            lines.append(f"   |{key_prefix}_min = {min_num}")
            lines.append(f"   |{key_prefix}_max = {max_num}")
            lines.append(f"   |{key_prefix}_weight = {weight}")

    lines.append("}}")
    return "\n".join(lines)


def build_enemy_base_chest_drops_export_text(
    *,
    input_path: str = item_lottery_input_file,
) -> str:
    en = EnglishText()
    rows_by_id = _load_item_lottery_rows(input_path=input_path)

    grouped: DefaultDict[Tuple[str, str], List[ItemLotteryRow]] = defaultdict(list)

    for _, row in rows_by_id.items():
        field_name = _trim(row.get("FieldName"))
        if not field_name.startswith("EnemyCamp_"):
            continue

        grade_number = _parse_grade_number(row.get("TreasureBoxGrade"))
        if not grade_number:
            continue

        grouped[(field_name, grade_number)].append(row)

    def group_sort_key(k: Tuple[str, str]) -> Tuple[str, int]:
        fname, g = k
        return (fname.casefold(), _to_int(g))

    blocks: List[str] = []
    for (field_name, grade_number) in sorted(grouped.keys(), key=group_sort_key):
        location = build_enemy_base_location(field_name, grade_number)

        block = _format_chest_drop_block(
            chest_name=field_name,
            grade_number=grade_number,
            location=location,
            rows=grouped[(field_name, grade_number)],
            en=en,
        )

        blocks.append(block)

    return ("\n\n".join(blocks).rstrip() + "\n") if blocks else ""


def build_dungeon_chest_drops_export_text(
    *,
    dungeon_input_path: str = dungeon_item_lottery_input_file,
    item_lottery_path: str = item_lottery_input_file,
) -> str:
    """
    Export #2: Dungeons
    - DT_DungeonItemLotteryDataTable.json provides:
        - SpawnAreaId (ignore TestDebug*)
        - Type (Normal/Special)
        - ItemFieldLotteryName
    - chestName = ItemFieldLotteryName:TypeLeaf
    - ItemFieldLotteryName is used to match DT_ItemLotteryDataTable.FieldName
    - Then group by TreasureBoxGrade number (same as Enemy Base)
    """
    en = EnglishText()

    dungeon_rows_by_id = _load_dungeon_item_lottery_rows(input_path=dungeon_input_path)
    item_rows_by_id = _load_item_lottery_rows(input_path=item_lottery_path)

    item_rows_by_field: DefaultDict[str, List[ItemLotteryRow]] = defaultdict(list)
    for _, r in item_rows_by_id.items():
        field_name = _trim(r.get("FieldName"))
        if field_name:
            item_rows_by_field[field_name].append(r)

    # Which dungeon "chests" exist:
    # key: chestName, value: item_field_name
    chest_to_item_field: Dict[str, str] = {}
    for _, dr in dungeon_rows_by_id.items():
        spawn_area = _trim(dr.get("SpawnAreaId"))
        if spawn_area.startswith("TestDebug"):
            continue

        item_field = _trim(dr.get("ItemFieldLotteryName"))
        if not item_field:
            continue

        type_leaf = _parse_enum_leaf(dr.get("Type"))
        if not type_leaf:
            continue

        chest_name = f"{item_field}:{type_leaf}"
        # If duplicates exist, they should point to the same item_field anyway
        chest_to_item_field[chest_name] = item_field

    grouped: DefaultDict[Tuple[str, str], List[ItemLotteryRow]] = defaultdict(list)

    for chest_name, item_field in chest_to_item_field.items():
        matching_item_rows = item_rows_by_field.get(item_field, [])
        if not matching_item_rows:
            continue

        for ir in matching_item_rows:
            grade_number = _parse_grade_number(ir.get("TreasureBoxGrade"))
            if not grade_number:
                continue
            grouped[(chest_name, grade_number)].append(ir)

    def group_sort_key(k: Tuple[str, str]) -> Tuple[str, int]:
        chest, g = k
        return (chest.casefold(), _to_int(g))

    blocks: List[str] = []
    for (chest_name, grade_number) in sorted(grouped.keys(), key=group_sort_key):
        block = _format_chest_drop_block(
            chest_name=chest_name,
            grade_number=grade_number,
            location="",
            rows=grouped[(chest_name, grade_number)],
            en=en,
        )
        blocks.append(block)

    return ("\n\n".join(blocks).rstrip() + "\n") if blocks else ""


def build_all_chest_drop_exports() -> Dict[str, str]:
    out: Dict[str, str] = {}

    out["chest_enemy_base.txt"] = build_enemy_base_chest_drops_export_text()
    out["chest_dungeon.txt"] = build_dungeon_chest_drops_export_text()

    # Export #3 placeholder (world)
    out["chest_world.txt"] = ""

    return out
