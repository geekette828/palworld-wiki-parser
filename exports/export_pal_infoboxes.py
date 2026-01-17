import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.pal_infobox import build_all_pal_infoboxes_text

force_utf8_stdout()

output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "pal_infobox.txt")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> None:
    print("🔄 Building pal infobox export text...")
    text = build_all_pal_infoboxes_text(include_headers=True)

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    print("✅ Done.")


if __name__ == "__main__":
    main()
