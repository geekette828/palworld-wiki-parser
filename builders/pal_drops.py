import os
import sys
import json
from typing import Any, Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText

param_input_file = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json")
drop_input_file = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalDropItem.json")


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def zukan_no(zukan_index: Any, zukan_suffix: Any) -> str:
    if zukan_index is None:
        return ""
    try:
        idx = int(zukan_index)
    except (TypeError, ValueError):
        return ""

    if idx < 0:
        return ""

    base = str(idx).zfill(3)

    suf = "" if zukan_suffix is None else str(zukan_suffix).strip()
    if suf == "":
        return base
    return f"{base}{suf}"


def format_chance(rate_value) -> str:
    try:
        f = float(rate_value)
    except Exception:
        return str(rate_value)

    if f.is_integer():
        return str(int(f))
    return str(f).rstrip("0").rstrip(".")


def get_pal_display_name(en: EnglishText, pal_id: str) -> str:
    pal_id = str(pal_id).strip()
    name = en.get_pal_name(pal_id)
    return name if name else pal_id


def get_item_display_name(en: EnglishText, item_id: str) -> str:
    item_id = str(item_id).strip()
    name = en.get_item_name(item_id)
    return name if name else item_id


def extract_drop_list(drop_row: dict, en: EnglishText) -> str:
    if not isinstance(drop_row, dict):
        return ""

    parts = []
    for i in range(1, 11):
        item_id = drop_row.get(f"ItemId{i}")
        rate = drop_row.get(f"Rate{i}")
        min_qty = drop_row.get(f"min{i}")
        max_qty = drop_row.get(f"Max{i}")

        if not item_id or str(item_id).lower() == "none":
            continue

        try:
            rate_f = float(rate)
        except Exception:
            rate_f = 0.0

        if rate_f <= 0:
            continue

        try:
            min_int = int(min_qty)
            max_int = int(max_qty)
        except Exception:
            continue

        if min_int <= 0 and max_int <= 0:
            continue

        item_name = get_item_display_name(en, item_id)

        qty_text = str(min_int) if min_int == max_int else f"{min_int}-{max_int}"
        chance_text = format_chance(rate)

        parts.append(f"{item_name}*{qty_text}@{chance_text}")

    return "; ".join(parts)


def index_drop_rows_by_character_id(drop_rows: dict) -> dict:
    by_id = {}
    for _, row in (drop_rows or {}).items():
        if not isinstance(row, dict):
            continue

        character_id = row.get("CharacterID")
        if not character_id:
            continue

        level = row.get("Level", 0)
        try:
            level_int = int(level)
        except Exception:
            level_int = 0

        if level_int != 0:
            continue

        by_id[str(character_id).strip()] = row

    return by_id


def build_pal_order(param_rows: dict) -> List[str]:
    pal_order = []
    for key, row in (param_rows or {}).items():
        if not isinstance(key, str):
            continue
        if not key.startswith("BOSS_"):
            continue

        base = key.replace("BOSS_", "")
        normal = param_rows.get(base)
        if not isinstance(normal, dict):
            continue

        pal_no = zukan_no(normal.get("ZukanIndex"), normal.get("ZukanIndexSuffix"))
        if pal_no == "":
            continue

        pal_order.append((pal_no, base))

    pal_order.sort(key=lambda x: (int(x[0][:3]), x[0][3:]))
    return [base for _, base in pal_order]


def build_pal_drop_wikitext(
    base: str,
    *,
    param_rows: dict,
    drops_by_character_id: dict,
    en: EnglishText,
) -> str:
    pal_display_name = get_pal_display_name(en, base)

    normal_drop_row = drops_by_character_id.get(base)
    alpha_drop_row = drops_by_character_id.get(f"BOSS_{base}")

    normal_text = extract_drop_list(normal_drop_row, en) if normal_drop_row else ""
    alpha_text = extract_drop_list(alpha_drop_row, en) if alpha_drop_row else ""

    out: List[str] = []
    out.append("{{Pal Drop")
    out.append(f"|palName = {pal_display_name}")
    out.append(f"|normal_drops = {normal_text}")
    out.append(f"|alpha_drops = {alpha_text}")
    out.append("}}")

    return "\n".join(out).rstrip() + "\n"


def build_all_pal_drops_text(*, include_blank_line: bool = True) -> str:
    en = EnglishText()

    param_data = load_json(param_input_file)
    drop_data = load_json(drop_input_file)

    param_rows = extract_datatable_rows(param_data, source="DT_PalMonsterParameter")
    drop_rows = extract_datatable_rows(drop_data, source="DT_PalDropItem")

    drops_by_character_id = index_drop_rows_by_character_id(drop_rows)
    base_names = build_pal_order(param_rows)

    blocks: List[str] = []
    for base in base_names:
        block = build_pal_drop_wikitext(
            base,
            param_rows=param_rows,
            drops_by_character_id=drops_by_character_id,
            en=en,
        )
        if block:
            blocks.append(block)
            if include_blank_line:
                blocks.append("\n")

    return "".join(blocks).rstrip() + "\n"
