import os
import sys
import re
import difflib
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from config import constants  # type: ignore
from pywikibot import pagegenerators
from utils.console_utils import force_utf8_stdout  # type: ignore
from utils.english_text_utils import EnglishText  # type: ignore
from builders.item_page import resolve_item_id_and_title  # type: ignore
from builders.item_infobox import (
    build_item_infobox_model_for_page,
    item_infobox_model_to_params,
    render_item_infobox,
)  # type: ignore

from builders.item_recipe import (
    build_item_recipe_model_by_id,
    crafting_recipe_model_to_params,
    render_crafting_recipe,
)  # type: ignore

from typing import List, Optional, Tuple, Dict
force_utf8_stdout()


compare_output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Compare_Item_Pages.txt")

DRY_RUN = True
OVERWRITE_EXISTING = True

CHECK_INFOBOX = True
CHECK_RECIPE = True

TEST_RUN = False
TEST_PAGES = [
    "Milk",
]

# Parameters to skip during comparison.
# Use the wiki param names as they appear in the template.
SKIP_PARAMS = [
    "technology",
    "ammo",
    "capture_power",
]

SKIP_RECIPE_PARAMS = [
    "recipe.workbench",
    # "recipe.ingredients",
]

_TEMPLATE_NAME_RE_CACHE: Dict[str, re.Pattern] = {}


def _is_blank(v: Optional[str]) -> bool:
    return v is None or str(v).strip() == ""


def _write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _normalize_title(s: str) -> str:
    s = str(s or "").strip()
    return " ".join(s.split())

def _normalize_skip_keys(keys: List[str]) -> set[str]:
    out: set[str] = set()
    for k in (keys or []):
        s = str(k or "").strip()
        if not s:
            continue
        out.add(s.casefold())
    return out

def _get_template_name_re(template_name: str) -> re.Pattern:
    key = template_name.strip().casefold()
    if key in _TEMPLATE_NAME_RE_CACHE:
        return _TEMPLATE_NAME_RE_CACHE[key]
    pat = re.compile(r"\{\{\s*" + re.escape(template_name.strip()) + r"\b", re.IGNORECASE)
    _TEMPLATE_NAME_RE_CACHE[key] = pat
    return pat

def _extract_param_block(template_text: str, key: str) -> str:
    """
    Returns the exact "|key = ..." block from template_text.
    Supports multiline values (captures until next "|other =" or "}}").
    Returns "" if not found.
    """
    if _is_blank(template_text):
        return ""

    text = template_text.replace("\r\n", "\n").replace("\r", "\n")

    pat = re.compile(
        r"(?ims)^[ \t]*\|\s*"
        + re.escape(key)
        + r"\s*=\s*.*?(?=^\s*\|\s*[^=\n|]+?\s*=|^\s*\}\}\s*$)",
    )
    m = pat.search(text)
    return (m.group(0) or "").rstrip() if m else ""


def _replace_param_block(template_text: str, key: str, new_block: str) -> str:
    """
    Replaces the "|key = ..." block in template_text with new_block.
    If key is not present, returns template_text unchanged.
    """
    if _is_blank(template_text) or _is_blank(new_block):
        return template_text

    text = template_text.replace("\r\n", "\n").replace("\r", "\n")

    pat = re.compile(
        r"(?ims)^[ \t]*\|\s*"
        + re.escape(key)
        + r"\s*=\s*.*?(?=^\s*\|\s*[^=\n|]+?\s*=|^\s*\}\}\s*$)",
    )

    if not pat.search(text):
        return template_text

    replaced = pat.sub(new_block.rstrip(), text, count=1)
    return replaced


def _preserve_skipped_params(
    *,
    canonical_block: str,
    wiki_block: str,
    skip_param_names: List[str],
) -> str:
    """
    For each param name in skip_param_names, if wiki has it, copy the wiki param block
    into the canonical block so patching won't overwrite user-maintained values.
    """
    out = canonical_block
    for key in skip_param_names:
        k = str(key or "").strip()
        if not k:
            continue

        wiki_k_block = _extract_param_block(wiki_block, k)
        if not wiki_k_block:
            continue

        out = _replace_param_block(out, k, wiki_k_block)

    return out


def _find_template_blocks(text: str, template_name: str) -> List[Tuple[str, int, int]]:
    """
    Returns list of (block_text, start_index, end_index) for each template block.
    This is a simple brace counter and assumes templates are well-formed.
    """
    out: List[Tuple[str, int, int]] = []
    if _is_blank(text):
        return out

    name_re = _get_template_name_re(template_name)
    for m in name_re.finditer(text):
        start = m.start()
        i = start
        depth = 0

        while i < len(text) - 1:
            two = text[i : i + 2]
            if two == "{{":
                depth += 1
                i += 2
                continue
            if two == "}}":
                depth -= 1
                i += 2
                if depth == 0:
                    end = i
                    out.append((text[start:end], start, end))
                    break
                continue
            i += 1

    return out

def _strip_trailing_wiki_comment(s: str) -> str:
    # Remove inline <!-- ... --> noise from single-line params
    return re.sub(r"\s*<!--.*?-->\s*$", "", s or "", flags=re.DOTALL).strip()


