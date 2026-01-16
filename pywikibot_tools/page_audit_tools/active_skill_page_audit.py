import os
import sys
import json
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from pywikibot import pagegenerators
from utils.console_utils import force_utf8_stdout
from utils.english_text_utils import EnglishText
from utils.json_datatable_utils import extract_datatable_rows
from pathlib import Path

force_utf8_stdout()

missing_pages_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Missing_Active_Skills.txt")
WAZA_INPUT_FILE = os.path.join(constants.INPUT_DIRECTORY, "Waza", "DT_WazaDataTable.json")

CATEGORY_NAME = "Active Skills"


def normalize_title(s: str) -> str:
    s = str(s or "").strip()
    return " ".join(s.split())


def ensure_directory(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def get_category_titles(site: pywikibot.Site, category_name: str) -> set[str]:
    category = pywikibot.Category(site, f"Category:{category_name}")
    titles: set[str] = set()

    for page in pagegenerators.CategorizedPageGenerator(category, recurse=False):
        titles.add(normalize_title(page.title(with_ns=False)))

    return titles

def load_valid_waza_skill_ids() -> set[str]:
    """
    Only include skills that actually exist in the Waza data table and are not disabled.
    This filters out phantom/alias English text entries.
    """
    with open(WAZA_INPUT_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    rows = extract_datatable_rows(raw, source=os.path.basename(WAZA_INPUT_FILE)) or {}

    valid_ids: set[str] = set()

    for _, row in rows.items():
        if not isinstance(row, dict):
            continue

        if row.get("DisabledData") is True:
            continue

        waza_type = str(row.get("WazaType") or "").strip()
        if waza_type.startswith("EPalWazaID::"):
            valid_ids.add(waza_type.split("::", 1)[1].strip())

    return valid_ids

def load_active_skill_english_names() -> set[str]:
    """
    Build the English skill name set from the English name DT file.
    Active skills are stored under keys like:
      ACTION_SKILL_<id>, COOP_<id>, ACTIVE_<id>
    We prefer ACTION_SKILL_ when duplicates exist.
    """
    en_name_file = constants.EN_SKILL_NAME_FILE
    english = EnglishText()
    valid_ids = load_valid_waza_skill_ids()


    with open(en_name_file, "r", encoding="utf-8") as f:
        raw = json.load(f)

    rows = extract_datatable_rows(raw, source=os.path.basename(en_name_file)) or {}

    names: dict[str, str] = {}

    # Prefer ACTION_SKILL_ over COOP_ over ACTIVE_
    prefixes = ["ACTION_SKILL_", "COOP_", "ACTIVE_"]

    for prefix in prefixes:
        for key in rows.keys():
            if not str(key).startswith(prefix):
                continue

            skill_id = str(key)[len(prefix):].strip()
            if not skill_id:
                continue

            if skill_id not in valid_ids:
                continue

            name = english.get(en_name_file, key)
            name = normalize_title(name)
            if not name:
                continue

            if name.casefold() == "en text":
                continue

            folded = name.casefold()
            if folded not in names:
                names[folded] = name

    return set(names.values())


def main() -> None:
    site = pywikibot.Site()
    site.login()

    print("🔍 Building active skill name set from English data tables...")
    data_skill_titles = {normalize_title(n) for n in load_active_skill_english_names()}
    print(f"✅ Data-mine active skills: {len(data_skill_titles)}")

    print(f"🔍 Reading pages from Category:{CATEGORY_NAME} on-wiki...")
    category_titles = get_category_titles(site, CATEGORY_NAME)
    print(f"✅ Category pages found: {len(category_titles)}")

    category_folded = {t.casefold() for t in category_titles}
    missing = [
        t for t in sorted(data_skill_titles, key=lambda s: s.casefold())
        if t.casefold() not in category_folded
    ]

    ensure_directory(missing_pages_file)
    with open(missing_pages_file, "w", encoding="utf-8") as f:
        f.write("\n".join(missing).rstrip() + "\n")

    file_uri = Path(missing_pages_file).as_uri()
    print(f"✅ Wrote {len(missing)} missing pages to: {file_uri}")


if __name__ == "__main__":
    main()
