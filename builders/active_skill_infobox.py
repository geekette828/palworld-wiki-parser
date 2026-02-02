import os
import re
import sys
import json
from typing import Any, Dict, Optional, Tuple, List, TypedDict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from config.name_map import ELEMENT_NAME_MAP, ACTIVE_SKILL_STATUS_EFFECT_MAP
from utils.english_text_utils import EnglishText, clean_english_text
from utils.json_datatable_utils import extract_datatable_rows
from utils.console_utils import force_utf8_stdout

force_utf8_stdout()

param_input_file = os.path.join(constants.INPUT_DIRECTORY, "Waza", "DT_WazaDataTable.json")
item_input_file = os.path.join(constants.INPUT_DIRECTORY, "Item", "DT_ItemDataTable.json")
en_name_file = constants.EN_SKILL_NAME_FILE
en_description_file = constants.EN_SKILL_DESC_FILE

_CACHED_WAZA_ROWS: Optional[Dict[str, Dict[str, Any]]] = None
_CACHED_SKILL_IDS_WITH_SKILLCARDS: Optional[set[str]] = None


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
    fruit: bool


_CHARACTERNAME_TAG_RE = re.compile(r"<characterName\s+id=\|([^|]+)\|/?>", re.IGNORECASE)


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

    data = _load_json(param_input_file)
    _CACHED_WAZA_ROWS = extract_datatable_rows(data, source=os.path.basename(param_input_file)) or {}
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


def resolve_skill_id_from_english_name(english_skill_name: str, english: Optional[EnglishText] = None) -> str:
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
        "fruit": bool(has_fruit),
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


def build_active_skill_infobox_model(english_skill_name: str) -> ActiveSkillInfoboxModel:
    english = EnglishText()
    skill_id = resolve_skill_id_from_english_name(english_skill_name, english=english)
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


def build_all_active_skill_infobox_models() -> List[Tuple[str, ActiveSkillInfoboxModel]]:
    english = EnglishText()
    waza_rows = _load_waza_rows()
    fruit_ids = _load_skill_ids_with_skillcards()

    name_to_id = _build_english_name_to_id_map(english)

    id_to_display: Dict[str, str] = {}
    for _, skill_id in name_to_id.items():
        if skill_id not in id_to_display:
            id_to_display[skill_id] = english.get_active_skill_name(skill_id) or ""

    out: List[Tuple[str, ActiveSkillInfoboxModel]] = []

    for skill_id, display_name in id_to_display.items():
        model = _build_active_skill_infobox_model_from_skill_id(
            skill_id,
            english=english,
            waza_rows=waza_rows,
            fruit_ids=fruit_ids,
        )
        if model:
            out.append((display_name or model.get("display_name", ""), model))

    out.sort(key=lambda x: (x[0] or "").casefold())
    return out
