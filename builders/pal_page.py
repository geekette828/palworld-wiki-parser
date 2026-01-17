import re
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from config import constants

from utils.english_text_utils import EnglishText, clean_english_text
from utils.json_datatable_utils import extract_datatable_rows

from builders.pal_infobox import (
    load_rows,
    build_waza_master_index,
    build_pal_infobox_wikitext,
    after_double_colon,
    normalize_element,
)
from builders.pal_drops import (
    load_json,
    index_drop_rows_by_character_id,
    build_pal_drop_wikitext,
)
from builders.pal_breeding import (
    build_pal_breeding_wikitext,
)


PARAM_INPUT_FILE = os.path.join(
    constants.INPUT_DIRECTORY,
    "Character",
    "DT_PalMonsterParameter.json",
)

DROP_INPUT_FILE = os.path.join(
    constants.INPUT_DIRECTORY,
    "Character",
    "DT_PalDropItem.json",
)

ACTIVE_SKILL_INPUT_FILE = os.path.join(
    constants.INPUT_DIRECTORY,
    "Waza",
    "DT_WazaMasterLevel.json",
)

_CHARACTER_NAME_TAG_RE = re.compile(
    r"<characterName\b[^|>]*\|([^|>]+)\|/>",
    flags=re.IGNORECASE,
)

def _resolve_character_name_tags(text: str, en: EnglishText) -> str:
    s = str(text or "")

    def repl(m: re.Match) -> str:
        pal_id = (m.group(1) or "").strip()
        if not pal_id:
            return ""
        return en.get_pal_name(pal_id) or pal_id

    return _CHARACTER_NAME_TAG_RE.sub(repl, s)


def _clean_paldeck_description(raw: str, en: EnglishText, row: Optional[dict]) -> str:
    # Only special-case CRLF -> space (leave lone \r handling to existing utils)
    s = str(raw or "").replace("\r\n", " ")

    # Must resolve BEFORE clean_english_text strips tags
    s = _resolve_character_name_tags(s, en)

    s = clean_english_text(s, row)

    # Compact whitespace for stable output
    return " ".join(s.split())


@dataclass(frozen=True)
class PalPageOptions:
    include_placeholders: bool = True
    include_navbox_and_category: bool = True
    include_history_section: bool = True
    include_paldeck: bool = True
    include_intro_line: bool = True
    include_characteristics: bool = True
    include_drops: bool = True
    include_breeding: bool = True


AI_BEHAVIOR_TEMPLATES: Dict[str, str] = {
    "Friendly": (
        "<PALNAME> is generally non-aggressive and will not attack players on sight, allowing them to be approached safely. "
        "It only becomes hostile if directly attacked or if it witnesses a nearby member of its species being harmed. "
        "Once provoked, <PALNAME> may retaliate using basic defensive behaviors or attacks and will typically remain aggressive "
        "until it is defeated or the player leaves its render distance."
    ),
    "Escape_to_Battle": (
        "<PALNAME> is naturally passive and will attempt to flee immediately upon spotting a player rather than engaging in combat. "
        "It often prioritizes escape over confrontation and may cower briefly when first attacked. If pursued or harmed, <PALNAME> "
        "can shift from evasive behavior to active aggression, defending itself against the player. Once provoked, it will engage "
        "in combat and remain hostile until defeated or the player disengages."
    ),
    "Warlike": (
        "<PALNAME> is highly aggressive and will attack the player on sight as soon as it notices them. "
        "It does not require provocation to engage and will immediately initiate combat upon detecting a nearby player."
    ),
    "NotInterested": (
        "<PALNAME> is peaceful and shows no interest in engaging the player, remaining non-hostile unless directly attacked. "
        "It will not initiate combat under any circumstances and only retaliates if provoked."
    ),
}


def _get_primary_element(rows: Dict[str, dict], base: str) -> str:
    row = rows.get(base)
    if not isinstance(row, dict):
        return ""

    raw = after_double_colon(row.get("ElementType1"))
    return normalize_element(raw)


