import os
import sys
import json
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from functools import lru_cache
from config.name_map import WORK_SUITABILITY_MAP
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import clean_english_text
from utils.console_utils import force_utf8_stdout
force_utf8_stdout()

# Paths 
param_input_file = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalHumanParameter.json")
en_name_file = constants.EN_HUMAN_NAME_FILE



# Template-facing stats map (Humans don't use the Pal STATS_MAP 1:1)
HUMAN_STATS_MAP = {
    "Hp": "hp",
    "Defense": "defense",
    "Support": "support",
    "Stamina": "stamina",
    "SlowWalkSpeed": "slow_walk_speed",
    "WalkSpeed": "walk_speed",
    "RunSpeed": "run_speed",
    "RideSprintSpeed": "ride_sprint_speed",
    "TransportSpeed": "transport_speed",
    "CraftSpeed": "work_speed",
}

# Heuristic mapping for Organization -> wiki-facing faction names.
# Unknown values fall back to the enum leaf.
ORGANIZATION_TO_FACTION = {
    "TeamBlackHunter": "Rayne Syndicate",
    "FireCult": "Brothers of the Eternal Pyre",
    "Labmen": "Pal Genetic Research Unit",
    "Believer": "Free Pal Alliance",
    "Police": "PIDF",
    "City": "",  # civilian/merchant/guard etc
}

_TOKEN_WS_RE = re.compile(r"[ \t\r\n]+")


class HumanInfoboxModel(TypedDict, total=False):
    internal_id: str
    display_name: str

    type: str
    level: str
    faction: str
    food: str
    nocturnal: str
    price: str

    work_suitability: str
    active_skills: str

    # Stats
    hp: str
    attack: str
    defense: str
    support: str
    stamina: str
    walk_speed: str
    slow_walk_speed: str
    run_speed: str
    ride_sprint_speed: str
    transport_speed: str
    work_speed: str


def _trim(v: Any) -> str:
    return str(v or "").strip()


def after_double_colon(v: Any) -> str:
    s = _trim(v)
    if "::" in s:
        return s.split("::", 1)[1].strip()
    return s


def fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        # keep stable repr like other builders
        return repr(v).rstrip("0").rstrip(".") if "." in repr(v) else repr(v)
    return str(v)


def bool_to_yes_no(v: Any) -> str:
    if v is True:
        return "True"
    if v is False:
        return "False"
    return ""


