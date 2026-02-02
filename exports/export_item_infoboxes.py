import os
import sys
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.item_infobox import build_all_item_infobox_models, ItemInfoboxModel

force_utf8_stdout()

output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "item_infobox.txt")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _trim(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def render_item_infobox(model: ItemInfoboxModel, *, include_heading: bool = True) -> str:
    """
    Render entry-point:
    Convert an infobox model into canonical wikitext.
    """
    if not model:
        return ""

    display_name = (model.get("display_name") or "").strip()

    lines: List[str] = []

    if include_heading:
        lines.append(f"## {display_name}")

    lines.extend([
        "{{Item",
        f"|description = {model.get('description', '')}",
        f"|type = {model.get('type', '')}",
        f"|subtype = {model.get('subtype', '')}",
    ])

    # Only include rarity/sell in the top section when not using qualities
    if not _trim(model.get("qualities")):
        lines.append(f"|rarity = {model.get('rarity', '')}")
        lines.append(f"|sell = {model.get('sell', '')}")

    lines.extend([
        f"|weight = {model.get('weight', '')}",
        f"|technology = {model.get('technology', '')}",
    ])

    # Equipment section
    if _trim(model.get("qualities")) or _trim(model.get("durability")) or _trim(model.get("attack")) or _trim(model.get("magazine")) or _trim(model.get("health")) or _trim(model.get("defense")) or _trim(model.get("shield")) or _trim(model.get("equip_effect")):
        lines.append("<!-- Equipment Data -->")

        qualities = _trim(model.get("qualities"))
        if qualities:
            lines.append("|qualities =")
            lines.append(f"  {qualities}")
        else:
            if _trim(model.get("durability")):
                lines.append(f"|durability = {model.get('durability', '')}")
            if _trim(model.get("attack")):
                lines.append(f"|attack = {model.get('attack', '')}")
            if _trim(model.get("magazine")):
                lines.append(f"|magazine = {model.get('magazine', '')}")
            if _trim(model.get("health")):
                lines.append(f"|health = {model.get('health', '')}")
            if _trim(model.get("defense")):
                lines.append(f"|defense = {model.get('defense', '')}")
            if _trim(model.get("shield")):
                lines.append(f"|shield = {model.get('shield', '')}")
            if _trim(model.get("equip_effect")):
                lines.append(f"|equip_effect = {model.get('equip_effect', '')}")

    # Consumable section
    if _trim(model.get("nutrition")) or _trim(model.get("san")) or _trim(model.get("corruption")) or _trim(model.get("consumeEffect")):
        lines.append("<!-- Consumable Data -->")
        if _trim(model.get("nutrition")):
            lines.append(f"|nutrition = {model.get('nutrition', '')}")
        if _trim(model.get("san")):
            lines.append(f"|san = {model.get('san', '')}")
        if _trim(model.get("corruption")):
            lines.append(f"|corruption = {model.get('corruption', '')}")
        if _trim(model.get("consumeEffect")):
            lines.append(f"|consumeEffect = {model.get('consumeEffect', '')}")

    lines.extend([
        "}}",
        "",
        "",
    ])

    return "\n".join(lines)


def build_all_item_infoboxes_text() -> str:
    entries = build_all_item_infobox_models()

    blocks: List[str] = []
    for display_name, item_id, model in entries:
        block = render_item_infobox(model, include_heading=False)
        if not block:
            continue
        header = f"## {display_name} ({item_id})\n"
        blocks.append(header + block)

    return "".join(blocks)


def main() -> None:
    print("🔄 Building item infobox export text...")
    text = build_all_item_infoboxes_text()

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    line_count = text.count("\n") + (1 if text else 0)
    print(f"✅ Done. Wrote {line_count} lines.")


if __name__ == "__main__":
    main()
