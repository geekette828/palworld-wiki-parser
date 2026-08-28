import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import List
from utils.console_utils import force_utf8_stdout
from builders.human_infobox import build_all_human_infobox_models, HumanInfoboxModel

force_utf8_stdout()

# Paths
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "human_infobox.txt")


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


def render_human_infobox(model: HumanInfoboxModel, *, include_heading: bool = True) -> str:
    """
    Render entry-point:
    Convert a human infobox model into canonical wikitext.
    Mirrors exports.export_item_infoboxes.render_item_infobox().
    """
    if not model:
        return ""

    display_name = (model.get("display_name") or "").strip()
    internal_id = (model.get("internal_id") or "").strip()

    lines: List[str] = []

    if include_heading:
        lines.append(f"## {display_name} ({internal_id})")

    lines.append("{{Human")
    lines.append(f"|internal_id = {model.get('internal_id', '')}")
    lines.append(f"|type = {model.get('type', '')}")
    lines.append(f"|level = {model.get('level', '')}")
    lines.append(f"|faction = {model.get('faction', '')}")
    lines.append(f"|hunger = {model.get('food', '')}")
    lines.append(f"|nocturnal = {model.get('nocturnal', '')}")
    lines.append(f"|price = {model.get('price', '')}")
    lines.append(f"|work_suitability = {model.get('work_suitability', '')}")
    lines.append(f"|active_skills = {model.get('active_skills', '')}")

    lines.append("<!-- Stats -->")
    lines.append(f"|hp = {model.get('hp', '')}")
    lines.append(f"|attack = {model.get('attack', '')}")
    lines.append(f"|defense = {model.get('defense', '')}")
    lines.append(f"|support = {model.get('support', '')}")
    lines.append(f"|stamina = {model.get('stamina', '')}")
    lines.append(f"|walk_speed = {model.get('walk_speed', '')}")
    lines.append(f"|slow_walk_speed = {model.get('slow_walk_speed', '')}")
    lines.append(f"|run_speed = {model.get('run_speed', '')}")
    lines.append(f"|ride_sprint_speed = {model.get('ride_sprint_speed', '')}")
    lines.append(f"|transport_speed = {model.get('transport_speed', '')}")
    lines.append(f"|work_speed = {model.get('work_speed', '')}")
    lines.append("}}")
    lines.append("")
    return "\n".join(lines)


def build_all_human_infoboxes_text() -> str:
    entries = build_all_human_infobox_models()

    blocks: List[str] = []
    for display_name, internal_id, model in entries:
        block = render_human_infobox(model, include_heading=True)
        if not block:
            continue
        blocks.append(block)

    return "".join(blocks).rstrip() + "\n"


def main() -> None:
    print("🔄 Building human infobox export text...")
    text = build_all_human_infoboxes_text()

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    line_count = text.count("\n") + (1 if text else 0)
    print(f"✅ Done. Wrote {line_count} lines.")


if __name__ == "__main__":
    main()
