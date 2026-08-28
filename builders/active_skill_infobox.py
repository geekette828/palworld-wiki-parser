import os
import re
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import Any, Dict, Optional, Tuple, List, TypedDict
from config.name_map import ELEMENT_NAME_MAP, ACTIVE_SKILL_STATUS_EFFECT_MAP
from utils.english_text_utils import EnglishText, clean_english_text
from utils.json_datatable_utils import extract_datatable_rows

#Paths
waza_input_file = os.path.join(constants.INPUT_DIRECTORY, "Waza", "DT_WazaDataTable.json")
waza_master_level_file = os.path.join(constants.INPUT_DIRECTORY, "Waza", "DT_WazaMasterLevel.json")
item_input_file = os.path.join(constants.INPUT_DIRECTORY, "Item", "DT_ItemDataTable.json")
en_name_file = constants.EN_SKILL_NAME_FILE
en_description_file = constants.EN_SKILL_DESC_FILE


_CHARACTERNAME_TAG_RE = re.compile(r"<characterName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)

_CACHED_WAZA_ROWS: Optional[Dict[str, Dict[str, Any]]] = None
_CACHED_SKILL_IDS_WITH_SKILLCARDS: Optional[set[str]] = None
_CACHED_PAL_IDS_BY_SKILL_ID: Optional[Dict[str, List[str]]] = None

# Untranslated rows in the English name table fall back to this placeholder.
_PLACEHOLDER_SKILL_NAMES = {"en text"}

# Pal id decorations that point back at a base pal (alphas, tower/raid bosses, predators,
# oil rig variants, mount/summon copies). Stripped only when the decorated id has no name.
_PAL_ID_PREFIX_RE = re.compile(r"^(?:BOSS|PREDATOR|GYM|RAID|SUMMON)_", re.IGNORECASE)
_PAL_ID_SUFFIX_RE = re.compile(r"(?:_(?:2|MAX|Avatar|Otomo|Oilrig|Hand_Left|Hand_Right))+$", re.IGNORECASE)

class ActiveSkillInfoboxModel(TypedDict, total=False):
    skill_id: str
    display_name: str
    description: str
    element: str
    ct: str
    power: str
    range: str
    status: str
    chance: str
    status2: str
    chance2: str
    unique_to: List[str]
    fruit: bool
    inherited: bool

def _replace_charactername_tags(text: str, english: EnglishText) -> str:
    s = str(text or "")

    def repl(m: re.Match) -> str:
        pal_id = (m.group(1) or "").strip()
        pal_name = english.get_pal_name(pal_id) or pal_id
        return pal_name

    return _CHARACTERNAME_TAG_RE.sub(repl, s)


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _trim(v: Any) -> str:
    return str(v or "").strip()


def _leaf_enum(v: Any) -> str:
    s = _trim(v)
    if "::" in s:
        return s.split("::", 1)[1].strip()
    return s


def _format_number(v: Any) -> str:
    if v is None:
        return ""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return _trim(v)

    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return str(n).rstrip("0").rstrip(".")


def _normalize_element(element_enum: Any) -> str:
    leaf = _leaf_enum(element_enum)
    return ELEMENT_NAME_MAP.get(leaf, leaf)


def _load_skill_ids_with_skillcards() -> set[str]:
    global _CACHED_SKILL_IDS_WITH_SKILLCARDS
    if _CACHED_SKILL_IDS_WITH_SKILLCARDS is not None:
        return _CACHED_SKILL_IDS_WITH_SKILLCARDS

    data = _load_json(item_input_file)
    rows = extract_datatable_rows(data, source=os.path.basename(item_input_file)) or {}

    skill_ids: set[str] = set()

    for row_name, row in rows.items():
        if not isinstance(row, dict):
            continue

        if not str(row_name).startswith("SkillCard_"):
            continue

        if row.get("bLegalInGame") is False:
            continue

        waza = _trim(row.get("WazaID"))
        if waza.startswith("EPalWazaID::"):
            skill_ids.add(waza.split("::", 1)[1].strip())

    _CACHED_SKILL_IDS_WITH_SKILLCARDS = skill_ids
    return _CACHED_SKILL_IDS_WITH_SKILLCARDS


def _load_pal_ids_by_skill_id() -> Dict[str, List[str]]:
    """Map each skill id to the pal ids that learn it naturally, in data-table order."""
    global _CACHED_PAL_IDS_BY_SKILL_ID
    if _CACHED_PAL_IDS_BY_SKILL_ID is not None:
        return _CACHED_PAL_IDS_BY_SKILL_ID

    data = _load_json(waza_master_level_file)
    rows = extract_datatable_rows(data, source=os.path.basename(waza_master_level_file)) or {}

    mapping: Dict[str, List[str]] = {}

    for _, row in rows.items():
        if not isinstance(row, dict):
            continue

        waza = _trim(row.get("WazaID"))
        if not waza.startswith("EPalWazaID::"):
            continue

        skill_id = waza.split("::", 1)[1].strip()
        pal_id = _trim(row.get("PalId"))
        if not skill_id or not pal_id:
            continue

        bucket = mapping.setdefault(skill_id, [])
        if pal_id not in bucket:
            bucket.append(pal_id)

    _CACHED_PAL_IDS_BY_SKILL_ID = mapping
    return _CACHED_PAL_IDS_BY_SKILL_ID


def _resolve_pal_display_name(pal_id: str, english: EnglishText) -> str:
    """Resolve a pal id to its English name, falling back to the base pal for variant ids."""
    candidate = _trim(pal_id)

    while candidate:
        name = english.get_pal_name(candidate)
        if name:
            return name

        stripped = _PAL_ID_PREFIX_RE.sub("", candidate)
        stripped = _PAL_ID_SUFFIX_RE.sub("", stripped)

        if stripped == candidate:
            return ""

        candidate = stripped

    return ""


def _build_unique_to(skill_id: str, english: EnglishText) -> List[str]:
    """Pals a skill is exclusive to: only skills that cannot be inherited or bought as a fruit."""
    pal_ids = _load_pal_ids_by_skill_id().get(skill_id, [])

    names: List[str] = []
    for pal_id in pal_ids:
        name = _resolve_pal_display_name(pal_id, english)
        if name and name not in names:
            names.append(name)

    return names


def _build_status_and_chance(row: Dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []

    for idx in (1, 2):
        t = row.get(f"EffectType{idx}")
        v = row.get(f"EffectValue{idx}")

        t_leaf = _leaf_enum(t)
        if not t_leaf or t_leaf.lower() == "none":
            continue

        v_str = _format_number(v)
        if not v_str:
            continue

        status_name = ACTIVE_SKILL_STATUS_EFFECT_MAP.get(t_leaf, t_leaf)
        status_name = str(status_name or "").strip()

        if not status_name:
            continue

        pairs.append((status_name, v_str))

    return pairs


def _build_range(min_range: Any, max_range: Any) -> str:
    min_str = _format_number(min_range)
    max_str = _format_number(max_range)

    if not min_str and not max_str:
        return ""
    if min_str and not max_str:
        return min_str
    if max_str and not min_str:
        return max_str
    if min_str == max_str:
        return min_str
    return f"{min_str} - {max_str}"


def _normalize_english_key(s: str) -> str:
    s = re.sub(r"\s+", " ", _trim(s))
    return s.casefold()


def _build_english_name_to_id_map(english: EnglishText) -> Dict[str, str]:
    raw = _load_json(en_name_file)
    rows = extract_datatable_rows(raw, source=os.path.basename(en_name_file)) or {}

    mapping: Dict[str, str] = {}
    prefixes = ["ACTION_SKILL_", "COOP_", "ACTIVE_"]

    for prefix in prefixes:
        for key in rows.keys():
            if not key.startswith(prefix):
                continue

            skill_id = key[len(prefix):].strip()
            if not skill_id:
                continue

            en_name = english.get(en_name_file, key)
            if not en_name:
                continue

            k = _normalize_english_key(en_name)
            if k not in mapping:
                mapping[k] = skill_id

    return mapping


def _load_waza_rows() -> Dict[str, Dict[str, Any]]:
    global _CACHED_WAZA_ROWS
    if _CACHED_WAZA_ROWS is not None:
        return _CACHED_WAZA_ROWS

    data = _load_json(waza_input_file)
    _CACHED_WAZA_ROWS = extract_datatable_rows(data, source=os.path.basename(waza_input_file)) or {}
    return _CACHED_WAZA_ROWS


def _find_waza_row_for_skill_id(waza_rows: Dict[str, Dict[str, Any]], skill_id: str) -> Optional[Dict[str, Any]]:
    target = f"EPalWazaID::{skill_id}"

    for _, row in waza_rows.items():
        if not isinstance(row, dict):
            continue

        if row.get("DisabledData") is True:
            continue

        if _trim(row.get("WazaType")) == target:
            return row

    return None


def resolve_active_skill_id_from_name(english_skill_name: str, english: Optional[EnglishText] = None) -> str:
    english = english or EnglishText()
    name_to_id = _build_english_name_to_id_map(english)
    key = _normalize_english_key(english_skill_name)
    return name_to_id.get(key, "")


def _build_active_skill_infobox_model_from_skill_id(
    skill_id: str,
    *,
    english: EnglishText,
    waza_rows: Dict[str, Dict[str, Any]],
    fruit_ids: set[str],
) -> ActiveSkillInfoboxModel:
    if not skill_id:
        return {}

    row = _find_waza_row_for_skill_id(waza_rows, skill_id)
    if not row:
        return {}

    has_fruit = skill_id in fruit_ids

    # IgnoreRandomInherit is the game's flag for "never handed down at random":
    # true means the skill cannot be bred onto a child.
    is_inheritable = not bool(row.get("IgnoreRandomInherit"))

    # A skill is exclusive when it can be reached neither by breeding nor by a skill fruit.
    unique_to = [] if (is_inheritable or has_fruit) else _build_unique_to(skill_id, english)

    display_name = english.get_active_skill_name(skill_id) or _trim(skill_id)

    desc_key = f"ACTION_SKILL_{skill_id}"
    desc_raw = english.get_raw(en_description_file, desc_key)
    desc_raw = _replace_charactername_tags(desc_raw, english)
    description = clean_english_text(desc_raw, row).replace("\r", "").strip()

    element = _normalize_element(row.get("Element"))
    ct = _format_number(row.get("CoolTime"))
    power = _format_number(row.get("Power"))
    rng = _build_range(row.get("MinRange"), row.get("MaxRange"))
    status_pairs = _build_status_and_chance(row)

    model: ActiveSkillInfoboxModel = {
        "skill_id": skill_id,
        "display_name": display_name,
        "description": description,
        "element": element,
        "ct": ct,
        "power": power,
        "range": rng,
        "unique_to": unique_to,
        "fruit": bool(has_fruit),
        "inherited": is_inheritable,
    }

    if status_pairs:
        (status1, chance1) = status_pairs[0]
        model["status"] = status1
        model["chance"] = chance1

        if len(status_pairs) > 1:
            (status2, chance2) = status_pairs[1]
            model["status2"] = status2
            model["chance2"] = chance2
    else:
        model["status"] = ""
        model["chance"] = ""

    return model


def build_active_skill_infobox_model_by_id(skill_id: str) -> ActiveSkillInfoboxModel:
    """Builder entry-point: Given an internal skill_id, return the canonical infobox model."""
    english = EnglishText()
    waza_rows = _load_waza_rows()
    fruit_ids = _load_skill_ids_with_skillcards()
    return _build_active_skill_infobox_model_from_skill_id(skill_id, english=english, waza_rows=waza_rows, fruit_ids=fruit_ids)


def build_active_skill_infobox_model_from_name(english_skill_name: str) -> ActiveSkillInfoboxModel:
    english = EnglishText()
    skill_id = resolve_active_skill_id_from_name(english_skill_name, english=english)
    if not skill_id:
        return {}

    waza_rows = _load_waza_rows()
    fruit_ids = _load_skill_ids_with_skillcards()

    return _build_active_skill_infobox_model_from_skill_id(
        skill_id,
        english=english,
        waza_rows=waza_rows,
        fruit_ids=fruit_ids,
    )


def _iter_active_skill_ids(english: EnglishText) -> List[str]:
    """Every skill id present in the English name table, deduped by id (not by display name)."""
    raw = _load_json(en_name_file)
    rows = extract_datatable_rows(raw, source=os.path.basename(en_name_file)) or {}

    skill_ids: List[str] = []
    seen: set[str] = set()
    prefixes = ["ACTION_SKILL_", "COOP_", "ACTIVE_"]

    for prefix in prefixes:
        for key in rows.keys():
            if not str(key).startswith(prefix):
                continue

            skill_id = str(key)[len(prefix):].strip()
            if not skill_id or skill_id in seen:
                continue

            name = english.get_active_skill_name(skill_id)
            if not name or name.strip().casefold() in _PLACEHOLDER_SKILL_NAMES:
                continue

            seen.add(skill_id)
            skill_ids.append(skill_id)

    return skill_ids


def build_all_active_skill_infobox_models() -> List[Tuple[str, ActiveSkillInfoboxModel]]:
    english = EnglishText()
    waza_rows = _load_waza_rows()
    fruit_ids = _load_skill_ids_with_skillcards()

    out: List[Tuple[str, ActiveSkillInfoboxModel]] = []

    # Iterate by skill id so skills that share a display name are all exported.
    for skill_id in _iter_active_skill_ids(english):
        model = _build_active_skill_infobox_model_from_skill_id(
            skill_id,
            english=english,
            waza_rows=waza_rows,
            fruit_ids=fruit_ids,
        )
        if model:
            out.append((model.get("display_name", ""), model))

    out.sort(key=lambda x: ((x[0] or "").casefold(), x[1].get("skill_id", "")))
    return out


def list_placeholder_named_skill_ids() -> List[str]:
    """Skills that exist in the Waza table but have no translated name yet."""
    english = EnglishText()
    waza_rows = _load_waza_rows()

    raw = _load_json(en_name_file)
    rows = extract_datatable_rows(raw, source=os.path.basename(en_name_file)) or {}

    out: List[str] = []
    seen: set[str] = set()

    for key in rows.keys():
        for prefix in ("ACTION_SKILL_", "COOP_", "ACTIVE_"):
            if not str(key).startswith(prefix):
                continue

            skill_id = str(key)[len(prefix):].strip()
            if not skill_id or skill_id in seen:
                continue

            name = english.get_active_skill_name(skill_id)
            if not name or name.strip().casefold() not in _PLACEHOLDER_SKILL_NAMES:
                continue

            if not _find_waza_row_for_skill_id(waza_rows, skill_id):
                continue

            seen.add(skill_id)
            out.append(skill_id)
            break

    return sorted(out)
