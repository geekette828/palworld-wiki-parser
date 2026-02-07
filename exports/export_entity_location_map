import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import Any, Dict, List, Tuple
from utils.console_utils import force_utf8_stdout
from builders.entity_spawn import build_all_spawn_point_models, SpawnPointModel
force_utf8_stdout()

#Paths
OUTPUT_FILE_PATH = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "entity_location_map.txt")



def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def _group_spawn_points(
    models: List[SpawnPointModel],
) -> Dict[Tuple[str, str, Any], List[str]]:
    """
    Group spawn points by (name, variant, level) and collect coords.
    """
    grouped: Dict[Tuple[str, str, Any], List[str]] = {}

    for m in models:
        name = str(m.get("name") or "").strip()
        variant = str(m.get("variant") or "").strip()
        level = m.get("level")
        coords = str(m.get("coords") or "").strip()

        if not name or not coords:
            continue

        key = (name, variant, level)
        grouped.setdefault(key, []).append(coords)

    return grouped


def render_entity_location_map(
    name: str,
    variant: str,
    level: Any,
    coords_list: List[str],
) -> str:
    lines = [
        "{{Entity Location Map",
        f"|name = {name}",
        "|location = ",
        f"|variant = {variant}",
        f"|level = {level if isinstance(level, int) else ''}",
    ]

    for i, coords in enumerate(coords_list, start=1):
        suffix = "" if i == 1 else str(i)
        lines.append(f"|coords{suffix} = {coords}")

    lines.append("}}")
    return "\n".join(lines)


def main() -> None:
    print("🔄 Building Entity Location Map export...")

    models = build_all_spawn_point_models()
    print(f"🔍 Loaded {len(models)} spawn points")

    grouped = _group_spawn_points(models)

    blocks: List[str] = []
    for (name, variant, level), coords_list in grouped.items():
        blocks.append(
            render_entity_location_map(
                name=name,
                variant=variant,
                level=level,
                coords_list=coords_list,
            )
        )

    text = "\n\n".join(blocks)
    write_text(OUTPUT_FILE_PATH, text)

    print("✅ Wrote:")
    print(f"   - {OUTPUT_FILE_PATH}")


if __name__ == "__main__":
    main()