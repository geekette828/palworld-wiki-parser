import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.passive_skill_infobox import build_infobox_map

force_utf8_stdout()

output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "passive_skill_infobox.txt")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> None:
    print("🔄 Building passive skill infobox export text...")
    infobox_map = build_infobox_map()

    ordered_names = sorted(infobox_map.keys(), key=lambda s: s.casefold())
    lines = []
    for name in ordered_names:
        lines.append(infobox_map[name].rstrip())
        lines.append("")

    text = "\n".join(lines).rstrip() + "\n"

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    print(f"✅ Wrote {len(ordered_names)} passive skill infobox entries.")


if __name__ == "__main__":
    main()