def _parse_template_params(template_text: str, *, allow_multiline_keys: Optional[set[str]] = None) -> Dict[str, str]:
    """
    Parse a template block into {param_name: value}.

    By default, values are treated as single-line and cut at the first newline.
    Only keys in allow_multiline_keys retain newlines.
    """
    params: Dict[str, str] = {}
    if _is_blank(template_text):
        return params

    allow_multiline_keys = allow_multiline_keys or set()

    text = template_text.replace("\r\n", "\n").replace("\r", "\n")

    pattern = re.compile(
        r"\|\s*(?P<key>[^=\n|]+?)\s*=\s*(?P<val>.*?)(?=\n\|\s*[^=\n|]+?\s*=|\n\}\}\s*$)",
        re.IGNORECASE | re.DOTALL,
    )

    for m in pattern.finditer(text):
        key_raw = (m.group("key") or "").strip()
        val_raw = (m.group("val") or "").strip()

        if not key_raw:
            continue

        key_norm = key_raw.casefold()

        if key_norm not in {k.casefold() for k in allow_multiline_keys}:
            # Single-line param: only take the first line, strip trailing comments
            first_line = val_raw.split("\n", 1)[0].strip()
            params[key_raw] = _strip_trailing_wiki_comment(first_line)
        else:
            # Multiline param: preserve, but still trim
            params[key_raw] = val_raw.strip()

    return params

def _extract_first_template_block(text: str, template_name: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    blocks = _find_template_blocks(text, template_name)
    if not blocks:
        return None, None, None
    b, s, e = blocks[0]
    return b, s, e

def _extract_recipe_params(template_text: str) -> Dict[str, str]:
    keys = [
        "product", "yield", "workbench", "ingredients", "workload", "schematic",
        "2_workload", "2_ingredients",
        "3_workload", "3_ingredients",
        "4_workload", "4_ingredients",
        "5_workload", "5_ingredients",
    ]
    out: Dict[str, str] = {}
    for k in keys:
        out[k] = _extract_param_value(template_text, k)
    return out

def _replace_span(text: str, start: int, end: int, replacement: str) -> str:
    return text[:start] + replacement + text[end:]


def _normalize_for_compare(s: str) -> str:
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    s = s.strip() + "\n"
    return s

_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")

def _strip_wikilinks(s: str) -> str:
    """
    [[Target]] -> Target
    [[Target|Label]] -> Label
    """
    def repl(m: re.Match) -> str:
        target = (m.group(1) or "").strip()
        label = (m.group(2) or "").strip()
        return label if label else target

    return _WIKILINK_RE.sub(repl, s or "")

def _normalize_param_value_for_compare(v: str) -> str:
    # Normalize line endings
    v = (v or "").replace("\r\n", "\n").replace("\r", "\n")

    # Ignore wiki link markup differences (mainly for description, but safe globally)
    v = _strip_wikilinks(v)

    # Ignore thousands separators in numbers: 1,200 == 1200
    v = re.sub(r"(?<=\d),(?=\d)", "", v)

    # Collapse whitespace/newlines
    v = re.sub(r"\s+", " ", v).strip()
    return v


def _compare_param_dicts(
    expected: Dict[str, str],
    found: Dict[str, str],
    *,
    prefix: str = "",
    skip_keys: Optional[set[str]] = None,
) -> List[str]:
    mismatches: List[str] = []
    keys = set(expected.keys()) | set(found.keys())

    skip_keys = skip_keys or set()

    for key in sorted(keys, key=lambda x: x.casefold()):
        label = f"{prefix}{key}" if prefix else key

        # Skip if listed
        if label.casefold() in skip_keys or key.casefold() in skip_keys:
            continue

        exp_raw = (expected.get(key, "") or "")
        got_raw = (found.get(key, "") or "")

        exp = _normalize_param_value_for_compare(exp_raw)
        got = _normalize_param_value_for_compare(got_raw)

        if exp == "" and got == "":
            continue

        if exp != got:
            mismatches.append(f"- {label} Expected {repr(exp)} - Found {repr(got)}")

    return mismatches

def _unified_diff(*, title: str, old: str, new: str, label: str) -> str:
    old_lines = _normalize_for_compare(old).splitlines(keepends=True)
    new_lines = _normalize_for_compare(new).splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"{title} ({label}) - wiki",
        tofile=f"{title} ({label}) - data",
        lineterm="",
    )
    return "\n".join(diff).strip()


