import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import Any, List, Tuple, TypedDict
from config.name_map import ELEMENT_NAME_MAP
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText

#Paths
param_input_file = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json")

#Mapping
EGG_SIZE_BY_RARITY = [
    (1, 4, "Regular"),
    (5, 7, "Large"),
    (8, 10, "Huge"),
]

EGG_ELEMENT_MAP = {
    "Neutral": "Common",
    "Ground": "Rocky",
    "Water": "Damp",
    "Electric": "Electric",
    "Grass": "Verdant",
    "Fire": "Scorching",
    "Ice": "Frozen",
    "Dark": "Dark",
    "Dragon": "Dragon",
}


class PalBreedingModel(TypedDict, total=False):
    base_id: str
    display_name: str

    breeding_rank: str
    male_probability: str
    combi_duplicate_priority: str
    egg: str

    unique_combos: str

def egg_size_from_rarity(rarity: Any) -> str:
    if rarity is None:
        return ""
    try:
        r = int(rarity)
    except (TypeError, ValueError):
        return ""

    if r == 20:
        return "Huge"

    for low, high, label in EGG_SIZE_BY_RARITY:
        if low <= r <= high:
            return label

    return ""

def egg_type_from_element(element: Any) -> str:
    if not element:
        return ""

    e = str(element).strip()
    if e.lower() == "normal":
        e = "Neutral"

    return EGG_ELEMENT_MAP.get(e, "")

def normalize_element(element: Any) -> str:
    if not element:
        return ""

    e = str(element).strip()
    return ELEMENT_NAME_MAP.get(e, e)

def after_double_colon(v: Any) -> str:
    if v is None:
        return ""
    s = str(v)
    if "::" in s:
        return s.split("::", 1)[1]
    return s

def build_breeding_egg(row: dict) -> str:
    if not isinstance(row, dict):
        return ""

    rarity = row.get("Rarity")
    element_raw = normalize_element(after_double_colon(row.get("ElementType1")))

    size = egg_size_from_rarity(rarity)
    egg_type = egg_type_from_element(element_raw)

    if not size or not egg_type:
        return ""

    if size == "Regular":
        return f"{egg_type} Egg"

    return f"{size} {egg_type} Egg"

def fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v)
    return str(v)

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

def build_pal_order(param_rows: dict) -> List[str]:
    pal_order = []

    for key, row in (param_rows or {}).items():
        if not isinstance(key, str):
            continue
        if not key.startswith("BOSS_"):
            continue

        base_id = key.replace("BOSS_", "")
        normal = param_rows.get(base_id)
        if not isinstance(normal, dict):
            continue

        pal_no = zukan_no(normal.get("ZukanIndex"), normal.get("ZukanIndexSuffix"))
        if pal_no == "":
            continue

        pal_order.append((pal_no, base_id))

    pal_order.sort(key=lambda x: (int(x[0][:3]), x[0][3:]))
    return [base_id for _, base_id in pal_order]

def build_pal_breeding_model_by_id(
    base_id: str,
    *,
    rows: dict,
    en: EnglishText,
) -> PalBreedingModel:
    normal = rows.get(base_id)
    boss = rows.get(f"BOSS_{base_id}")

    if not isinstance(normal, dict) or not isinstance(boss, dict):
        return {}

    display_name = en.get_pal_name(base_id) or base_id

    model: PalBreedingModel = {
        "base_id": base_id,
        "display_name": display_name,
        "breeding_rank": fmt(normal.get("CombiRank")),
        "male_probability": fmt(normal.get("MaleProbability")),
        "combi_duplicate_priority": fmt(normal.get("CombiDuplicatePriority")),
        "egg": build_breeding_egg(normal),
        "unique_combos": "",
    }

    return model

def build_all_pal_breeding_models() -> List[Tuple[str, PalBreedingModel]]:
    with open(param_input_file, "r", encoding="utf-8") as f:
        param_data = json.load(f)

    rows = extract_datatable_rows(param_data, source="DT_PalMonsterParameter")
    en = EnglishText()

    base_ids = build_pal_order(rows)

    out: List[Tuple[str, PalBreedingModel]] = []
    for base_id in base_ids:
        model = build_pal_breeding_model_by_id(base_id, rows=rows, en=en)
        if model:
            out.append((model.get("display_name", base_id), model))

    return out
