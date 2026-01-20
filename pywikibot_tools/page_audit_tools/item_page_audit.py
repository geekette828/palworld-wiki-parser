import os
import re
import sys
import json
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText
from pywikibot.exceptions import InvalidTitleError
from pathlib import Path

force_utf8_stdout()

# Outputs
missing_pages_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Missing_Items.txt")
other_items_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Missing_Items_Data.txt")

# Inputs
ITEM_INPUT_FILE = os.path.join(constants.INPUT_DIRECTORY, "Item", "DT_ItemDataTable.json")
TEMPLATE_NAME = "Item"


def alt_item_name_ids(item_id: str) -> list[str]:
    """
    Item IDs often have variant tiers that share the same production item name.
    Examples:
      CopperHelmet_2 -> CopperHelmet
      Musket_5 -> Musket
    For audits, these should be considered "mapped" if the base item has an English name.
    """
    item_id = str(item_id or "").strip()
    if not item_id:
        return []

    out = [item_id]

    # Common tier/quality suffix pattern: <Base>_<Number>
    m = re.match(r"^(.*)_(\d+)$", item_id)
    if m:
        base = m.group(1).strip()
        if base:
            out.append(base)

    # Less common: digits with no underscore: <Base><Number>
    m2 = re.match(r"^(.*?)(\d+)$", item_id)
    if m2:
        base2 = m2.group(1).strip()
        num2 = m2.group(2).strip()
        if base2 and num2:
            out.append(f"{base2}_{num2}")
            out.append(base2)

    # De-dupe preserving order
    seen = set()
    deduped = []
    for v in out:
        if v in seen:
            continue
        seen.add(v)
        deduped.append(v)

    return deduped

def sanitize_wiki_title(title: str) -> str:
    """
    Convert characters illegal in MediaWiki titles to acceptable equivalents.
    Currently:
      [ -> (
      ] -> )
    """
    if not title:
        return title

    return title.replace("[", "(").replace("]", ")")

def normalize_title(s: str) -> str:
    s = str(s or "").strip()
    return " ".join(s.split())


