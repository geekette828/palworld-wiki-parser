import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.chest_slot_chance import (
    build_field_lottery_slot_chances_text,
)

force_utf8_stdout()

output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> None:
    print("🔄 Building field lottery slot chances...")

    text = build_field_lottery_slot_chances_text()
    output_path = os.path.join(output_directory, "chest_slot_chances.txt")

    write_text(output_path, text)

    print(f"✅ Wrote {output_path}")


if __name__ == "__main__":
    main()
