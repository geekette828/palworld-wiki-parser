import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.item_recipe import build_all_item_recipes_export_text

force_utf8_stdout()

output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "item_recipes.txt")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main() -> None:
    print("🔄 Building item recipes export text...")
    text = build_all_item_recipes_export_text()

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    recipe_count = text.count("\n## ")
    print(f"✅ Done. Wrote {recipe_count} recipes.")


if __name__ == "__main__":
    main()