def _get_ai_response(rows: Dict[str, dict], base: str) -> str:
    row = rows.get(base)
    if not isinstance(row, dict):
        return ""
    v = row.get("AIResponse")
    return str(v).strip() if v is not None else ""


def _build_behavior_text(pal_name: str, ai_response: str, *, include_placeholders: bool) -> str:
    pal_name = str(pal_name or "").strip()
    ai_response = str(ai_response or "").strip()

    if ai_response in AI_BEHAVIOR_TEMPLATES:
        return AI_BEHAVIOR_TEMPLATES[ai_response].replace("<PALNAME>", pal_name)

    if include_placeholders:
        return "<We're going to write this in a minute, put a placeholder for now>"

    return ""


def _extract_template_block(wikitext: str, template_name: str) -> str:
    if not wikitext:
        return ""

    lines = wikitext.splitlines()
    start = None
    end = None

    for i, line in enumerate(lines):
        if line.strip().startswith(f"{{{{{template_name}"):
            start = i
            break

    if start is None:
        return ""

    for j in range(start, len(lines)):
        if lines[j].strip() == "}}":
            end = j
            break

    if end is None:
        return ""

    return "\n".join(lines[start : end + 1]).rstrip()


def build_pal_page_sections(
    base: str,
    *,
    rows: Dict[str, dict],
    waza_by_pal_id: Dict[str, list],
    drops_by_character_id: Dict[str, list],
    en: EnglishText,
    options: Optional[PalPageOptions] = None,
) -> Dict[str, str]:
    options = options or PalPageOptions()

    base = str(base or "").strip()
    if not base:
        return {}

    normal = rows.get(base)
    boss = rows.get(f"BOSS_{base}")
    if not isinstance(normal, dict) or not isinstance(boss, dict):
        return {}

    pal_name = en.get_pal_name(base)  # uses localization lookup :contentReference[oaicite:3]{index=3}
    ele1 = _get_primary_element(rows, base)

    sections: Dict[str, str] = {}

    sections["infobox"] = build_pal_infobox_wikitext(
        base,
        rows=rows,
        waza_by_pal_id=waza_by_pal_id,
        en=en,
        include_header=False,
    ).rstrip()

    if options.include_paldeck:
        key = f"PAL_LONG_DESC_{base}"
        raw = en.get_raw(constants.EN_PAL_LONG_DESCRIPTION_FILE, key)
        row = en._get_table(constants.EN_PAL_LONG_DESCRIPTION_FILE).get(key)  # same cached table en uses
        desc = _clean_paldeck_description(raw, en, row)

        if desc:
            sections["paldeck"] = f"{{{{paldeck|{desc}}}}}"
        elif options.include_placeholders:
            sections["paldeck"] = "{{paldeck|<!--Pal Deck Summary Goes here-->}}"


    if options.include_intro_line:
        if ele1:
            sections["intro"] = (
                f"'''{pal_name}''' is a {{{{i|{ele1}}}}} [[Elements|element]] [[Pals|Pal]]. "
                "<!-- Information on the pal, and a description on what the pal looks like. -->"
            )
        else:
            sections["intro"] = (
                f"'''{pal_name}''' is a [[Pals|Pal]]. "
                "<!-- Information on the pal, and a description on what the pal looks like. -->"
            )

    if options.include_characteristics:
        ai_response = _get_ai_response(rows, base)

        # NEW: behavior comes from AIResponse mapping (fallback to placeholder if configured)
        sections["behavior"] = _build_behavior_text(
            pal_name,
            ai_response,
            include_placeholders=options.include_placeholders,
        )

        # Utility remains a placeholder for now (as requested)
        sections["utility"] = (
            f"{pal_name} is able to ???. <!-- Describe how this Pal can help the player -->"
            if options.include_placeholders
            else ""
        )

    if options.include_drops:
        sections["drops"] = build_pal_drop_wikitext(
            base,
            param_rows=rows,
            drops_by_character_id=drops_by_character_id,
            en=en,
        ).rstrip()

    if options.include_breeding:
        sections["breeding_intro"] = (
            "[[Breeding]] allows Pals to be paired together to produce offspring, "
            "with outcomes determined by various breeding statistics and special parent combinations."
        )

        breeding_full = build_pal_breeding_wikitext(
            base,
            rows=rows,
            en=en,
            include_header=False,
        )
        sections["breeding"] = _extract_template_block(breeding_full, "Breeding")

    if options.include_history_section:
        sections["history"] = "\n".join(
            [
                "==History==",
                "* [[0.?.?]]",
                "** Introduced.",
            ]
        )

    if options.include_navbox_and_category:
        sections["footer"] = "\n".join(
            [
                "{{Navbox Pals}}",
                "[[Category:Pals]]",
            ]
        )

    return sections


