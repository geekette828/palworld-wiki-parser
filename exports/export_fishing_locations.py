import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.fishing_location import (
    build_pal_fishing_locations_text,
    build_pal_fishing_locations_deduped_text,
    build_pal_fishing_locations_wikiformat_text,
)

force_utf8_stdout()

output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Fishing")

output_file_detailed = os.path.join(output_directory, "Pal_Fishing_Locations.txt")
output_file_deduped = os.path.join(output_directory, "Pal_Fishing_Locations_Deduped.txt")
output_file_wikiformat = os.path.join(output_directory, "fishing_wikiformat.txt")

INCLUDE_WEIGHTS = True
INCLUDE_PERCENT = True


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main() -> None:
    detailed = build_pal_fishing_locations_text(
        include_weights=INCLUDE_WEIGHTS,
        include_percent=INCLUDE_PERCENT,
    )
    write_text(output_file_detailed, detailed)
    print(f"Wrote: {output_file_detailed}")

    deduped = build_pal_fishing_locations_deduped_text()
    write_text(output_file_deduped, deduped)
    print(f"Wrote: {output_file_deduped}")

    wikiformat = build_pal_fishing_locations_wikiformat_text()
    write_text(output_file_wikiformat, wikiformat)
    print(f"Wrote: {output_file_wikiformat}")


if __name__ == "__main__":
    main()
