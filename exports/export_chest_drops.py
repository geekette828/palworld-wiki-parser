import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.chest_drop import build_all_chest_drop_export_models, ChestDropGroup

force_utf8_stdout()

output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def render_chest_drop_block(group: ChestDropGroup) -> str:
    chest_name = str(group.get("chest_name") or "")
    grade_number = str(group.get("grade_number") or "")
    location = str(group.get("location") or "")

    lines: List[str] = []
    lines.append("{{Chest Drop")
    lines.append(f"|chestName = {chest_name}")
    lines.append(f"|grade = {grade_number}")
    lines.append(f"|location = {location}".rstrip())

    entries = group.get("entries") or []
    # Entries already contain stable slot ordering and within-slot ordering.
    for e in entries:
        slot = int(e.get("slot_number") or 0)
        idx = int(e.get("index_in_slot") or 0)
        key_prefix = f"{slot}_{idx}"

        item_name = str(e.get("item_name") or "")
        min_num = int(e.get("min_num") or 0)
        max_num = int(e.get("max_num") or 0)
        weight = float(e.get("weight") or 0.0)

        lines.append(f"  |{key_prefix}_name = {item_name}")
        lines.append(f"   |{key_prefix}_min = {min_num}")
        lines.append(f"   |{key_prefix}_max = {max_num}")
        lines.append(f"   |{key_prefix}_weight = {weight}")

    lines.append("}}")
    return "\n".join(lines)


def build_export_text(groups: List[ChestDropGroup]) -> str:
    if not groups:
        return ""
    blocks = [render_chest_drop_block(g) for g in groups]
    return ("\n\n".join(blocks).rstrip() + "\n")


def main() -> None:
    print("🔄 Building chest drop exports...")
    exports: Dict[str, List[ChestDropGroup]] = build_all_chest_drop_export_models()

    wrote = 0
    for filename, groups in exports.items():
        output_path = os.path.join(output_directory, filename)
        print(f"🔄 Writing output file: {output_path}")
        write_text(output_path, build_export_text(groups))
        wrote += 1

    print(f"✅ Done. Wrote {wrote} export file(s).")


if __name__ == "__main__":
    main()