def build_pal_page_wikitext(
    base: str,
    *,
    rows: Dict[str, dict],
    waza_by_pal_id: Dict[str, list],
    drops_by_character_id: Dict[str, list],
    en: EnglishText,
    options: Optional[PalPageOptions] = None,
) -> str:
    options = options or PalPageOptions()

    sections = build_pal_page_sections(
        base,
        rows=rows,
        waza_by_pal_id=waza_by_pal_id,
        drops_by_character_id=drops_by_character_id,
        en=en,
        options=options,
    )

    if not sections:
        return ""

    out: List[str] = []

    def add(key: str) -> None:
        v = sections.get(key, "").strip()
        if v:
            out.append(v)
            out.append("")

    infobox = sections.get("infobox", "").strip()
    if infobox:
        out.append(infobox)

    paldeck = sections.get("paldeck", "").strip()
    if paldeck:
        out.append(paldeck)

    intro = sections.get("intro", "").strip()
    if intro:
        out.append(intro)

    out.append("") 

    if options.include_characteristics:
        out.append("==Characteristics==")
        out.append("===Behavior and Habitat===")
        add("behavior")
        out.append("===Utility===")
        add("utility")
        out.append("<!--")
        out.append("===Variants===")
        out.append("Link to other variants of this pal")
        out.append("-->")
        out.append("")

    if options.include_drops:
        out.append("==Drops==")
        add("drops")

    if options.include_breeding:
        out.append("==Breeding==")

        intro = sections.get("breeding_intro", "").strip()
        if intro:
            out.append(intro)

        breeding = sections.get("breeding", "").strip()
        if breeding:
            out.append(breeding)

        out.append("")

    if options.include_placeholders:
        out.extend(
            [
                "<!--==Trivia==",
                "* This Pal was featured in [[Paldeck]] #??? on ??/??/??:",
                "",
                "==Media==",
                "<gallery widths=150>",
                "FileName.png|Caption of File",
                "</gallery>",
                "-->",
                "",
            ]
        )

    add("history")
    add("footer")

    return "\n".join(out).rstrip() + "\n"


def build_pal_page_from_files(
    base: str,
    *,
    options: Optional[PalPageOptions] = None,
) -> str:
    en = EnglishText()

    rows = load_rows(PARAM_INPUT_FILE, source="DT_PalMonsterParameter")
  
    waza_rows = load_rows(ACTIVE_SKILL_INPUT_FILE, source="DT_WazaMasterLevel")
    waza_by_pal_id = build_waza_master_index(waza_rows)

    drop_data = load_json(DROP_INPUT_FILE)
    drop_rows = extract_datatable_rows(drop_data, source="DT_PalDropItem")
    drops_by_character_id = index_drop_rows_by_character_id(drop_rows)

    return build_pal_page_wikitext(
        base,
        rows=rows,
        waza_by_pal_id=waza_by_pal_id,
        drops_by_character_id=drops_by_character_id,
        en=en,
        options=options,
    )

