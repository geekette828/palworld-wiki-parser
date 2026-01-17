import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.active_skill_infobox import build_all_active_skill_infoboxes_text

force_utf8_stdout()

output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "active_skill_infobox.txt",)


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> None:
    print("🔄 Building active skill infobox export text...")
    text = build_all_active_skill_infoboxes_text()

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    line_count = text.count("\n") + (1 if text else 0)
    print(f"✅ Done. Wrote {line_count} lines.")


if __name__ == "__main__":
    main()
