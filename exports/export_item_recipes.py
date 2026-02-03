import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import List
from utils.console_utils import force_utf8_stdout
from builders.item_recipe import build_all_item_recipe_models, CraftingRecipeModel
force_utf8_stdout()

#Paths
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "item_recipes.txt")



def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def render_crafting_recipe(model: CraftingRecipeModel) -> str:
    if not model:
        return ""

    lines: List[str] = []
    lines.append("{{Crafting Recipe")
    lines.append(f"|product = {model.get('product', '')}")
    lines.append(f"|yield = {model.get('yield_count', '')}")
    lines.append(f"|workbench = {model.get('workbench', '')}")
    lines.append(f"|ingredients = {model.get('ingredients', '')}")
    lines.append(f"|workload = {model.get('workload', '')}")

    variants = model.get("variants") or {}
    if variants:
        lines.append(f"|schematic = {model.get('schematic', '')}")
        lines.append("")

        first = True
        for n in (2, 3, 4, 5):
            v = variants.get(n)
            if not v:
                continue

            if not first:
                lines.append("")
            first = False

            lines.append(f"|{n}_workload = {v.get('workload', '')}")
            lines.append(f"|{n}_ingredients = {v.get('ingredients', '')}")

    lines.append("}}")
    return "\n".join(lines).rstrip() + "\n"


def build_all_item_recipes_export_text(*, include_headers: bool = True) -> str:
    entries = build_all_item_recipe_models()

    blocks: List[str] = []
    for entry in entries:
        model = entry.get("model")
        product_id = (entry.get("product_id") or "").strip()
        display_name = (entry.get("display_name") or "").strip()

        if not model or not product_id:
            continue

        recipe_text = render_crafting_recipe(model).rstrip()
        if not recipe_text:
            continue

        if include_headers:
            header = f"## {display_name} ({product_id})"
            blocks.append(f"{header}\n{recipe_text}")
        else:
            blocks.append(recipe_text)

    return ("\n\n".join(blocks).rstrip() + "\n") if blocks else ""


def main() -> None:
    print("🔄 Building item recipes export text...")
    text = build_all_item_recipes_export_text(include_headers=True)

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    recipe_count = text.count("\n## ")
    print(f"✅ Done. Wrote {recipe_count} recipes.")


if __name__ == "__main__":
    main()
