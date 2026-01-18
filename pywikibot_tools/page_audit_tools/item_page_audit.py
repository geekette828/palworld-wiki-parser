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
from pathlib import Path

force_utf8_stdout()

# Outputs
missing_pages_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Missing_Items.txt")
invalid_pages_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Invalid_Item_Pages.txt")
unmapped_item_ids_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Unmapped_Item_IDs.txt")

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
    data_folded = {t.casefold() for t in data_item_titles}

    missing = [
        t for t in sorted(data_item_titles, key=lambda s: s.casefold())
        if t.casefold() not in existing_folded
    ]

    invalid = [
        t for t in sorted(existing_titles, key=lambda s: s.casefold())
        if t.casefold() not in data_folded
    ]

    ensure_directory(missing_pages_file)
    with open(missing_pages_file, "w", encoding="utf-8") as f:
        f.write("\n".join(missing).rstrip() + "\n")

    ensure_directory(invalid_pages_file)
    with open(invalid_pages_file, "w", encoding="utf-8") as f:
        f.write("\n".join(invalid).rstrip() + "\n")

    ensure_directory(unmapped_item_ids_file)
    with open(unmapped_item_ids_file, "w", encoding="utf-8") as f:
        f.write("\n".join(unmapped).rstrip() + "\n")

    print(f"✅ Wrote {len(unmapped)} unmapped internal IDs to: {Path(unmapped_item_ids_file).as_uri()}")
    print(f"✅ Wrote {len(missing)} missing pages to: {Path(missing_pages_file).as_uri()}")
    print(f"✅ Wrote {len(invalid)} invalid pages to: {Path(invalid_pages_file).as_uri()}")


if __name__ == "__main__":
    main()
