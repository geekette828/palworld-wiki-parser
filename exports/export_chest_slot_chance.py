import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.chest_slot_chance import build_chest_slot_chance_models
force_utf8_stdout()

#Paths
output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")



def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> None:
    print("🔄 Building chest slot chance JSON...")

    data = build_chest_slot_chance_models()
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True).rstrip() + "\n"

    output_path = os.path.join(output_directory, "ChestSlotChance.json")

    write_text(output_path, text)

    print(f"✅ Wrote {output_path}")
    print("📝 Paste this into Data:ChestSlotChance.json")


if __name__ == "__main__":
    main()
