import os
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple

from utils.english_text_utils import EnglishText

from builders.item_infobox import (
    build_item_infobox_model_for_page,
    render_item_infobox,
    resolve_item_id_from_english_name,
)

from builders.item_recipe import (
    build_item_recipe_wikitext,
)


@dataclass(frozen=True)
class ItemPageOptions:
    include_history_section: bool = True
    include_navbox: bool = True
    include_placeholders: bool = True


def _normalize_title(s: str) -> str:
    s = str(s or "").strip()
    return " ".join(s.split())

def _is_pal_bounty_token(item_type: str) -> bool:
    return (item_type or "").strip() == "Pal Bounty Token"


def _navbox_for_item(*, item_type: str, subtype: str) -> str:
    t = (item_type or "").strip()
    st = (subtype or "").strip()

    if t in {"Armor", "Weapon", "Accessory", "Sphere"}:
        return "{{Navbox Gear}}"

    if t == "Material":
        return "{{Navbox Materials}}"

    if t == "Consumable":
        if st in {"Food", "Ingredient"}:
            return "{{Navbox Ingredients}}"
        return "{{Navbox Consumables}}"

    if st == "Skill Fruit":
        return "{{Navbox Skill Fruit}}"

    return ""


def build_item_page_sections(
    item_id: str,
    *,
    en: EnglishText,
    options: Optional[ItemPageOptions] = None,
) -> Dict[str, str]:
    options = options or ItemPageOptions()

    item_id = str(item_id or "").strip()
    if not item_id:
        return {}

    model = build_item_infobox_model_for_page(item_id)
    if not model:
        return {}

    display_name = (model.get("display_name") or "").strip()
    if not display_name:
        return {}

    item_type = (model.get("type") or "").strip()
    subtype = (model.get("subtype") or "").strip()

    sections: Dict[str, str] = {}

    sections["infobox"] = render_item_infobox(model, include_heading=False).rstrip()

    # Summary (for now, single generic line)
    if item_type:
        sections["summary"] = f"'''{display_name}''' is a [[{item_type}]] item."
    else:
        sections["summary"] = f"'''{display_name}''' is an item."

    # Acquisition section (templates only for now)
    sections["acquisition"] = "\n".join(
        [
            "==Acquisition==",
            "===Merchants===",
            "{{Shops}}",
            "",
            "===Pal Drops===",
            "{{Drops}}",
        ]
    )

    # Crafting section
    recipe_text = build_item_recipe_wikitext(item_id).strip()

    crafted_from_lines: List[str] = []
    crafted_from_lines.append("==Crafting==")
    crafted_from_lines.append("===Crafted From===")

    if recipe_text:
        crafted_from_lines.append(recipe_text)
    elif options.include_placeholders:
        crafted_from_lines.append("<!-- No crafting recipe template available for this item. -->")

    crafted_from_lines.extend(
        [
            "",
            "===Used In===",
            "{{Used In Crafting}}",
        ]
    )

    sections["crafting"] = "\n".join(crafted_from_lines).rstrip()

    # History
    if options.include_history_section:
        sections["history"] = "\n".join(
            [
                "==History==",
                "* [[?.?.?]]",
                "** Introduced.",
            ]
        )

    # Footer
    if options.include_navbox:
        navbox = _navbox_for_item(item_type=item_type, subtype=subtype)
        if navbox:
            sections["footer"] = navbox

    # Optional placeholders for trivia/media
    if options.include_placeholders:
        sections["placeholders"] = "\n".join(
            [
                "<!--==Trivia==",
                "*",
                "",
                "==Media==",
                "<gallery>",
                "FileName.png|File Description",
                "</gallery>",
                "-->",
            ]
        )

    return sections


def build_item_page_wikitext(
    item_id: str,
    *,
    en: EnglishText,
    options: Optional[ItemPageOptions] = None,
) -> str:
    options = options or ItemPageOptions()

    model = build_item_infobox_model_for_page(item_id)
    if not model:
        return ""

    item_type = (model.get("type") or "").strip()

    # Pal Bounty Token → redirect only
    if _is_pal_bounty_token(item_type):
        return "#REDIRECT [[Pal_Bounty_Token]]\n"

    sections = build_item_page_sections(item_id, en=en, options=options)
    if not sections:
        return ""

    out: List[str] = []

    def add(key: str) -> None:
        v = (sections.get(key) or "").strip()
        if v:
            out.append(v)
            out.append("")

    add("infobox")
    add("summary")
    add("acquisition")
    add("crafting")

    if options.include_placeholders:
        add("placeholders")

    add("history")
    add("footer")

    return "\n".join(out).rstrip() + "\n"


def resolve_item_id_and_title(user_title: str, *, en: Optional[EnglishText] = None) -> Tuple[Optional[str], str]:
    """
    Returns (item_id, final_page_title)

    - If user_title matches an English item name: keep it as the title.
    - If user_title is an internal item id: title becomes the English display name.
    """
    en = en or EnglishText()

    raw_title = _normalize_title(user_title)
    if not raw_title:
        return None, ""

    # Try: English name -> item_id
    item_id = resolve_item_id_from_english_name(raw_title, english=en)
    if item_id:
        return item_id, raw_title

    # Otherwise treat it as an internal ID
    model = build_item_infobox_model_for_page(raw_title)
    if not model:
        return None, raw_title

    display_name = _normalize_title(model.get("display_name") or raw_title)
    return raw_title, display_name


def build_item_page_from_name_or_id(
    name_or_id: str,
    *,
    options: Optional[ItemPageOptions] = None,
) -> Tuple[str, str]:
    """
    Convenience wrapper:
    pass English name or internal id, get (title, page_text).
    """
    en = EnglishText()

    item_id, title = resolve_item_id_and_title(name_or_id, en=en)
    if not item_id:
        return "", ""

    text = build_item_page_wikitext(item_id, en=en, options=options)
    return title, text
