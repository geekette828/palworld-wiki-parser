import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import List
from utils.console_utils import force_utf8_stdout
from builders.human_drop import build_human_drops_by_faction, HumanDropsModel

force_utf8_stdout()

# Paths
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "human_drops.txt")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def render_human_drop(model: HumanDropsModel) -> str:
    if not model:
        return ""

    out: List[str] = []
    out.append(f"Internal Name: {model.get('character_id','')}")
    out.append("{{Item Drop")
    out.append(f"|enemy_name = {model.get('human_name', '')}")
    out.append(f"|type = Human")
    out.append(f"|normal_drops = {model.get('drops', '')}")
    out.append(f"|alpha_drops = ")
    out.append("}}")

    return "\n".join(out).rstrip() + "\n"


def build_all_human_drops_text(*, include_blank_line: bool = True) -> str:
    grouped = build_human_drops_by_faction()

    blocks: List[str] = []
    for faction_name, models in grouped.items():
        blocks.append(f"### {faction_name}\n")
        for model in models:
            block = render_human_drop(model)
            if block:
                blocks.append(block)
                if include_blank_line:
                    blocks.append("\n")

    return "".join(blocks).rstrip() + "\n"


def main() -> None:
    print("🔄 Building human drops export text...")
    text = build_all_human_drops_text(include_blank_line=True)

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    print(f"✅ Wrote: {output_file}")


if __name__ == "__main__":
    main()
