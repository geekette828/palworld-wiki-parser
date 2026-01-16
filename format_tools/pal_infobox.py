import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from config.name_map import WORK_SUITABILITY_MAP, ELEMENT_NAME_MAP
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText


# Define paths
param_input_file = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json")
active_skill_input_file = os.path.join(constants.INPUT_DIRECTORY, "Waza", "DT_WazaMasterLevel.json")
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "pal_infobox.txt")


STATS_MAP = {
    # Core
    "Hp": "hp",
    "ShotAttack": "attack",
    "Defense": "defense",
    "CraftSpeed": "work_speed",
    "Friendship_HP": "trust_hp",
    "Friendship_ShotAttack": "trust_attack",
    "Friendship_Defense": "trust_defense",
    "Friendship_CraftSpeed": "trust_work_speed",
    # Movement
    "Stamina": "stamina",
    "SlowWalkSpeed": "slow_walk_speed",
    "WalkSpeed": "walk_speed",
    "RunSpeed": "run_speed",
    "RideSprintSpeed": "ride_sprint_speed",
    "TransportSpeed": "transport_speed",
    "SwimSpeed": "swim_speed",
    "SwimDashSpeed": "swim_dash_speed",
    # Encounter scaling
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


def normalize_element(element):
    if not element:
        return ""

    e = str(element).strip()
    # Prefer centralized mapping (name_map)
    return ELEMENT_NAME_MAP.get(e, e)


def bool_to_yes_no(v):
    if v is True:
        return "True"
    if v is False:
        return "False"
    return ""


def sell_price_from_buy(v):
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


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v)
    return str(v)


def after_double_colon(v):
    if v is None:
        return ""
    s = str(v)
    if "::" in s:
        return s.split("::", 1)[1]
    return s


def zukan_no(zukan_index, zukan_suffix):
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


def collect_passives(row: dict, en: EnglishText):
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


def build_work_suitability(row: dict):
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


def build_waza_master_index(waza_rows: dict):
    by_pal_id = {}
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


def build_active_skills(monster_row_key: str, monster_row: dict, waza_by_pal_id: dict, en: EnglishText):
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


def main():
    rows = load_rows(param_input_file, source="DT_PalMonsterParameter")
    waza_rows = load_rows(active_skill_input_file, source="DT_WazaMasterLevel")

    waza_by_pal_id = build_waza_master_index(waza_rows)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    en = EnglishText()

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
    base_names = [base for _, base in pal_order]

    output_lines = []

    for base in base_names:
        normal = rows.get(base)
        boss = rows.get(f"BOSS_{base}")

        if not isinstance(normal, dict) or not isinstance(boss, dict):
            continue

        pal_display_name = en.get_pal_name(base) or base

        output_lines.append(f"# {pal_display_name} ({base})")
        output_lines.append("{{Pal/sandbox")

        output_lines.append(f"|no = {zukan_no(normal.get('ZukanIndex'), normal.get('ZukanIndexSuffix'))}")
        output_lines.append("|alpha_title = ")

        ele1 = normalize_element(after_double_colon(normal.get("ElementType1")))
        ele2_raw = normalize_element(after_double_colon(normal.get("ElementType2")))
        ele2 = "" if ele2_raw.strip().lower() == "none" else ele2_raw

        output_lines.append(f"|ele1 = {ele1}")
        output_lines.append(f"|ele2 = {ele2}")

        size_raw = normal.get("Size")
        pal_size = after_double_colon(size_raw) if size_raw else ""
        output_lines.append(f"|pal_size = {pal_size}")

        output_lines.append("|partner_skill_name = ")
        output_lines.append("|partner_skill_desc = ")
        output_lines.append("|partner_skill_icon = ")

        output_lines.append("|pal_gear = ")
        # Keep name-map conversion for work suitability
        output_lines.append(f"|work_suitability = {build_work_suitability(normal)}")

        output_lines.append("<!-- Basics -->")
        output_lines.append(f"|hunger = {fmt(normal.get('FoodAmount'))}")
        output_lines.append(f"|nocturnal = {bool_to_yes_no(normal.get('Nocturnal'))}")
        output_lines.append(f"|sell_price = {sell_price_from_buy(normal.get('Price'))}")

        output_lines.append("<!-- Skills -->")
        passives = collect_passives(normal, en)
        output_lines.append(f"|passive_skills = {'; '.join(passives) if passives else ''}")
        output_lines.append(f"|active_skills = {build_active_skills(base, normal, waza_by_pal_id, en)}")

        output_lines.append("<!-- Stats -->")
        for json_key, param in STATS_MAP.items():
            normal_val = normal.get(json_key)
            boss_val = boss.get(json_key)

            output_lines.append(f"|{param} = {fmt(normal_val)}")

            if param in ALPHA_ELIGIBLE_PARAMS and normal_val != boss_val:
                output_lines.append(f"|alpha_{param} = {fmt(boss_val)}")

        output_lines.append("}}")
        output_lines.append("")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"✅ Wrote pal infobox data to: {output_file}")


if __name__ == "__main__":
    main()
