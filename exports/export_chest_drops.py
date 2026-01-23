import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.chest_drop import build_all_chest_drop_exports

force_utf8_stdout()

output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> None:
    print("🔄 Building chest drop exports...")
    exports = build_all_chest_drop_exports()

    wrote = 0
    for filename, text in exports.items():
        output_path = os.path.join(output_directory, filename)
        print(f"🔄 Writing output file: {output_path}")
        write_text(output_path, text or "")
        wrote += 1

    print(f"✅ Done. Wrote {wrote} export file(s).")


if __name__ == "__main__":
    main()