def load_rows(path: str, *, source: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return extract_datatable_rows(data, source=source)


def _textdata_string(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    td = row.get("TextData")
    if not isinstance(td, dict):
        return ""

    s = td.get("LocalizedString")
    if s is None or str(s).strip() == "":
        s = td.get("SourceString")

    return "" if s is None else str(s)


def _lookup_text(rows: dict, key: str) -> str:
    if not rows or not key:
        return ""
    row = rows.get(key)
    return _textdata_string(row).strip()


@lru_cache(maxsize=1)
def _load_human_name_rows() -> dict:
    return load_rows(en_name_file, source="DT_HumanNameText_Common")

def _resolve_display_name(row: Dict[str, Any], internal_id: str) -> str:
    key = _trim(row.get("OverrideNameTextID"))
    if key and key.lower() != "none":
        name = _lookup_text(_load_human_name_rows(), key)
        if name and name.strip() and name.strip() != "-":
            return name.strip()
    return internal_id

def _resolve_faction(row: Dict[str, Any]) -> str:
    org = after_double_colon(row.get("Organization"))
    if not org or org.lower() == "none":
        return ""
    mapped = ORGANIZATION_TO_FACTION.get(org)
    if mapped is not None:
        return mapped
    return org

def _guess_type(row: Dict[str, Any]) -> str:
    if row.get("IsTowerBoss") is True:
        return "Boss"

    if row.get("IsBoss") is True:
        bgm = _trim(row.get("BattleBGM"))
        bgm_leaf = after_double_colon(bgm)
        if bgm == "EPalBattleBGMType::FieldBoss" or bgm_leaf == "FieldBoss":
            return "Bounty Target"

    return ""

def _choose_attack_value(row: Dict[str, Any]) -> str:
    # Your {{Human}} template only has one attack field, but the table has MeleeAttack + ShotAttack.
    # Choose based on weapon type when possible, otherwise prefer ShotAttack (since most enemies shoot).
    weapon = after_double_colon(row.get("Weapon")).lower()
    melee = fmt(row.get("MeleeAttack"))
    shot = fmt(row.get("ShotAttack"))

    if weapon in {"none", ""}:
        return shot or melee

    # crude heuristic: if weapon name includes these, use melee
    if any(k in weapon for k in ("sword", "bat", "spear", "club", "melee")):
        return melee or shot

    return shot or melee


def build_work_suitability(row: Dict[str, Any]) -> str:
    parts: List[str] = []
    for json_key, label in (WORK_SUITABILITY_MAP or {}).items():
        v = row.get(json_key)
        if v is None:
            continue
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if n <= 0:
            continue
        parts.append(f"{label}@{n}")
    return "; ".join(parts)


def build_human_infobox_model_by_id(
    internal_id: str,
    *,
    rows: dict,
) -> HumanInfoboxModel:
    row = rows.get(internal_id)
    if not isinstance(row, dict):
        return {}

    display_name = _resolve_display_name(row, internal_id)

    model: HumanInfoboxModel = {
        "internal_id": internal_id,
        "display_name": display_name,

        "type": _guess_type(row),
        "level": "",
        "faction": "",

        "food": fmt(row.get("FoodAmount")),
        "nocturnal": bool_to_yes_no(row.get("Nocturnal")),
        "price": fmt(row.get("Price")),

        "work_suitability": build_work_suitability(row),
        "active_skills": "Punch@1",

        "hp": fmt(row.get("Hp")),
        "attack": _choose_attack_value(row),
        "defense": fmt(row.get("Defense")),
        "support": fmt(row.get("Support")),
        "stamina": fmt(row.get("Stamina")),

        "walk_speed": fmt(row.get("WalkSpeed")),
        "slow_walk_speed": fmt(row.get("SlowWalkSpeed")),
        "run_speed": fmt(row.get("RunSpeed")),
        "ride_sprint_speed": fmt(row.get("RideSprintSpeed")),
        "transport_speed": fmt(row.get("TransportSpeed")),
        "work_speed": fmt(row.get("CraftSpeed")),
    }

    # Clean up any -1 speed defaults (table uses -1 for "use default")
    for k in ("walk_speed", "slow_walk_speed", "run_speed", "ride_sprint_speed"):
        if _trim(model.get(k)) == "-1":
            model[k] = ""

    # Normalize whitespace in string-ish fields
    for k, v in list(model.items()):
        if isinstance(v, str):
            model[k] = _TOKEN_WS_RE.sub(" ", v).strip()

    return model


def build_all_human_infobox_models(
    *,
    param_path: Optional[str] = None,
) -> List[Tuple[str, str, HumanInfoboxModel]]:
    """
    Returns a list of (display_name, internal_id, model) entries in stable output order.
    Mirrors builders.item_infobox.build_all_item_infobox_models().
    """
    path = param_path or param_input_file
    rows = load_rows(path, source="DT_PalHumanParameter")

    out: List[Tuple[str, str, HumanInfoboxModel]] = []
    for internal_id in (rows or {}).keys():
        model = build_human_infobox_model_by_id(internal_id, rows=rows)
        if not model:
            continue

        display_name = _trim(model.get("display_name"))
        if not display_name:
            continue

        out.append((display_name, internal_id, model))

    # Stable order: display name then internal id
    out.sort(key=lambda t: (t[0].casefold(), t[1].casefold()))
    return out


def human_infobox_model_to_params(model: HumanInfoboxModel) -> Dict[str, str]:
    """
    Mapping helper for comparer:
    Converts model -> flat dict matching {{Human}} template param names.
    """
    if not model:
        return {}

    keys = [
        "internal_id",
        "type",
        "level",
        "faction",
        "food",
        "nocturnal",
        "price",
        "work_suitability",
        "active_skills",

        "hp",
        "attack",
        "defense",
        "support",
        "stamina",
        "walk_speed",
        "slow_walk_speed",
        "run_speed",
        "ride_sprint_speed",
        "transport_speed",
        "work_speed",
    ]

    out: Dict[str, str] = {}
    for k in keys:
        out[k] = _trim(model.get(k, ""))
    return out


def render_human_infobox(model: HumanInfoboxModel, *, include_heading: bool = True) -> str:
    from exports.export_human_infoboxes import render_human_infobox as _render
    return _render(model, include_heading=include_heading)


def build_human_infobox(internal_id: str) -> str:
    """
    Convenience wrapper:
    pass an internal id, get rendered infobox block back.
    """
    rows = load_rows(param_input_file, source="DT_PalHumanParameter")
    model = build_human_infobox_model_by_id(internal_id, rows=rows)
    return render_human_infobox(model, include_heading=True)
