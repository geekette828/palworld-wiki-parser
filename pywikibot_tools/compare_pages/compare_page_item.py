import os
import sys
import re
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants  # type: ignore
from pywikibot import pagegenerators
from typing import List, Optional, Tuple, Dict
from utils.console_utils import force_utf8_stdout  # type: ignore
from utils.english_text_utils import EnglishText  # type: ignore
from builders.item_page import resolve_item_id_and_title  # type: ignore
from builders.item_infobox import (
    build_item_infobox_model_for_page,
    item_infobox_model_to_params,
)  # type: ignore

from builders.item_recipe import (
    build_item_recipe_model_by_id,
    crafting_recipe_model_to_params,
)  # type: ignore

from utils.compare_utils import (
    is_blank,
    normalize_title,
    normalize_skip_keys,
    find_template_blocks,
    extract_first_template_block,
    replace_span,
    parse_template_params,
    extract_param_value_single_line,
    compare_param_dicts,
    patch_template_params_in_place,
    template_has_meaningful_data,
)

force_utf8_stdout()

compare_output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Compare_Item_Pages.txt")

DRY_RUN = True

CHECK_INFOBOX = True
CHECK_RECIPE = True

TEST_RUN = False
TEST_PAGES = [
"Metal Armor",
]

SKIP_PARAMS = [
    "technology",
    "ammo",
    "capture_power",
    "equip_effect",
    "consumeEffect",
    "code",
]

SKIP_RECIPE_PARAMS = [
    "recipe.workbench",
]


def _write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _extract_recipe_params(template_text: str) -> Dict[str, str]:
    keys = [
        "product",
        "yield",
        "workbench",
        "ingredients",
        "workload",
        "schematic",
        "2_workload",
        "2_ingredients",
        "3_workload",
        "3_ingredients",
        "4_workload",
        "4_ingredients",
        "5_workload",
        "5_ingredients",
    ]
    out: Dict[str, str] = {}
    for k in keys:
        out[k] = extract_param_value_single_line(template_text, k)
    return out


def _select_recipe_block(
    *,
    page_text: str,
    canonical_product: str,
) -> Tuple[Optional[Tuple[str, int, int]], Optional[str]]:
    blocks = find_template_blocks(page_text, "Crafting Recipe")
    if not blocks:
        return None, None

    if len(blocks) == 1:
        return blocks[0], None

    canonical_product = (canonical_product or "").strip()
    if not canonical_product:
        products = [extract_param_value_single_line(b, "product") or "(blank)" for (b, _, _) in blocks]
        return None, f"Ambiguous: multiple Crafting Recipe templates but canonical product is blank. Found: {', '.join(products)}"

    matches: List[Tuple[str, int, int]] = []
    found_products: List[str] = []
    for b, s, e in blocks:
        p = extract_param_value_single_line(b, "product")
        found_products.append(p or "(blank)")
        if p.strip() == canonical_product.strip():
            matches.append((b, s, e))

    if len(matches) == 1:
        return matches[0], None

    if len(matches) > 1:
        return None, f"Ambiguous: multiple Crafting Recipe templates match product '{canonical_product}'."

    return None, f"Ambiguous: multiple Crafting Recipe templates and none match canonical product '{canonical_product}'. Found: {', '.join(found_products)}"


