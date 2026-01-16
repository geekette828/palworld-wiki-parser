import os
import re
import sys
import json
from typing import Any, Dict, Optional, Tuple, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from config.name_map import ELEMENT_NAME_MAP, ACTIVE_SKILL_STATUS_EFFECT_MAP
from utils.english_text_utils import EnglishText, clean_english_text
from utils.json_datatable_utils import extract_datatable_rows
from utils.console_utils import force_utf8_stdout

force_utf8_stdout()

# Paths
param_input_file = os.path.join(constants.INPUT_DIRECTORY, "Waza", "DT_WazaDataTable.json")
item_input_file = os.path.join(constants.INPUT_DIRECTORY, "Item", "DT_ItemDataTable.json")
en_name_file = constants.EN_SKILL_NAME_FILE
en_description_file = constants.EN_SKILL_DESC_FILE
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "active_skill_infobox.txt")

_CACHED_WAZA_ROWS: Optional[Dict[str, Dict[str, Any]]] = None
_CACHED_SKILL_IDS_WITH_SKILLCARDS: Optional[set[str]] = None

_CHARACTERNAME_TAG_RE = re.compile(r"<characterName id=\|([^|]+)\|/>([’']?s)?", re.IGNORECASE)

def _replace_charactername_tags(text: str, english: EnglishText) -> str:
    s = str(text or "")

    def repl(m: re.Match) -> str:
        pal_id = (m.group(1) or "").strip()
        suffix = (m.group(2) or "").strip()

        pal_name = english.get_pal_name(pal_id) or pal_id

        if suffix:
            return f"{pal_name}'s"
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

        # If this flag exists and is false, treat it as not obtainable/usable
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
    # Case-insensitive, collapse whitespace
    s = re.sub(r"\s+", " ", _trim(s))
    return s.casefold()


def _build_english_name_to_id_map(english: EnglishText) -> Dict[str, str]:
    """
    Invert DT_SkillNameText_Common entries so we can accept English skill names as inputs.
    We only map keys that look like active skills:
      ACTION_SKILL_<id>, COOP_<id>, ACTIVE_<id>
    """
    raw = _load_json(en_name_file)
    rows = extract_datatable_rows(raw, source=os.path.basename(en_name_file)) or {}

    mapping: Dict[str, str] = {}

    # Prefer ACTION_SKILL_ over COOP_ over ACTIVE_ if collisions happen
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


def build_active_skill_infobox(english_skill_name: str) -> str:
    """
    External-friendly helper: pass an English skill name, get one infobox block back.
    """
    english = EnglishText()
    name_to_id = _build_english_name_to_id_map(english)

    key = _normalize_english_key(english_skill_name)
    skill_id = name_to_id.get(key)
    if not skill_id:
        return ""
    
    waza_rows = _load_waza_rows()
    row = _find_waza_row_for_skill_id(waza_rows, skill_id)
    if not row:
        return ""

    has_fruit = skill_id in _load_skill_ids_with_skillcards()

    # Skill display name (English)
    display_name = english.get_active_skill_name(skill_id) or _trim(english_skill_name)

    # Description: pull raw localized string, then clean it using the Waza row so {EffectValue#} works.
    desc_key = f"ACTION_SKILL_{skill_id}"
    desc_raw = english.get_raw(en_description_file, desc_key)
    desc_raw = _replace_charactername_tags(desc_raw, english)
    description = clean_english_text(desc_raw, row).replace("\r", "").strip()

    element = _normalize_element(row.get("Element"))
    ct = _format_number(row.get("CoolTime"))
    power = _format_number(row.get("Power"))
    rng = _build_range(row.get("MinRange"), row.get("MaxRange"))
    status_pairs = _build_status_and_chance(row)

    lines = [
        f"## {display_name}",
        "{{Active Skill",
        f"|description = {description}",
        f"|element = {element}",
        f"|ct = {ct}",
        f"|power = {power}",
        f"|range = {rng}",
    ]

    if status_pairs:
        for i, (status, chance) in enumerate(status_pairs, start=1):
            suffix = "" if i == 1 else str(i)
            lines.append(f"|status{suffix} = {status}")
            lines.append(f"|chance{suffix} = {chance}")
    else:
        lines.append("|status = ")
        lines.append("|chance = ")

    lines.extend([
        f"|fruit = {'True' if has_fruit else 'False'}",
        "}}",
        "",
        "",
    ])

    return "\n".join(lines)

def build_all_active_skill_infoboxes_text() -> str:
    english = EnglishText()
    waza_rows = _load_waza_rows()

    # Build internal id -> english name from name table (only active skill prefixes)
    name_to_id = _build_english_name_to_id_map(english)
    # invert to id -> english
    id_to_name: Dict[str, str] = {}
    for en_key, skill_id in name_to_id.items():
        # recover the original English name via english.get_active_skill_name for consistent display
        id_to_name[skill_id] = english.get_active_skill_name(skill_id) or id_to_name.get(skill_id, "")

    # Only include skills that have a matching Waza row and are not disabled
    blocks: List[Tuple[str, str]] = []

    for skill_id, display_name in id_to_name.items():
        row = _find_waza_row_for_skill_id(waza_rows, skill_id)
        if not row:
            continue

        block = build_active_skill_infobox(display_name)
        if block:
            blocks.append((display_name.casefold(), block))

    blocks.sort(key=lambda x: x[0])
    return "".join(b for _, b in blocks)


def main() -> None:
    # If a skill name is passed, print only that block (useful for page builders).
    # Otherwise write all blocks to the output file.
    if len(sys.argv) > 1:
        english_name = " ".join(sys.argv[1:]).strip()
        text = build_active_skill_infobox(english_name)
        if text:
            print(text, end="")
        return

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    text = build_all_active_skill_infoboxes_text()
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Wrote: {output_file}")


if __name__ == "__main__":
    main()
