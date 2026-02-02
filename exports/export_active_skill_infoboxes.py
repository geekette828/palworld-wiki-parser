import os
import sys
from typing import List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.active_skill_infobox import build_all_active_skill_infobox_models, ActiveSkillInfoboxModel

force_utf8_stdout()

output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "active_skill_infobox.txt")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def render_active_skill_infobox(model: ActiveSkillInfoboxModel, *, include_heading: bool = True) -> str:
    if not model:
        return ""

    display_name = (model.get("display_name") or "").strip()
    description = model.get("description", "")
    element = model.get("element", "")
    ct = model.get("ct", "")
    power = model.get("power", "")
    rng = model.get("range", "")
    fruit = "True" if model.get("fruit") else "False"

    lines: List[str] = []

    if include_heading:
        lines.append(f"## {display_name}")

    lines.extend([
        "{{Active Skill",
        f"|description = {description}",
        f"|element = {element}",
        f"|ct = {ct}",
        f"|power = {power}",
        f"|range = {rng}",
    ])

    status = model.get("status", "")
    chance = model.get("chance", "")

    status2 = model.get("status2", "")
    chance2 = model.get("chance2", "")

    if status or chance:
        lines.append(f"|status = {status}")
        lines.append(f"|chance = {chance}")

        if status2 or chance2:
            lines.append(f"|status2 = {status2}")
            lines.append(f"|chance2 = {chance2}")
    else:
        lines.append("|status = ")
        lines.append("|chance = ")

    lines.extend([
        f"|fruit = {fruit}",
        "}}",
        "",
        "",
    ])

    return "\n".join(lines)


def build_all_active_skill_infoboxes_text() -> str:
    items = build_all_active_skill_infobox_models()
    return "".join(render_active_skill_infobox(model, include_heading=True) for _, model in items)


def main() -> None:
    print("🔄 Building active skill infobox export text...")
    text = build_all_active_skill_infoboxes_text()

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    line_count = text.count("\n") + (1 if text else 0)
    print(f"✅ Done. Wrote {line_count} lines.")


if __name__ == "__main__":
    main()
