import os
import re
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import Any, Dict, List, Optional, TypedDict, Tuple
from functools import lru_cache
from config.name_map import ELEMENT_NAME_MAP
from utils.english_text_utils import clean_english_text

#Paths
param_input_file = os.path.join(constants.INPUT_DIRECTORY, "PassiveSkill", "DT_PassiveSkill_Main.json")
en_name_file = constants.EN_SKILL_NAME_FILE
en_description_file = constants.EN_SKILL_DESC_FILE



class PassiveSkillEffect(TypedDict, total=False):
    index: int
    effect_type_leaf: str
    label: str
    value_raw: float
    value_text: str
    target_type_leaf: str

class PassiveSkillModel(TypedDict, total=False):
    passive_skill_id: str
    display_name: str
    description: str
    rank: str
    effects: List[PassiveSkillEffect]

def normalize_title(s: str) -> str:
    s = str(s or "").strip()
    return " ".join(s.split())

def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _extract_localized_text(entry: Any) -> str:
    if entry is None:
        return ""

    if isinstance(entry, str):
        return entry.strip()

    if isinstance(entry, dict):
        text_data = entry.get("TextData")
        if isinstance(text_data, dict):
            s = text_data.get("LocalizedString") or text_data.get("SourceString") or ""
            return str(s).strip()

        s = entry.get("LocalizedString") or entry.get("SourceString") or ""
        return str(s).strip()

    return ""

def _extract_datatable_rows(data: Any, *, source: str = "") -> Dict[str, Any]:
    if isinstance(data, list):
        dt_obj = None
        for entry in data:
            if isinstance(entry, dict) and isinstance(entry.get("Rows"), dict):
                dt_obj = entry
                break
        if not isinstance(dt_obj, dict):
            raise ValueError(f"{source} JSON list did not contain a DataTable object with 'Rows'")
        data = dt_obj

    if not isinstance(data, dict):
        raise ValueError(f"{source} JSON must be an object or list containing a DataTable object")

    rows = data.get("Rows")
    if not isinstance(rows, dict):
        keys = ", ".join(list(data.keys())[:25])
        raise ValueError(f"{source} JSON missing 'Rows'. Top-level keys: {keys}")

    return rows

@lru_cache(maxsize=1)
def _load_text_table(path: str) -> Dict[str, str]:
    raw = _load_json(path)
    rows = _extract_datatable_rows(raw, source=os.path.basename(path))

    out: Dict[str, str] = {}
    for k, v in rows.items():
        out[str(k)] = _extract_localized_text(v)

    return out

def _enum_leaf(v: Any) -> str:
    v = str(v or "")
    if "::" in v:
        return v.split("::")[-1]
    return v

def _is_placeholder_name(s: str) -> bool:
    s = str(s or "").strip()
    return s == "" or s.lower() == "en text"

def _is_displayable_passive(row_id: str, row: dict, *, english_name: str) -> bool:
    category_leaf = _enum_leaf(row.get("Category", ""))
    if category_leaf == "SortNotDisplayable":
        return False

    if _is_placeholder_name(english_name):
        return False

    rid = str(row_id or "")
    if rid.lower().startswith("test"):
        return False

    return True

def _humanize_effect_type(effect_type_leaf: str) -> str:
    effect_type_leaf = str(effect_type_leaf or "").strip()
    if effect_type_leaf == "":
        return ""

    mapping = {
        "ShotAttack": "Attack",
        "MeleeAttack": "Melee Attack",
        "Defense": "Defense",
        "MaxHP": "Max HP",
        "CraftSpeed": "Work Speed",
        "WorkSpeed": "Work Speed",
        "MoveSpeed": "Movement Speed",
        "Stamina": "Stamina",
        "Hunger": "Hunger",
        "SAN": "Sanity",
        "CoolTime": "Cooldown",
        "PalCaptureRate": "Capture Rate",
        "ExpRate": "EXP",
        "Weight": "Weight",
        "GainItemDrop": "Item Drop",
    }

    if effect_type_leaf.startswith("ElementBoost_"):
        raw_element = effect_type_leaf.split("_", 1)[1].strip()
        element = ELEMENT_NAME_MAP.get(raw_element, raw_element)
        return f"Element Boost {element}"

    if effect_type_leaf.startswith("ElementResist_"):
        raw_element = effect_type_leaf.split("_", 1)[1].strip()
        element = ELEMENT_NAME_MAP.get(raw_element, raw_element)
        return f"Element Resist {element}"

    if effect_type_leaf in mapping:
        return mapping[effect_type_leaf]

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", effect_type_leaf)
    spaced = spaced.replace("_", " ").strip()
    return spaced

def _format_effect_value(v: Any) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return ""

    if abs(n - round(n)) < 1e-9:
        n_str = str(int(round(n)))
    else:
        n_str = str(n).rstrip("0").rstrip(".")
    return f"{n_str}%"

def _get_effects(passive_row: dict) -> List[PassiveSkillEffect]:
    effects: List[PassiveSkillEffect] = []
    indices: List[int] = []

    for k in passive_row.keys():
        m = re.match(r"^EffectType(\d+)$", str(k))
        if m:
            indices.append(int(m.group(1)))

    for i in sorted(set(indices)):
        effect_type = passive_row.get(f"EffectType{i}")
        effect_value = passive_row.get(f"EffectValue{i}")
        target_type = passive_row.get(f"TargetType{i}")

        effect_type_leaf = _enum_leaf(effect_type)

        if effect_type_leaf.lower() == "no":
            continue

        try:
            n = float(effect_value)
        except (TypeError, ValueError):
            continue

        if abs(n) < 1e-12:
            continue

        effects.append(
            {
                "index": i,
                "effect_type_leaf": effect_type_leaf,
                "label": _humanize_effect_type(effect_type_leaf),
                "value_raw": n,
                "value_text": _format_effect_value(effect_value),
                "target_type_leaf": _enum_leaf(target_type),
            }
        )

    return effects

