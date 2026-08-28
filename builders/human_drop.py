import os
import sys
import json
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import Any, Dict, List, Tuple, TypedDict
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText

# Paths
drop_input_file = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalDropItem.json")
human_param_input_file = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalHumanParameter.json")
human_name_text_input_file = constants.EN_HUMAN_NAME_FILE



class HumanDropsModel(TypedDict, total=False):
    character_id: str
    faction_name: str
    human_name: str
    drops: str


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_chance(rate_value: Any) -> str:
    try:
        f = float(rate_value)
    except Exception:
        return str(rate_value)

    if f.is_integer():
        return str(int(f))
    return str(f).rstrip("0").rstrip(".")


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

        # Match pal_drops behavior: only Level 0 rows
        if level_int != 0:
            continue

        by_id[str(character_id).strip()] = row

    return by_id


def _is_human_param_row(row: dict) -> bool:
    if not isinstance(row, dict):
        return False

    # Prefer game flags over name-prefix guesses
    if row.get("IsPal") is True:
        return False

    tribe = str(row.get("Tribe") or "")
    if "Human" in tribe:
        return True

    # fallback: humanoid genus often present
    genus = str(row.get("GenusCategory") or "")
    if "Humanoid" in genus:
        return True

    return False


def _resolve_human_param_row(character_id: str, human_param_rows: dict) -> Tuple[str, dict]:
    character_id = str(character_id or "").strip()
    if character_id == "":
        return "", {}

    row = human_param_rows.get(character_id)
    if isinstance(row, dict) and _is_human_param_row(row):
        return character_id, row

    if character_id.startswith("BOSS_"):
        base = character_id.replace("BOSS_", "", 1)
        row2 = human_param_rows.get(base)
        if isinstance(row2, dict) and _is_human_param_row(row2):
            return base, row2

    return "", {}


_CAMEL_SPLIT_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _prettify_weapon_enum(value: Any) -> str:
    s = str(value or "").strip()
    if s == "" or s.lower() == "none":
        return ""

    # Expect strings like: EPalWeaponType::LaserRifle
    if "::" in s:
        s = s.split("::", 1)[1].strip()

    if s == "" or s.lower() == "none":
        return ""

    # Avoid ugly outputs for "MeleeWeapon"
    if s.lower() in {"meleeweapon", "unarmed"}:
        return ""

    # Split CamelCase into words: LaserRifle -> Laser Rifle
    parts = _CAMEL_SPLIT_RE.split(s)
    pretty = " ".join([p for p in parts if p]).strip()
    return pretty


def _resolve_human_base_name(override_text_id: str, human_name_rows: dict) -> str:
    override_text_id = str(override_text_id or "").strip()
    if override_text_id == "" or override_text_id.lower() == "none":
        return ""

    row = human_name_rows.get(override_text_id)
    if not isinstance(row, dict):
        return ""

    text_data = row.get("TextData")
    if not isinstance(text_data, dict):
        return ""

    localized = str(text_data.get("LocalizedString") or "").strip()
    if localized == "" or localized == "-":
        localized = str(text_data.get("SourceString") or "").strip()

    return localized


def build_human_drops_model_by_character_id(
    character_id: str,
    *,
    drops_by_character_id: dict,
    human_param_rows: dict,
    human_name_rows: dict,
    en: EnglishText,
) -> HumanDropsModel:
    character_id = str(character_id or "").strip()
    if character_id == "":
        return {}

    resolved_id, human_row = _resolve_human_param_row(character_id, human_param_rows)
    if not human_row:
        return {}

    override_name_text_id = str(human_row.get("OverrideNameTextID") or "").strip()
    base_name = _resolve_human_base_name(override_name_text_id, human_name_rows)
    if base_name == "":
        return {}

    weapon_pretty = _prettify_weapon_enum(human_row.get("Weapon"))

    is_invader = (
        character_id.endswith("_Invader")
        or resolved_id.endswith("_Invader")
        or "_Invader" in character_id
        or "_Invader" in resolved_id
    )

    if weapon_pretty != "":
        if is_invader:
            weapon_pretty = f"{weapon_pretty} Invader"
        display_name = f"{base_name} ({weapon_pretty})"
    else:
        display_name = base_name

    drop_row = drops_by_character_id.get(character_id)
    if not drop_row:
        # try the resolved (non-BOSS_) id if different
        if resolved_id and resolved_id != character_id:
            drop_row = drops_by_character_id.get(resolved_id)

    drops_text = extract_drop_list(drop_row, en) if drop_row else ""
    if drops_text == "":
        return {}

    return {
        "character_id": character_id,
        "faction_name": base_name,
        "human_name": display_name,
        "drops": drops_text,
    }


def build_all_human_drops_models() -> List[Tuple[str, HumanDropsModel]]:
    en = EnglishText()

    drop_data = load_json(drop_input_file)
    human_param_data = load_json(human_param_input_file)
    human_name_text_data = load_json(human_name_text_input_file)

    drop_rows = extract_datatable_rows(drop_data, source="DT_PalDropItem")
    human_param_rows = extract_datatable_rows(human_param_data, source="DT_PalHumanParameter")
    human_name_rows = extract_datatable_rows(human_name_text_data, source="DT_HumanNameText_Common")

    drops_by_character_id = index_drop_rows_by_character_id(drop_rows)

    out: List[Tuple[str, HumanDropsModel]] = []
    for character_id in sorted(drops_by_character_id.keys()):
        model = build_human_drops_model_by_character_id(
            character_id,
            drops_by_character_id=drops_by_character_id,
            human_param_rows=human_param_rows,
            human_name_rows=human_name_rows,
            en=en,
        )
        if model:
            sort_key = f"{model.get('faction_name','')}::{model.get('human_name','')}::{character_id}"
            out.append((sort_key, model))

    out.sort(key=lambda x: x[0].lower())
    return out


def build_human_drops_by_faction() -> Dict[str, List[HumanDropsModel]]:
    grouped: Dict[str, List[HumanDropsModel]] = {}
    for _, model in build_all_human_drops_models():
        faction = model.get("faction_name", "").strip()
        if faction == "":
            continue
        grouped.setdefault(faction, []).append(model)

    for faction, models in grouped.items():
        models.sort(key=lambda m: (m.get("human_name", "").lower(), m.get("character_id", "").lower()))

    return dict(sorted(grouped.items(), key=lambda kv: kv[0].lower()))
