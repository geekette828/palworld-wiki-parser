import os
import sys
import json
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from config.name_map import WORK_SUITABILITY_MAP, ELEMENT_NAME_MAP
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText


param_input_file = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json")
active_skill_input_file = os.path.join(constants.INPUT_DIRECTORY, "Waza", "DT_WazaMasterLevel.json")


STATS_MAP = {
    "Hp": "hp",
    "ShotAttack": "attack",
    "Defense": "defense",
    "CraftSpeed": "work_speed",
    "Friendship_HP": "trust_hp",
    "Friendship_ShotAttack": "trust_attack",
    "Friendship_Defense": "trust_defense",
    "Friendship_CraftSpeed": "trust_work_speed",
    "Stamina": "stamina",
    "SlowWalkSpeed": "slow_walk_speed",
    "WalkSpeed": "walk_speed",
    "RunSpeed": "run_speed",
    "RideSprintSpeed": "ride_sprint_speed",
    "TransportSpeed": "transport_speed",
    "SwimSpeed": "swim_speed",
    "SwimDashSpeed": "swim_dash_speed",
    "ExpRatio": "exp_ratio",
    "EnemyMaxHPRate": "max_hp_rate",
    "EnemyReceiveDamageRate": "receive_damage_rate",
    "EnemyInflictDamageRate": "inflict_damage_rate",
    "CaptureRateCorrect": "capture_rate",
}

ALPHA_ELIGIBLE_PARAMS = {
    "hp",
    "attack",
    "defense",
    "work_speed",
    "trust_hp",
    "trust_attack",
    "trust_defense",
    "trust_work_speed",
    "stamina",
    "slow_walk_speed",
    "walk_speed",
    "run_speed",
    "ride_sprint_speed",
    "transport_speed",
    "swim_speed",
    "swim_dash_speed",
    "exp_ratio",
    "max_hp_rate",
    "receive_damage_rate",
    "inflict_damage_rate",
    "capture_rate",
}


def normalize_element(element: Any) -> str:
    if not element:
        return ""
    e = str(element).strip()
    return ELEMENT_NAME_MAP.get(e, e)


def bool_to_yes_no(v: Any) -> str:
    if v is True:
        return "True"
    if v is False:
        return "False"
    return ""


def sell_price_from_buy(v: Any) -> str:
    if v is None:
        return ""
    try:
        return str(int(float(v) / 10))
    except (TypeError, ValueError):
        return ""


def load_rows(path: str, *, source: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return extract_datatable_rows(data, source=source)


def fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v)
    return str(v)


def after_double_colon(v: Any) -> str:
    if v is None:
        return ""
    s = str(v)
    if "::" in s:
        return s.split("::", 1)[1]
    return s


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


def collect_passives(row: dict, en: EnglishText) -> List[str]:
    passives = []
    for i in range(1, 5):
        key = f"PassiveSkill{i}"
        v = row.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if s == "" or s.lower() == "none":
            continue
        passives.append(en.get_passive_name(s) or s)
    return passives


def build_work_suitability(row: dict) -> str:
    parts = []
    for json_key, label in WORK_SUITABILITY_MAP.items():
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


def build_waza_master_index(waza_rows: dict) -> Dict[str, List[Tuple[int, str]]]:
    by_pal_id: Dict[str, List[Tuple[int, str]]] = {}
    for _, row in (waza_rows or {}).items():
        if not isinstance(row, dict):
            continue

        pal_id = row.get("PalId")
        waza_id = row.get("WazaID")
        level = row.get("Level")

        pal_id = "" if pal_id is None else str(pal_id).strip()
        if pal_id == "":
            continue

        skill_name = after_double_colon(waza_id).strip()
        if skill_name == "":
            continue

        try:
            lvl = int(level)
        except (TypeError, ValueError):
            continue

        by_pal_id.setdefault(pal_id, []).append((lvl, skill_name))

    for pal_id, items in by_pal_id.items():
        items.sort(key=lambda x: (x[0], x[1].lower()))
    return by_pal_id