def _build_description_from_effects(effects: List[PassiveSkillEffect]) -> str:
    if not effects:
        return ""

    parts: List[str] = []
    for e in effects:
        label = e.get("label", "")
        val = e.get("value_text", "")
        if label and val:
            parts.append(f"{label} {val}")

    return "\n".join(parts)

def _is_none_text(v: Any) -> bool:
    s = str(v or "").strip()
    return s == "" or s.lower() == "none"

def _first_text(table: Dict[str, str], keys: List[Any]) -> str:
    for k in keys:
        if _is_none_text(k):
            continue
        s = table.get(str(k), "")
        if s:
            return str(s).strip()
    return ""

@lru_cache(maxsize=1)
def _load_passive_rows() -> Dict[str, dict]:
    raw_passive_data = _load_json(param_input_file)
    passive_rows = _extract_datatable_rows(raw_passive_data, source=os.path.basename(param_input_file))
    out: Dict[str, dict] = {}
    for passive_id, row in passive_rows.items():
        if isinstance(row, dict):
            out[str(passive_id)] = row
    return out

@lru_cache(maxsize=1)
def _build_name_to_id_map() -> Dict[str, str]:
    passive_rows = _load_passive_rows()
    en_skill_names = _load_text_table(en_name_file)

    out: Dict[str, str] = {}
    for passive_id, row in passive_rows.items():
        name_keys = [
            row.get("OverrideNameTextID"),
            row.get("OverrideSummaryTextId"),
            f"PASSIVE_{passive_id}",
            passive_id,
        ]

        english_name = _first_text(en_skill_names, name_keys)
        if english_name:
            english_name = clean_english_text(english_name)

        if not english_name:
            english_name = passive_id

        if not _is_displayable_passive(passive_id, row, english_name=english_name):
            continue

        key = normalize_title(english_name).casefold()
        if key and key not in out:
            out[key] = passive_id

    return out

def resolve_passive_skill_id_from_name(name: str) -> str:
    name = normalize_title(name)
    if not name:
        return ""
    m = _build_name_to_id_map()
    return m.get(name.casefold(), "")

def build_passive_skill_model_by_id(passive_skill_id: str) -> Optional[PassiveSkillModel]:
    passive_skill_id = str(passive_skill_id or "").strip()
    if not passive_skill_id:
        return None

    passive_rows = _load_passive_rows()
    row = passive_rows.get(passive_skill_id)
    if not isinstance(row, dict):
        return None

    en_skill_names = _load_text_table(en_name_file)
    en_skill_desc = _load_text_table(en_description_file)

    name_keys = [
        row.get("OverrideNameTextID"),
        row.get("OverrideSummaryTextId"),
        f"PASSIVE_{passive_skill_id}",
        passive_skill_id,
    ]
    desc_keys = [
        row.get("OverrideDescMsgID"),
        f"PASSIVE_{passive_skill_id}",
        passive_skill_id,
    ]

    english_name = _first_text(en_skill_names, name_keys)
    if english_name:
        english_name = clean_english_text(english_name)
    if not english_name:
        english_name = passive_skill_id

    if not _is_displayable_passive(passive_skill_id, row, english_name=english_name):
        return None

    english_desc = _first_text(en_skill_desc, desc_keys)
    if english_desc:
        english_desc = clean_english_text(english_desc, row=row)

    rank = str(row.get("Rank", "") or "")
    effects = _get_effects(row)

    if not english_desc:
        english_desc = _build_description_from_effects(effects)

    model: PassiveSkillModel = {
        "passive_skill_id": passive_skill_id,
        "display_name": normalize_title(english_name),
        "description": str(english_desc or "").strip(),
        "rank": str(rank or "").strip(),
        "effects": effects,
    }

    return model

def build_passive_skill_model_from_name(name: str) -> Optional[PassiveSkillModel]:
    passive_id = resolve_passive_skill_id_from_name(name)
    if not passive_id:
        return None
    return build_passive_skill_model_by_id(passive_id)

def build_all_passive_skill_models() -> List[PassiveSkillModel]:
    passive_rows = _load_passive_rows()
    en_skill_names = _load_text_table(en_name_file)

    ids: List[str] = []
    for passive_id, row in passive_rows.items():
        if not isinstance(row, dict):
            continue

        name_keys = [
            row.get("OverrideNameTextID"),
            row.get("OverrideSummaryTextId"),
            f"PASSIVE_{passive_id}",
            passive_id,
        ]

        english_name = _first_text(en_skill_names, name_keys)
        if english_name:
            english_name = clean_english_text(english_name)
        if not english_name:
            english_name = passive_id

        if not _is_displayable_passive(passive_id, row, english_name=english_name):
            continue

        ids.append(passive_id)

    models: List[PassiveSkillModel] = []
    for passive_id in ids:
        m = build_passive_skill_model_by_id(passive_id)
        if m:
            models.append(m)

    models.sort(key=lambda d: str(d.get("display_name", "")).casefold())
    return models
