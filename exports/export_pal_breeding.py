import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import List
from utils.console_utils import force_utf8_stdout
from builders.pal_breeding import build_all_pal_breeding_models, PalBreedingModel
force_utf8_stdout()

#Paths
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "pal_breeding.txt")



def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def render_pal_breeding(model: PalBreedingModel, *, include_header: bool = True) -> str:
    if not model:
        return ""

    base_id = model.get("base_id", "")
    display_name = model.get("display_name", base_id)

    out: List[str] = []

    if include_header:
        out.append(f"# {display_name} ({base_id})")

    out.append("==Breeding==")
    out.append(
        "[[Breeding]] allows Pals to be paired together to produce offspring, with outcomes determined by various breeding statistics and special parent combinations. "
    )
    out.append("{{Breeding")
    out.append(f"|breeding_rank = {model.get('breeding_rank', '')}")
    out.append(f"|male_probability = {model.get('male_probability', '')}")
    out.append(f"|combi_duplicate_priority = {model.get('combi_duplicate_priority', '')}")
    out.append(f"|egg = {model.get('egg', '')}")
    out.append("|uniqueCombos = ")
    out.append("}}")
    out.append("")
    out.append("")

    return "\n".join(out).rstrip() + "\n"


def build_all_pal_breeding_text(*, include_headers: bool = True) -> str:
    items = build_all_pal_breeding_models()

    blocks: List[str] = []
    for _, model in items:
        block = render_pal_breeding(model, include_header=include_headers)
        if block:
            blocks.append(block)
            blocks.append("\n")

    return "".join(blocks).rstrip() + "\n"


def main() -> None:
    print("🔄 Building pal breeding export text...")
    text = build_all_pal_breeding_text(include_headers=True)

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    line_count = text.count("\n") + (1 if text else 0)
    print(f"✅ Done. Wrote {line_count} lines.")


if __name__ == "__main__":
    main()
