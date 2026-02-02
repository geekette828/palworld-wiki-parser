import os
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple, Any

from utils.english_text_utils import EnglishText
from builders.item_page_summary import get_item_page_blurb

from builders.item_infobox import (
    build_item_infobox_model_by_id,
    resolve_item_id_from_name,
    ItemInfoboxModel,
)

from builders.item_recipe import (
    build_item_recipe_model_by_product_id,
    CraftingRecipeModel,
)


@dataclass(frozen=True)
class ItemPageOptions:
    include_history_section: bool = True
    include_navbox: bool = True
    include_placeholders: bool = True


@dataclass(frozen=True)
class ItemPageModel:
    item_id: str
    title: str
    infobox_model: ItemInfoboxModel
    recipe_model: Optional[CraftingRecipeModel]
    item_type: str
    subtype: str
    blurb: str


def _normalize_title(s: str) -> str:
    s = str(s or "").strip()
    return " ".join(s.split())


def resolve_item_id_and_title_from_name_or_id(
    user_title: str,
    *,
    en: Optional[EnglishText] = None,
) -> Tuple[Optional[str], str]:
    """Return (item_id, final_page_title).

    - If user_title matches an English item name: keep it as the title.
    - If user_title is an internal item id: title becomes the English display name.
    """
    en = en or EnglishText()

    raw_title = _normalize_title(user_title)
    if not raw_title:
        return None, ""

    item_id = resolve_item_id_from_name(raw_title, english=en)
    if item_id:
        return item_id, raw_title

    model = build_item_infobox_model_by_id(raw_title)
    if not model:
        return None, raw_title

    display_name = _normalize_title(model.get("display_name") or raw_title)
    return raw_title, display_name


def build_item_page_model_by_id(
    item_id: str,
    *,
    en: Optional[EnglishText] = None,
    options: Optional[ItemPageOptions] = None,
) -> Optional[ItemPageModel]:
    """Build the canonical data model needed to assemble an item page."""
    en = en or EnglishText()
    options = options or ItemPageOptions()

    item_id = str(item_id or "").strip()
    if not item_id:
        return None

    infobox_model = build_item_infobox_model_by_id(item_id)
    if not infobox_model:
        return None

    title = _normalize_title(infobox_model.get("display_name") or item_id)
    item_type = (infobox_model.get("type") or "").strip()
    subtype = (infobox_model.get("subtype") or "").strip()
    blurb = get_item_page_blurb(item_type=item_type, item_subtype=subtype) or ""

    recipe_model = build_item_recipe_model_by_product_id(item_id)

    return ItemPageModel(
        item_id=item_id,
        title=title,
        infobox_model=infobox_model,
        recipe_model=recipe_model,
        item_type=item_type,
        subtype=subtype,
        blurb=blurb,
    )


def build_item_page_model_from_name_or_id(
    user_title: str,
    *,
    en: Optional[EnglishText] = None,
    options: Optional[ItemPageOptions] = None,
) -> Tuple[str, Optional[ItemPageModel]]:
    """Resolve input to an item id and build the item page model."""
    en = en or EnglishText()
    options = options or ItemPageOptions()

    item_id, title = resolve_item_id_and_title_from_name_or_id(user_title, en=en)
    if not item_id:
        return title, None

    model = build_item_page_model_by_id(item_id, en=en, options=options)
    if not model:
        return title, None

    return title, model
