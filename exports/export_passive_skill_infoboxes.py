import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.passive_skill_infobox import build_all_passive_skill_models, PassiveSkillModel
force_utf8_stdout()

#Paths
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "passive_skill_infobox.txt")



def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def escape_pipe(v: str) -> str:
    return str(v or "").replace("|", "{{!}}")


def render_passive_skill_infobox(model: PassiveSkillModel) -> str:
    title = model.get("display_name", "")
    description = model.get("description", "")
    rank = model.get("rank", "")

    effects_parts = []
    for e in model.get("effects", []) or []:
        label = e.get("label", "")
        val = e.get("value_text", "")
        if label and val:
            effects_parts.append(f"{label}*{val}")
    effects = "; ".join(effects_parts)

    lines = []
    lines.append("{{Passive Skill Infobox")
    lines.append(f"|title = {escape_pipe(title)}")
    lines.append(f"|description = {escape_pipe(description)}")
    lines.append(f"|rank = {escape_pipe(str(rank or ''))}")
    lines.append(f"|effects = {escape_pipe(effects)}")
    lines.append("}}")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    print("🔄 Building passive skill infobox export text...")
    models = build_all_passive_skill_models()

    lines = []
    for model in models:
        lines.append(render_passive_skill_infobox(model).rstrip())
        lines.append("")

    text = "\n".join(lines).rstrip() + "\n"

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    print(f"✅ Wrote {len(models)} passive skill infobox entries.")


if __name__ == "__main__":
    main()
