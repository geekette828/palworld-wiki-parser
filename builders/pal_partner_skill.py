import os
import sys
import re
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import Any, Dict, List, TypedDict, Tuple
from config.name_map import ELEMENT_NAME_MAP
from config.partner_skill_map import PARTNER_SKILL_ICON_RULES, PARTNER_SKILL_LEVEL_RULES
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText, clean_english_text


# Paths
pal_activate_text_input_file = constants.EN_PAL_ACTIVATE_FILE
partner_skill_name_text_input_file = constants.EN_SKILL_NAME_FILE
passive_skill_main_input_file = os.path.join(constants.INPUT_DIRECTORY, "PassiveSkill", "DT_PassiveSkill_Main.json")


_ITEMNAME_TAG_RE = re.compile(r"<itemName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)
_MAPOBJECTNAME_TAG_RE = re.compile(r"<mapObjectName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)
_ACTIVESKILLNAME_TAG_RE = re.compile(r"<activeSkillName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)
_UICOMMON_TAG_RE = re.compile(r"<uiCommon\s+id=\|([^|]+)\|/?>", re.IGNORECASE)
_CHARACTERNAME_TAG_RE = re.compile(r"<characterName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)
_ELEMENTNAME_TAG_RE = re.compile(r"<elementName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)


def load_rows(path: str, *, source: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return extract_datatable_rows(data, source=source)

def after_double_colon(v: Any) -> str:
    if v is None:
        return ""
    s = str(v)
    if "::" in s:
        return s.split("::", 1)[1]
    return s

def fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v)
    return str(v)

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

def _replace_charactername_tags(text: str, english: EnglishText) -> str:
    s = str(text or "")

    def repl(m: re.Match) -> str:
        pal_id = (m.group(1) or "").strip()
        return english.get_pal_name(pal_id) or pal_id

    return _CHARACTERNAME_TAG_RE.sub(repl, s)

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
        return english.get(constants.EN_COMMON_TEXT_FILE, key) or key

    return _UICOMMON_TAG_RE.sub(repl, s)

def _replace_elementname_tags(text: str) -> str:
    s = str(text or "")

    def repl(m: re.Match) -> str:
        element_id = (m.group(1) or "").strip()
        return ELEMENT_NAME_MAP.get(element_id, element_id)

    return _ELEMENTNAME_TAG_RE.sub(repl, s)

def resolve_partner_skill_icon(desc: Any) -> str:
    s = str(desc or "").strip().lower()
    if s == "":
        return ""

    s = re.sub(r"\s+", " ", s)

    for icon_name, required_phrases, banned_phrases in (PARTNER_SKILL_ICON_RULES or []):
        if not icon_name:
            continue

        ok = True
        for phrase in (required_phrases or []):
            p = str(phrase or "").strip().lower()
            if p and p not in s:
                ok = False
                break
        if not ok:
            continue

        for phrase in (banned_phrases or []):
            p = str(phrase or "").strip().lower()
            if p and p in s:
                ok = False
                break
        if not ok:
            continue

        return str(icon_name).strip()

    return ""


def _expand_level_keys(prefix: str) -> List[Tuple[int, str]]:
    # * means the level slot inside the key name.
    # If no *, assume levels are at the end (append _*).
    if "*" not in prefix:
        prefix = prefix + "_*"

    out: List[Tuple[int, str]] = []
    for lvl in [1, 2, 3, 4, 5]:
        out.append((lvl, prefix.replace("*", str(lvl))))
    return out


class PartnerSkillRankLevel(TypedDict, total=False):
    effect_type: str
    effect_value: str
    target_type: str


class PartnerSkillEffectGroup(TypedDict, total=False):
    effect_group: str
    value_format: str
    levels: Dict[int, PartnerSkillRankLevel]


class PartnerSkillModel(TypedDict, total=False):
    base_id: str
    pal_name: str
    partner_skill_name: str
    partner_skill_desc: str
    partner_skill_icon: str
    effect_groups: List[PartnerSkillEffectGroup]


def _extract_primary_effect(row: dict) -> Tuple[str, str, str]:
    if not isinstance(row, dict):
        return ("", "", "")

    for i in range(1, 6):
        et = row.get(f"EffectType{i}")
        ev = row.get(f"EffectValue{i}")
        tt = row.get(f"TargetType{i}")

        et_s = after_double_colon(et).strip()
        tt_s = after_double_colon(tt).strip()
        ev_s = fmt(ev).strip()

        if et_s != "" or ev_s != "" or tt_s != "":
            return (et_s, ev_s, tt_s)

    return ("", "", "")


def _build_rank_groups_for_pal(
    base_id: str,
    *,
    passive_rows: dict,
    longer_variant_ids: List[str],
) -> List[PartnerSkillEffectGroup]:
    if not base_id:
        return []

    matches: List[str] = []
    for key in (passive_rows or {}).keys():
        if not isinstance(key, str):
            continue

        if not key.endswith(("_1", "_2", "_3", "_4", "_5")):
            continue

        if base_id not in key:
            continue

        skip = False
        for longer_id in longer_variant_ids:
            if longer_id and longer_id in key:
                skip = True
                break
        if skip:
            continue

        matches.append(key)

    if not matches:
        return []

    groups: Dict[str, Dict[int, PartnerSkillRankLevel]] = {}
    for key in matches:
        m = re.match(r"^(?P<base>.+)_(?P<rank>[1-5])$", key)
        if not m:
            continue

        group_base = m.group("base")
        rank = int(m.group("rank"))

        row = passive_rows.get(key)
        if not isinstance(row, dict):
            continue

        et, ev, tt = _extract_primary_effect(row)
        groups.setdefault(group_base, {})
        groups[group_base][rank] = {"effect_type": et, "effect_value": ev, "target_type": tt}

    out: List[PartnerSkillEffectGroup] = []
    for group_base, levels in groups.items():
        out.append(
            {
                "effect_group": group_base,
                "value_format": "raw",
                "levels": dict(sorted(levels.items(), key=lambda x: x[0])),
            }
        )

    out.sort(key=lambda g: str(g.get("effect_group", "")).lower())
    return out


def _build_rank_groups_from_prefix(prefix: str, *, value_format: str, passive_rows: dict) -> List[PartnerSkillEffectGroup]:
    levels: Dict[int, PartnerSkillRankLevel] = {}

    for lvl, key in _expand_level_keys(prefix):
        row = (passive_rows or {}).get(key)
        if not isinstance(row, dict):
            continue

        et, ev, tt = _extract_primary_effect(row)
        levels[lvl] = {"effect_type": et, "effect_value": ev, "target_type": tt}

    if not levels:
        return []

    return [
        {
            "effect_group": prefix,
            "value_format": value_format or "raw",
            "levels": dict(sorted(levels.items(), key=lambda x: x[0])),
        }
    ]


def _match_level_rules_from_description(desc: str, *, passive_rows: dict) -> List[Tuple[str, str]]:
    if not desc:
        return []

    s = desc.lower()

    matches: List[Tuple[str, str, int]] = []
    for prefix, required_phrases, banned_phrases, value_format in (PARTNER_SKILL_LEVEL_RULES or []):
        if not prefix:
            continue

        ok = True
        for phrase in (required_phrases or []):
            p = str(phrase or "").strip().lower()
            if p and p not in s:
                ok = False
                break
        if not ok:
            continue

        for phrase in (banned_phrases or []):
            p = str(phrase or "").strip().lower()
            if p and p in s:
                ok = False
                break
        if not ok:
            continue

        found = False
        for _, key in _expand_level_keys(prefix):
            if key in (passive_rows or {}):
                found = True
                break
        if not found:
            continue

        specificity = len([p for p in (required_phrases or []) if str(p).strip() != ""])
        matches.append((prefix, value_format or "raw", specificity))

    matches.sort(key=lambda x: (-x[2], x[0].lower()))
    return [(p, vf) for (p, vf, _) in matches]


def build_partner_skill_model_by_id(
    base: str,
    *,
    en: EnglishText,
    pal_activate_rows: dict,
    partner_skill_name_rows: dict,
    passive_rows: dict,
    longer_variant_ids: List[str],
) -> PartnerSkillModel:
    pal_name = en.get_pal_name(base) or base

    partner_skill_name_key = f"PARTNERSKILL_{base}"
    partner_skill_name = _lookup_text(partner_skill_name_rows, partner_skill_name_key)

    partner_skill_desc_key = f"PAL_FIRST_SPAWN_DESC_{base}"
    partner_skill_desc_raw = _lookup_text(pal_activate_rows, partner_skill_desc_key)

    partner_skill_desc_raw = _replace_charactername_tags(partner_skill_desc_raw, en)
    partner_skill_desc_raw = _replace_item_and_object_tags(partner_skill_desc_raw, en)
    partner_skill_desc_raw = _replace_activeskillname_tags(partner_skill_desc_raw, en)
    partner_skill_desc_raw = _replace_uicommon_tags(partner_skill_desc_raw, en)
    partner_skill_desc_raw = _replace_elementname_tags(partner_skill_desc_raw)

    partner_skill_desc = clean_english_text(partner_skill_desc_raw)
    partner_skill_desc = partner_skill_desc.replace("\r", " ").replace("\n", " ")
    partner_skill_desc = re.sub(r"\s+", " ", partner_skill_desc).strip()

    partner_skill_icon = resolve_partner_skill_icon(partner_skill_desc)

    effect_groups = _build_rank_groups_for_pal(
        base,
        passive_rows=passive_rows,
        longer_variant_ids=longer_variant_ids,
    )

    if not effect_groups:
        rule_matches = _match_level_rules_from_description(partner_skill_desc, passive_rows=passive_rows)

        used: set[str] = set()
        for prefix, value_format in rule_matches:
            if prefix in used:
                continue
            used.add(prefix)

            groups = _build_rank_groups_from_prefix(prefix, value_format=value_format, passive_rows=passive_rows)
            for g in groups:
                effect_groups.append(g)

    return {
        "base_id": base,
        "pal_name": pal_name,
        "partner_skill_name": partner_skill_name,
        "partner_skill_desc": partner_skill_desc,
        "partner_skill_icon": partner_skill_icon,
        "effect_groups": effect_groups,
    }


def build_all_partner_skill_models(*, pal_ids: List[str]) -> Dict[str, PartnerSkillModel]:
    pal_activate_rows = load_rows(pal_activate_text_input_file, source="DT_PalFirstActivatedInfoText")
    partner_skill_name_rows = load_rows(partner_skill_name_text_input_file, source="DT_SkillNameText_Common")
    passive_rows = load_rows(passive_skill_main_input_file, source="DT_PassiveSkill_Main")

    en = EnglishText()

    all_ids = [p for p in (pal_ids or []) if isinstance(p, str) and p.strip() != ""]
    out: Dict[str, PartnerSkillModel] = {}

    for base in all_ids:
        longer_variant_ids = [other for other in all_ids if other.startswith(base + "_")]

        model = build_partner_skill_model_by_id(
            base,
            en=en,
            pal_activate_rows=pal_activate_rows,
            partner_skill_name_rows=partner_skill_name_rows,
            passive_rows=passive_rows,
            longer_variant_ids=longer_variant_ids,
        )
        out[base] = model

    return out
