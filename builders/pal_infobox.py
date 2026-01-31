import os
import sys
import re
import json
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from config.name_map import WORK_SUITABILITY_MAP, ELEMENT_NAME_MAP
from config.partner_skill_icon_map import PARTNER_SKILL_ICON_RULES
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText, clean_english_text

param_input_file = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json")
active_skill_input_file = os.path.join(constants.INPUT_DIRECTORY, "Waza", "DT_WazaMasterLevel.json")
pal_activate_text_input_file = constants.EN_PAL_ACTIVATE_FILE
partner_skill_name_text_input_file = constants.EN_SKILL_NAME_FILE


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


_CHARACTERNAME_TAG_RE = re.compile(r"<characterName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)
def _replace_charactername_tags(text: str, english: EnglishText) -> str:
    s = str(text or "")

    def repl(m: re.Match) -> str:
        pal_id = (m.group(1) or "").strip()
        pal_name = english.get_pal_name(pal_id) or pal_id
        return pal_name

    return _CHARACTERNAME_TAG_RE.sub(repl, s)

_ITEMNAME_TAG_RE = re.compile(r"<itemName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)
_MAPOBJECTNAME_TAG_RE = re.compile(r"<mapObjectName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)
_ACTIVESKILLNAME_TAG_RE = re.compile(r"<activeSkillName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)
_UICOMMON_TAG_RE = re.compile(r"<uiCommon\s+id=\|([^|]+)\|/?>", re.IGNORECASE)

def _replace_item_and_object_tags(text: str, english: EnglishText) -> str:
    s = str(text or "")

    def item_repl(m: re.Match) -> str:
        item_id = (m.group(1) or "").strip()
        return english.get_item_name(item_id) or item_id

    def object_repl(m: re.Match) -> str:
        obj_id = (m.group(1) or "").strip()

        if obj_id == "MonsterFarm":
            return "the ranch"

        return obj_id

    s = _ITEMNAME_TAG_RE.sub(item_repl, s)
    s = _MAPOBJECTNAME_TAG_RE.sub(object_repl, s)
    return s

def _replace_activeskillname_tags(text: str, english: EnglishText) -> str:
    s = str(text or "")

    def repl(m: re.Match) -> str:
        skill_id = (m.group(1) or "").strip()
        return english.get_active_skill_name(skill_id) or skill_id

    return _ACTIVESKILLNAME_TAG_RE.sub(repl, s)

def _replace_uicommon_tags(text: str, english: EnglishText) -> str:
    s = str(text or "")

    def repl(m: re.Match) -> str:
        key = (m.group(1) or "").strip()
        # COMMON_STATUS_HP -> "Health", etc.
        return english.get(constants.EN_COMMON_TEXT_FILE, key) or key

    return _UICOMMON_TAG_RE.sub(repl, s)

def resolve_partner_skill_icon(desc: Any) -> str:
    s = str(desc or "").strip().lower()
    if s == "":
        return ""

    s = re.sub(r"\s+", " ", s)

    for icon_name, required_phrases, banned_phrases in (PARTNER_SKILL_ICON_RULES or []):
        if not icon_name:
            continue

        required_ok = True
        for phrase in (required_phrases or []):
            p = str(phrase or "").strip().lower()
            if p == "":
                continue
            if p not in s:
                required_ok = False
                break
        if not required_ok:
            continue

        banned_hit = False
        for phrase in (banned_phrases or []):
            p = str(phrase or "").strip().lower()
            if p == "":
                continue
            if p in s:
                banned_hit = True
                break
        if banned_hit:
            continue

        return str(icon_name).strip()

    return ""

def build_pal_infobox_wikitext(
    base: str,
    *,
    rows: dict,
    waza_by_pal_id: dict,
    en: EnglishText,
    include_header: bool = True,
    pal_activate_rows: dict,
    partner_skill_name_rows: dict,
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

    alpha_title_key = f"BOSS_NAME_{base}"
    alpha_title = (en.get(constants.EN_NAME_PREFIX_FILE, alpha_title_key) or "").strip()
    out.append(f"|alpha_title = {alpha_title}")

    ele1 = normalize_element(after_double_colon(normal.get("ElementType1")))
    ele2_raw = normalize_element(after_double_colon(normal.get("ElementType2")))
    ele2 = "" if ele2_raw.strip().lower() == "none" else ele2_raw

    out.append(f"|ele1 = {ele1}")
    out.append(f"|ele2 = {ele2}")

    size_raw = normal.get("Size")
    pal_size = after_double_colon(size_raw) if size_raw else ""
    out.append(f"|pal_size = {pal_size}")

    partner_skill_name_key = f"PARTNERSKILL_{base}"
    partner_skill_name = _lookup_text(partner_skill_name_rows, partner_skill_name_key)

    partner_skill_desc_key = f"PAL_FIRST_SPAWN_DESC_{base}"
    partner_skill_desc_raw = _lookup_text(pal_activate_rows, partner_skill_desc_key)
    partner_skill_desc_raw = _replace_charactername_tags(partner_skill_desc_raw, en)
    partner_skill_desc_raw = _replace_item_and_object_tags(partner_skill_desc_raw, en)
    partner_skill_desc_raw = _replace_activeskillname_tags(partner_skill_desc_raw, en)
    partner_skill_desc_raw = _replace_uicommon_tags(partner_skill_desc_raw, en)

    partner_skill_desc = clean_english_text(partner_skill_desc_raw).replace("\r", "").replace("\n", " ").strip()

    out.append(f"|partner_skill_name = {partner_skill_name}")
    out.append(f"|partner_skill_desc = {partner_skill_desc}")
    out.append(f"|partner_skill_icon = {resolve_partner_skill_icon(partner_skill_desc)}")

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

    pal_activate_rows = load_rows(pal_activate_text_input_file, source="DT_PalFirstActivatedInfoText")
    partner_skill_name_rows = load_rows(partner_skill_name_text_input_file, source="DT_SkillNameText_Common")

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
            pal_activate_rows=pal_activate_rows,
            partner_skill_name_rows=partner_skill_name_rows,
        )
        if block:
            blocks.append(block)
            blocks.append("\n")

    return "".join(blocks).rstrip() + "\n"
