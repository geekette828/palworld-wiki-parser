import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.pal_breeding import build_all_pal_breeding_text

force_utf8_stdout()

output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "pal_breeding.txt")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> None:
    print("🔄 Building pal breeding export text...")
    text = build_all_pal_breeding_text(include_headers=True)

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    print(f"✅ Wrote pal breeding data to: {output_file}")


if __name__ == "__main__":
    main()
