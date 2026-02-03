import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import List
from utils.console_utils import force_utf8_stdout
from builders.pal_infobox import (build_all_pal_infobox_models, PalInfoboxModel, STATS_MAP, ALPHA_ELIGIBLE_PARAMS)
force_utf8_stdout()

#Paths
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "pal_infobox.txt")



def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def render_pal_infobox(model: PalInfoboxModel, *, include_header: bool = True) -> str:
    if not model:
        return ""

    base_id = (model.get("base_id") or "").strip()
    display_name = (model.get("display_name") or base_id).strip()

    lines: List[str] = []

    if include_header:
        lines.append(f"# {display_name} ({base_id})")

    lines.append("{{Pal")
    lines.append(f"|no = {model.get('no', '')}")
    lines.append(f"|alpha_title = {model.get('alpha_title', '')}")
    lines.append(f"|ele1 = {model.get('ele1', '')}")
    lines.append(f"|ele2 = {model.get('ele2', '')}")
    lines.append(f"|pal_size = {model.get('pal_size', '')}")

    lines.append(f"|partner_skill_name = {model.get('partner_skill_name', '')}")
    lines.append(f"|partner_skill_desc = {model.get('partner_skill_desc', '')}")
    lines.append(f"|partner_skill_icon = {model.get('partner_skill_icon', '')}")

    lines.append("|pal_gear = ")
    lines.append(f"|work_suitability = {model.get('work_suitability', '')}")

    lines.append("<!-- Basics -->")
    lines.append(f"|hunger = {model.get('hunger', '')}")
    lines.append(f"|nocturnal = {model.get('nocturnal', '')}")
    lines.append(f"|sell_price = {model.get('sell_price', '')}")

    lines.append("<!-- Skills -->")
    lines.append(f"|passive_skills = {model.get('passive_skills', '')}")
    lines.append(f"|active_skills = {model.get('active_skills', '')}")

    lines.append("<!-- Stats -->")

    stats = model.get("stats") or {}
    alpha_stats = model.get("alpha_stats") or {}

    for _, param in STATS_MAP.items():
        lines.append(f"|{param} = {stats.get(param, '')}")

        if param in ALPHA_ELIGIBLE_PARAMS and param in alpha_stats:
            lines.append(f"|alpha_{param} = {alpha_stats.get(param, '')}")

    lines.append("}}")
    return "\n".join(lines).rstrip() + "\n"


def build_all_pal_infoboxes_text(*, include_headers: bool = True) -> str:
    items = build_all_pal_infobox_models()

    blocks: List[str] = []
    for _, model in items:
        block = render_pal_infobox(model, include_header=include_headers)
        if block:
            blocks.append(block)
            blocks.append("\n")

    return "".join(blocks).rstrip() + "\n"


def main() -> None:
    print("🔄 Building pal infobox export text...")
    text = build_all_pal_infoboxes_text(include_headers=True)

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    line_count = text.count("\n") + (1 if text else 0)
    print(f"✅ Done. Wrote {line_count} lines.")


if __name__ == "__main__":
    main()