def build_active_skills(monster_row_key: str, monster_row: dict, waza_by_pal_id: dict, en: EnglishText) -> str:
    if not isinstance(monster_row, dict):
        return ""

    tribe = after_double_colon(monster_row.get("Tribe")).strip()
    bp_class = "" if monster_row.get("BPClass") is None else str(monster_row.get("BPClass")).strip()
    key = "" if monster_row_key is None else str(monster_row_key).strip()

    candidates = []
    for v in (tribe, key, bp_class):
        if v and v not in candidates:
            candidates.append(v)

    skills = None
    for pal_id in candidates:
        skills = waza_by_pal_id.get(pal_id)
        if skills:
            break

    if not skills:
        return ""

    return "; ".join(
        f"{(en.get_active_skill_name(skill) or skill)}@{lvl}"
        for (lvl, skill) in skills
    )


def build_pal_order(rows: dict) -> List[str]:
    pal_order = []
    for key, row in rows.items():
        if not isinstance(key, str):
            continue
        if not key.startswith("BOSS_"):
            continue

        base = key.replace("BOSS_", "")
        normal = rows.get(base)
        if not isinstance(normal, dict):
            continue

        pal_no = zukan_no(normal.get("ZukanIndex"), normal.get("ZukanIndexSuffix"))
        if pal_no == "":
            continue

        pal_order.append((pal_no, base))

    pal_order.sort(key=lambda x: (int(x[0][:3]), x[0][3:]))
    return [base for _, base in pal_order]


def build_pal_infobox_wikitext(
    base: str,
    *,
    rows: dict,
    waza_by_pal_id: dict,
    en: EnglishText,
    include_header: bool = True,
) -> str:
    normal = rows.get(base)
    boss = rows.get(f"BOSS_{base}")

    if not isinstance(normal, dict) or not isinstance(boss, dict):
        return ""

    pal_display_name = en.get_pal_name(base) or base

    out: List[str] = []

    if include_header:
        out.append(f"# {pal_display_name} ({base})")

    out.append("{{Pal")
    out.append(f"|no = {zukan_no(normal.get('ZukanIndex'), normal.get('ZukanIndexSuffix'))}")
    out.append("|alpha_title = ")

    ele1 = normalize_element(after_double_colon(normal.get("ElementType1")))
    ele2_raw = normalize_element(after_double_colon(normal.get("ElementType2")))
    ele2 = "" if ele2_raw.strip().lower() == "none" else ele2_raw

    out.append(f"|ele1 = {ele1}")
    out.append(f"|ele2 = {ele2}")

    size_raw = normal.get("Size")
    pal_size = after_double_colon(size_raw) if size_raw else ""
    out.append(f"|pal_size = {pal_size}")

    out.append("|partner_skill_name = ")
    out.append("|partner_skill_desc = ")
    out.append("|partner_skill_icon = ")

    out.append("|pal_gear = ")
    out.append(f"|work_suitability = {build_work_suitability(normal)}")

    out.append("<!-- Basics -->")
    out.append(f"|hunger = {fmt(normal.get('FoodAmount'))}")
    out.append(f"|nocturnal = {bool_to_yes_no(normal.get('Nocturnal'))}")
    out.append(f"|sell_price = {sell_price_from_buy(normal.get('Price'))}")

    out.append("<!-- Skills -->")
    passives = collect_passives(normal, en)
    out.append(f"|passive_skills = {'; '.join(passives) if passives else ''}")
    out.append(f"|active_skills = {build_active_skills(base, normal, waza_by_pal_id, en)}")

    out.append("<!-- Stats -->")
    for json_key, param in STATS_MAP.items():
        normal_val = normal.get(json_key)
        boss_val = boss.get(json_key)

        out.append(f"|{param} = {fmt(normal_val)}")

        if param in ALPHA_ELIGIBLE_PARAMS and normal_val != boss_val:
            out.append(f"|alpha_{param} = {fmt(boss_val)}")

    out.append("}}")
    return "\n".join(out).rstrip() + "\n"


def build_all_pal_infoboxes_text(*, include_headers: bool = True) -> str:
    rows = load_rows(param_input_file, source="DT_PalMonsterParameter")
    waza_rows = load_rows(active_skill_input_file, source="DT_WazaMasterLevel")

    waza_by_pal_id = build_waza_master_index(waza_rows)
    en = EnglishText()

    base_names = build_pal_order(rows)

    blocks: List[str] = []
    for base in base_names:
        block = build_pal_infobox_wikitext(
            base,
            rows=rows,
            waza_by_pal_id=waza_by_pal_id,
            en=en,
            include_header=include_headers,
        )
        if block:
            blocks.append(block)
            blocks.append("\n")

    return "".join(blocks).rstrip() + "\n"