def _compare_and_patch_page(
    *,
    title: str,
    page_text: str,
    item_id: str,
) -> Tuple[str, List[str], List[str]]:
    diffs: List[str] = []
    warnings: List[str] = []

    new_text = page_text

    if CHECK_INFOBOX:
        wiki_block, s, e = extract_first_template_block(new_text, "Item")
        model = build_item_infobox_model_for_page(item_id)

        if not model:
            warnings.append("No canonical infobox could be generated from data.")
        elif wiki_block is None or s is None or e is None:
            warnings.append("No {{Item}} template found on page.")
        else:
            wiki_params = parse_template_params(wiki_block, allow_multiline_keys={"description", "qualities"})
            expected_params = item_infobox_model_to_params(model)

            skip_infobox = normalize_skip_keys(SKIP_PARAMS)

            if is_blank(expected_params.get("subtype")):
                skip_infobox.add("subtype")
                expected_params.pop("subtype", None)

            param_mismatches = compare_param_dicts(
                expected_params,
                wiki_params,
                skip_keys=skip_infobox,
            )

            if param_mismatches:
                diffs.extend(param_mismatches)

                patched_block, _patch_mismatches = patch_template_params_in_place(
                    template_text=wiki_block,
                    expected_params=expected_params,
                    skip_keys=skip_infobox,
                    allow_multiline_keys={"description", "qualities"},
                )

                new_text = replace_span(new_text, s, e, patched_block)

    if CHECK_RECIPE:
        recipe_model = build_item_recipe_model_by_id(item_id)

        if not recipe_model:
            blocks = find_template_blocks(new_text, "Crafting Recipe")

            meaningful_blocks = [
                b
                for (b, _, _) in blocks
                if template_has_meaningful_data(
                    b,
                    ignore_keys={"product"},  # product alone doesn't mean "wiki has recipe info"
                )
            ]

            if meaningful_blocks:
                warnings.append(
                    f"Page has {len(meaningful_blocks)} Crafting Recipe template(s) with wiki-data, "
                    f"but data has no canonical recipe. Skipping recipe edits."
                )
        else:
            canonical_product = (recipe_model.get("product") or "").strip()

            selected, ambiguous_reason = _select_recipe_block(
                page_text=new_text,
                canonical_product=canonical_product,
            )

            if ambiguous_reason:
                warnings.append(ambiguous_reason)
            elif selected is None:
                warnings.append("No {{Crafting Recipe}} template found on page.")
            else:
                wiki_recipe, rs, re_ = selected

                wiki_params = _extract_recipe_params(wiki_recipe)
                expected_params = crafting_recipe_model_to_params(recipe_model)

                skip_recipe_prefixed = normalize_skip_keys(SKIP_RECIPE_PARAMS)

                param_mismatches = compare_param_dicts(
                    expected_params,
                    wiki_params,
                    prefix="recipe.",
                    skip_keys=skip_recipe_prefixed,
                    qty_assume_one_suffixes={"ingredients"},
                )

                if param_mismatches:
                    diffs.extend(param_mismatches)

                    skip_bare: set[str] = set()
                    for k in (SKIP_RECIPE_PARAMS or []):
                        s_k = str(k or "").strip()
                        if not s_k:
                            continue
                        if s_k.lower().startswith("recipe."):
                            s_k = s_k.split(".", 1)[1].strip()
                        skip_bare.add(s_k.casefold())

                    patched_recipe, _patch_mismatches = patch_template_params_in_place(
                        template_text=wiki_recipe,
                        expected_params=expected_params,
                        skip_keys=skip_bare,
                        allow_multiline_keys=set(),
                        add_missing_params=True,   # ✅ this is the key
                    )

                    new_text = replace_span(new_text, rs, re_, patched_recipe)

    return new_text, diffs, warnings


def _page_generator(site: pywikibot.Site):
    template_page = pywikibot.Page(site, "Template:Item")

    for p in template_page.embeddedin(namespaces=[0]):
        try:
            if p.isRedirectPage():
                continue
        except Exception:
            pass

        yield p


def main() -> None:
    site = pywikibot.Site()
    site.login()

    en = EnglishText()

    diffs_out: List[str] = []
    warnings_out: List[str] = []
    changed_pages: List[str] = []

    pages = list(pagegenerators.PreloadingGenerator(_page_generator(site), groupsize=50))

    if TEST_RUN and TEST_PAGES:
        wanted = {t.strip() for t in TEST_PAGES if t.strip()}
        pages = [p for p in pages if normalize_title(p.title()) in wanted]

    total = len(pages)
    print(f"🔍 Found {total} pages embedding Template:Item")

    for idx, page in enumerate(pages, start=1):
        title = page.title()
        try:
            text = page.get()
        except Exception as e:
            warnings_out.append(f"## {title}\nFailed to read page: {e}\n")
            continue

        item_id, _final_title = resolve_item_id_and_title(title, en=en)
        if not item_id:
            warnings_out.append(f"## {title}\nCould not resolve item_id from page title. Skipping.\n")
            continue

        new_text, diffs, warns = _compare_and_patch_page(
            title=title,
            page_text=text,
            item_id=item_id,
        )

        if warns:
            warnings_out.append(f"## {title}\n" + "\n".join([f"- {w}" for w in warns]) + "\n")

        if diffs:
            diffs_out.append(f"- {title}")
            for d in diffs:
                diffs_out.append(f"  {d}")
            diffs_out.append("")
            changed_pages.append(title)

        if not DRY_RUN and diffs:
            if new_text.strip() == text.strip():
                continue

            page.text = new_text
            page.save(summary="Update item infobox/recipe from data", minor=False)
            print(f"📝 Updated: {title} ({idx}/{total})")
        else:
            if idx % 25 == 0 or idx == total:
                print(f"🔄 Scanned {idx}/{total}")

    if DRY_RUN:
        parts: List[str] = []

        parts.append("# Item Page Compare Output\n")
        parts.append(f"DRY_RUN: {DRY_RUN}\n")
        parts.append(f"CHECK_INFOBOX: {CHECK_INFOBOX}\n")
        parts.append(f"CHECK_RECIPE: {CHECK_RECIPE}\n")
        parts.append("")

        parts.append("# Parameter Mismatches\n")
        if diffs_out:
            parts.extend(diffs_out)
        else:
            parts.append("(none)")
        parts.append("")

        parts.append("# Warnings\n")
        if warnings_out:
            parts.extend(warnings_out)
        else:
            parts.append("(none)")
        parts.append("")

        _write_text(compare_output_file, "\n".join(parts).rstrip() + "\n")
        print(f"✅ Wrote diff report: {compare_output_file}")


if __name__ == "__main__":
    main()
