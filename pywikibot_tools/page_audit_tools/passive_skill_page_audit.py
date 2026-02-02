import os
import sys
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from pywikibot import pagegenerators
from utils.console_utils import force_utf8_stdout
from pathlib import Path
from builders.passive_skill_infobox import build_all_passive_skill_models
force_utf8_stdout()


missing_pages_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Missing_Passive_Skills.txt")

CATEGORY_NAME = "Passive Skills"

def normalize_title(s: str) -> str:
    s = str(s or "").strip()
    return " ".join(s.split())


def ensure_directory(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def get_category_titles(site: pywikibot.Site, category_name: str) -> set[str]:
    category = pywikibot.Category(site, f"Category:{category_name}")
    titles = set()

    # All pages in the category (default behavior includes subcats/files depending on wiki),
    # but we only record the page titles we actually iterate.
    for page in pagegenerators.CategorizedPageGenerator(category, recurse=False):
        titles.add(normalize_title(page.title(with_ns=False)))

    return titles


def main() -> None:
    site = pywikibot.Site()
    site.login()

    print("🔍 Building passive skill name set from data-mine...")
    models = build_all_passive_skill_models()
    data_skill_titles = {normalize_title(m.get("display_name", "")) for m in models if m.get("display_name")}

    print(f"✅ Data-mine passive skills: {len(data_skill_titles)}")

    print(f"🔍 Reading pages from Category:{CATEGORY_NAME} on-wiki...")
    category_titles = get_category_titles(site, CATEGORY_NAME)
    print(f"✅ Category pages found: {len(category_titles)}")

    # Compare (case-insensitive) but preserve the original-cased data title in output
    category_folded = {t.casefold() for t in category_titles}

    missing = [t for t in sorted(data_skill_titles, key=lambda s: s.casefold()) if t.casefold() not in category_folded]

    ensure_directory(missing_pages_file)
    with open(missing_pages_file, "w", encoding="utf-8") as f:
        f.write("\n".join(missing).rstrip() + "\n")

    file_uri = Path(missing_pages_file).as_uri()
    print(f"✅ Wrote {len(missing)} missing pages to: {file_uri}")

if __name__ == "__main__":
    main()