def _extract_param_value(template_text: str, param_name: str) -> str:
    """
    Single-line param extract for well-formed templates.
    - Only reads the value on the same line as `|param =`
    - Does not consume following lines or `}}`
    """
    if _is_blank(template_text):
        return ""

    text = template_text.replace("\r\n", "\n").replace("\r", "\n")

    # Match "| param = value" but only capture to end-of-line (not across newlines)
    pat = re.compile(
        r"^[ \t]*\|\s*" + re.escape(param_name) + r"\s*=\s*([^\n]*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    m = pat.search(text)
    if not m:
        return ""

    val = (m.group(1) or "").strip()

    # Strip trailing inline comments
    val = re.sub(r"\s*<!--.*?-->\s*$", "", val).strip()

    return val


def _select_recipe_block(
    *,
    page_text: str,
    canonical_product: str,
) -> Tuple[Optional[Tuple[str, int, int]], Optional[str]]:
    """
    Returns (selected_block, reason_if_ambiguous).

    Selection priority:
    1) Exact match on |product = value
    2) If only one recipe template exists, use it
    3) If multiple exist and none match, return ambiguous reason (no updates)
    """
    blocks = _find_template_blocks(page_text, "Crafting Recipe")
    if not blocks:
        return None, None

    if len(blocks) == 1:
        return blocks[0], None

    canonical_product = (canonical_product or "").strip()
    if not canonical_product:
        products = [
            _extract_param_value(b, "product") or "(blank)"
            for (b, _, _) in blocks
        ]
        return None, f"Ambiguous: multiple Crafting Recipe templates but canonical product is blank. Found: {', '.join(products)}"

    matches: List[Tuple[str, int, int]] = []
    found_products: List[str] = []
    for b, s, e in blocks:
        p = _extract_param_value(b, "product")
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
    """
    Returns (new_page_text, diffs, warnings)
    """
    diffs: List[str] = []
    warnings: List[str] = []

    new_text = page_text

    if CHECK_INFOBOX:
        wiki_block, s, e = _extract_first_template_block(new_text, "Item")
        model = build_item_infobox_model_for_page(item_id)

        if not model:
            warnings.append("No canonical infobox could be generated from data.")
        elif wiki_block is None or s is None or e is None:
            warnings.append("No {{Item}} template found on page.")
        else:
            # Parse wiki params from the page
            wiki_params = _parse_template_params(wiki_block, allow_multiline_keys={"description", "qualities"})

            # Expected params come from the model mapping (not from rendered template text)
            expected_params = item_infobox_model_to_params(model)

            skip_infobox = _normalize_skip_keys(SKIP_PARAMS)
            param_mismatches = _compare_param_dicts(
                expected_params,
                wiki_params,
                skip_keys=skip_infobox,
            )
            if param_mismatches:
                diffs.extend(param_mismatches)

                # Only render when patching
                canonical_block = render_item_infobox(model, include_heading=False).rstrip()

                # Preserve skipped infobox params when patching so we don't overwrite them.
                skip_infobox_names = [k for k in (SKIP_PARAMS or []) if k and not str(k).strip().startswith("recipe.")]
                canonical_block = _preserve_skipped_params(
                    canonical_block=canonical_block,
                    wiki_block=wiki_block,
                    skip_param_names=skip_infobox_names,
                )

                new_text = _replace_span(new_text, s, e, canonical_block)


    if CHECK_RECIPE:
        recipe_model = build_item_recipe_model_by_id(item_id)
        canonical_recipe = render_crafting_recipe(recipe_model).strip() if recipe_model else ""

        if _is_blank(canonical_recipe):
            blocks = _find_template_blocks(new_text, "Crafting Recipe")
            if blocks:
                warnings.append(f"Page has {len(blocks)} Crafting Recipe template(s), but data has no canonical recipe. Skipping recipe edits.")
        else:
            canonical_product = ""
            if recipe_model:
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

                # Wiki params from page (single-line extraction)
                wiki_params = _extract_recipe_params(wiki_recipe)

                # Expected params from model mapping (not from rendered text)
                expected_params: Dict[str, str] = {}
                if recipe_model:
                    expected_params = crafting_recipe_model_to_params(recipe_model)

                skip_recipe = _normalize_skip_keys(SKIP_RECIPE_PARAMS)
                param_mismatches = _compare_param_dicts(
                    expected_params,
                    wiki_params,
                    prefix="recipe.",
                    skip_keys=skip_recipe,
                )
                if param_mismatches:
                    diffs.extend(param_mismatches)
                    canonical_recipe_patched = canonical_recipe

                    # Preserve skipped recipe params when patching
                    skip_recipe_names = []
                    for k in (SKIP_RECIPE_PARAMS or []):
                        s = str(k or "").strip()
                        if not s:
                            continue
                        if s.lower().startswith("recipe."):
                            s = s.split(".", 1)[1].strip()
                        skip_recipe_names.append(s)

                    canonical_recipe_patched = _preserve_skipped_params(
                        canonical_block=canonical_recipe_patched,
                        wiki_block=wiki_recipe,
                        skip_param_names=skip_recipe_names,
                    )

                    new_text = _replace_span(new_text, rs, re_, canonical_recipe_patched)


    return new_text, diffs, warnings


def _page_generator(site: pywikibot.Site):
    template_page = pywikibot.Page(site, "Template:Item")

    for p in template_page.embeddedin(namespaces=[0]):
        # Some pywikibot versions don't support filterredir/filter_redirect.
        # Filter redirects manually so we don't process redirect pages.
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
        pages = [p for p in pages if _normalize_title(p.title()) in wanted]

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