def ensure_directory(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def load_rows(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return extract_datatable_rows(raw, source=os.path.basename(path)) or {}

def get_redirect_titles_main_namespace(site: pywikibot.Site) -> set[str]:
    """
    Bulk fetch all redirect page titles in main namespace (ns=0).
    Returns folded (case-insensitive) titles.
    """
    titles: set[str] = set()
    for page in site.allpages(namespace=0, filterredir=True):
        titles.add(normalize_title(page.title(with_ns=False)).casefold())
    return titles

def build_item_title_set() -> tuple[set[str], list[str]]:
    """
    Returns:
      - expected Item page titles (English display names)
      - unmapped internal item IDs (when EnglishText has no name mapping)
    """
    rows = load_rows(ITEM_INPUT_FILE)
    en = EnglishText()

    titles: list[str] = []
    unmapped: list[str] = []

    for item_id, row in rows.items():
        if not isinstance(item_id, str):
            continue
        if not isinstance(row, dict):
            continue

        # Skip illegal/unreleased items
        if row.get("bLegalInGame") is False:
            continue

        display_name = ""
        for candidate_id in alt_item_name_ids(item_id):
            display_name = normalize_title(en.get_item_name(candidate_id))
            if display_name:
                break

        if not display_name:
            unmapped.append(item_id)
            continue

        titles.append(display_name)

    # Deduplicate case-insensitively while preserving first-seen casing
    seen = set()
    out = set()
    for t in sorted(titles, key=lambda s: s.casefold()):
        f = t.casefold()
        if f in seen:
            continue
        seen.add(f)
        out.add(t)

    unmapped = sorted(set(unmapped), key=lambda s: s.casefold())
    return out, unmapped


def build_valid_item_title_folded_set() -> set[str]:
    """
    Folded (case-insensitive) set of valid item display names from the data-mine.
    """
    valid_titles, _ = build_item_title_set()
    return {normalize_title(t).casefold() for t in valid_titles}


def get_template_transclusion_titles(site: pywikibot.Site, template_name: str) -> set[str]:
    template_page = pywikibot.Page(site, f"Template:{template_name}")
    titles: set[str] = set()

    # Pages that include {{Item}} (template transclusions only)
    for page in template_page.getReferences(
        only_template_inclusion=True,
        namespaces=[0],
        content=False,
    ):
        titles.add(normalize_title(page.title(with_ns=False)))

    return titles

def resolve_redirect_target_title(
    site: pywikibot.Site,
    start_title: str,
    max_hops: int = 10,
) -> tuple[str, int, bool]:
    """
    Follow redirects from start_title and return:
      (final_target_title_without_ns, hops, was_redirect)
    If it fails to resolve for any reason, returns the start title.
    """
    page = pywikibot.Page(site, sanitize_wiki_title(start_title))
    if not page.exists():
        return normalize_title(start_title), 0, False

    hops = 0
    was_redirect = False

    while page.exists() and page.isRedirectPage():
        was_redirect = True
        try:
            target = page.getRedirectTarget()
        except Exception:
            break

        hops += 1
        if hops >= max_hops:
            break

        page = target

    return normalize_title(page.title(with_ns=False)), hops, was_redirect


def page_transcludes_template(
    page: pywikibot.Page,
    template_name: str,
) -> bool:
    """
    Checks if a page transcludes Template:<template_name>.
    We keep this simple: look at templates used on the page (namespace 10).
    """
    if not page.exists():
        return False

    try:
        for t in page.templates():
            if normalize_title(t.title(with_ns=False)).casefold() == template_name.casefold():
                return True
    except Exception:
        return False

    return False


def main() -> None:
    site = pywikibot.Site()
    site.login()

    print("🔍 Building Item name set from data-mine...")
    data_item_titles, unmapped = build_item_title_set()
    data_item_titles = {normalize_title(n) for n in data_item_titles}
    print(f"✅ Data-mine Items: {len(data_item_titles)}")

    print(f"🔍 Reading pages that transclude {{:{TEMPLATE_NAME}}} on-wiki...")
    existing_titles = get_template_transclusion_titles(site, TEMPLATE_NAME)
    print(f"✅ Item pages found (template transclusions): {len(existing_titles)}")

    existing_folded = {t.casefold() for t in existing_titles}

    print("🔍 Loading all redirect page titles in main namespace (bulk)...")
    redirect_folded = get_redirect_titles_main_namespace(site)
    print(f"✅ Redirect pages found (ns=0): {len(redirect_folded)}")

    # Candidate missing titles based on "not an Item page"
    missing_initial = [
        t for t in sorted(data_item_titles, key=lambda s: s.casefold())
        if t.casefold() not in existing_folded
    ]
    print(f"🔍 Checking {len(missing_initial)} candidates + {len(unmapped)} unmapped IDs...")

    truly_missing: list[str] = []
    other_lines: list[str] = []

    # Unmapped internal IDs always go to Other_Items.txt
    for item_id in unmapped:
        other_lines.append(f"{item_id} - Unmapped internal ID (no English item name mapping)")

    # Cross off anything that exists as a redirect title (after sanitization)
    for title in missing_initial:
        safe_title = sanitize_wiki_title(title)
        if safe_title.casefold() in redirect_folded:
            if safe_title != title:
                other_lines.append(f"{title} - Redirect exists as '{safe_title}' (sanitized title)")
            else:
                other_lines.append(f"{title} - Redirect page exists")
            continue

        # Still missing after accounting for redirects + Item pages
        truly_missing.append(safe_title)

    # Dedup missing list case-insensitively, preserving first casing
    seen_missing = set()
    dedup_missing: list[str] = []
    for t in truly_missing:
        f = t.casefold()
        if f in seen_missing:
            continue
        seen_missing.add(f)
        dedup_missing.append(t)

    ensure_directory(missing_pages_file)
    with open(missing_pages_file, "w", encoding="utf-8") as f:
        f.write("\n".join(dedup_missing).rstrip() + "\n")

    ensure_directory(other_items_file)
    with open(other_items_file, "w", encoding="utf-8") as f:
        f.write("\n".join(other_lines).rstrip() + "\n")

    print(f"✅ Wrote {len(dedup_missing)} missing pages to: {Path(missing_pages_file).as_uri()}")
    print(f"✅ Wrote {len(other_lines)} other items to: {Path(other_items_file).as_uri()}")

if __name__ == "__main__":
    main()