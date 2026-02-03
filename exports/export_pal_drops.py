import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import List
from utils.console_utils import force_utf8_stdout
from builders.pal_drops import build_all_pal_drops_models, PalDropsModel
force_utf8_stdout()

#Paths
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "pal_drops.txt")



def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def render_pal_drops(model: PalDropsModel) -> str:
    if not model:
        return ""

    out: List[str] = []
    out.append("{{Item Drop")
    out.append(f"|palName = {model.get('pal_name', '')}")
    out.append(f"|normal_drops = {model.get('normal_drops', '')}")
    out.append(f"|alpha_drops = {model.get('alpha_drops', '')}")
    out.append("}}")

    return "\n".join(out).rstrip() + "\n"


def build_all_pal_drops_text(*, include_blank_line: bool = True) -> str:
    items = build_all_pal_drops_models()

    blocks: List[str] = []
    for _, model in items:
        block = render_pal_drops(model)
        if block:
            blocks.append(block)
            if include_blank_line:
                blocks.append("\n")

    return "".join(blocks).rstrip() + "\n"


def main() -> None:
    print("🔄 Building pal drops export text...")
    text = build_all_pal_drops_text(include_blank_line=True)

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    print(f"✅ Wrote: {output_file}")


if __name__ == "__main__":
    main()
