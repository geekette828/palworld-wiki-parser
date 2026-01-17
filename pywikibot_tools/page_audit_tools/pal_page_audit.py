import os
import sys
import json
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from pywikibot import pagegenerators
from utils.console_utils import force_utf8_stdout
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText
from pathlib import Path

force_utf8_stdout()

missing_pages_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Missing_Pals.txt")
unmapped_internal_ids_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Unmapped_Pal_Internal_IDs.txt")

PARAM_INPUT_FILE = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json")

TEMPLATE_NAME = "Pal"


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


def safe_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def build_pal_title_set() -> tuple[set[str], list[str]]:
    """
    Returns:
      - expected Pal page titles (English display names)
      - unmapped internal IDs (when EnglishText has no name mapping)
    """
    rows = load_rows(PARAM_INPUT_FILE)
    en = EnglishText()

    pals: list[str] = []
    unmapped: list[str] = []

    for key, row in rows.items():
        if not isinstance(key, str):
            continue
        if not isinstance(row, dict):
            continue

        # Skip alpha/boss variants (pages are for the base Pal)
        if key.startswith("BOSS_"):
            continue

        zukan_index = safe_int(row.get("ZukanIndex"))
        if zukan_index is None or zukan_index < 0:
            continue

        display_name = normalize_title(en.get_pal_name(key))
        if not display_name:
            unmapped.append(key)
            continue

        pals.append(display_name)

    # Deduplicate case-insensitively, preserving first-seen casing
    seen = set()
    out = set()
    for t in sorted(pals, key=lambda s: s.casefold()):
        f = t.casefold()
        if f in seen:
            continue
        seen.add(f)
        out.add(t)

    unmapped = sorted(set(unmapped), key=lambda s: s.casefold())
    return out, unmapped


def get_template_transclusion_titles(site: pywikibot.Site, template_name: str) -> set[str]:
    template_page = pywikibot.Page(site, f"Template:{template_name}")
    titles: set[str] = set()

    # Pages that include {{Pal}} (template transclusions only)
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

    print("🔍 Building Pal name set from data-mine...")
    data_pal_titles, unmapped = build_pal_title_set()
    data_pal_titles = {normalize_title(n) for n in data_pal_titles}
    print(f"✅ Data-mine Pals: {len(data_pal_titles)}")

    print(f"🔍 Reading pages that transclude {{:{TEMPLATE_NAME}}} on-wiki...")
    existing_titles = get_template_transclusion_titles(site, TEMPLATE_NAME)
    print(f"✅ Pal pages found (template transclusions): {len(existing_titles)}")

    existing_folded = {t.casefold() for t in existing_titles}

    missing = [
        t for t in sorted(data_pal_titles, key=lambda s: s.casefold())
        if t.casefold() not in existing_folded
    ]

    ensure_directory(missing_pages_file)
    with open(missing_pages_file, "w", encoding="utf-8") as f:
        f.write("\n".join(missing).rstrip() + "\n")
    
    ensure_directory(unmapped_internal_ids_file)
    with open(unmapped_internal_ids_file, "w", encoding="utf-8") as f:
        f.write("\n".join(unmapped).rstrip() + "\n")

    print(f"✅ Wrote {len(unmapped)} unmapped internal IDs to: {Path(unmapped_internal_ids_file).as_uri()}")

    file_uri = Path(missing_pages_file).as_uri()
    print(f"✅ Wrote {len(missing)} missing pages to: {file_uri}")


if __name__ == "__main__":
    main()
