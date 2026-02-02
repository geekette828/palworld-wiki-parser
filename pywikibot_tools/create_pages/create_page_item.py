import os
import sys
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from typing import List
from utils.console_utils import force_utf8_stdout
from builders.item_page import build_item_page_from_name_or_id, ItemPageOptions

force_utf8_stdout()

preview_output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Item Pages")
missing_pages_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Missing_Items.txt")

DRY_RUN = True
OVERWRITE_EXISTING = True

TEST_PAGES = [
    "Core Eject Shotgun", "Cold Resistant Plasteel Armor", "Dazzi Hat"
]


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def normalize_title(s: str) -> str:
    s = str(s or "").strip()
    return " ".join(s.split())


def read_pages_list_file(path: str) -> List[str]:
    if not os.path.exists(path):
        print(f"🛠️ Missing pages file not found: {path}")
        return []

    raw = read_text(path)
    out: List[str] = []

    for line in raw.splitlines():
        line = normalize_title(line)
        if not line:
            continue
        if line.startswith("#"):
            continue
        out.append(line)

    seen = set()
    deduped: List[str] = []
    for title in out:
        if title in seen:
            continue
        seen.add(title)
        deduped.append(title)

    return deduped


def write_dry_run_page(title: str, text: str) -> None:
    safe_title = title.replace("/", "_")
    output_path = os.path.join(preview_output_directory, f"{safe_title}.txt")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"📝 DRY_RUN page written: {output_path}")


def create_or_update_page(site: pywikibot.Site, title: str, text: str) -> None:
    title = normalize_title(title)

    if DRY_RUN:
        write_dry_run_page(title, text)
        return

    page = pywikibot.Page(site, title)

    if page.exists() and not OVERWRITE_EXISTING:
        print(f"🛠️ Page exists, skipping (OVERWRITE_EXISTING=False): {title}")
        return

    page.text = text
    page.save(summary="Create Item page from create-page template.")
    print(f"✅ Page saved: {title}")


def main() -> None:
    cli_pages = [normalize_title(a) for a in sys.argv[1:] if normalize_title(a)]

    pages_from_file: List[str] = []
    if not cli_pages:
        pages_from_file = read_pages_list_file(missing_pages_file)

    if DRY_RUN:
        if TEST_PAGES:
            pages_to_process = [normalize_title(p) for p in TEST_PAGES if normalize_title(p)]
        else:
            pages_to_process = pages_from_file

        if not pages_to_process:
            print("DRY_RUN=True but no pages were provided (TEST_PAGES is empty and file had no entries).")
            return
    else:
        pages_to_process = cli_pages if cli_pages else pages_from_file
        if not pages_to_process:
            print("Usage: python create_page_item.py \"Baked Berries\" \"Pal Sphere\"")
            print(f"Or populate this file with one page title per line: {missing_pages_file}")
            return

    site = pywikibot.Site() if not DRY_RUN else None

    missing_item_ids_or_names: List[str] = []
    missing_page_text: List[str] = []

    options = ItemPageOptions(include_placeholders=True)

    for user_title in pages_to_process:
        final_title, page_text = build_item_page_from_name_or_id(user_title, options=options)

        if not final_title:
            missing_item_ids_or_names.append(user_title)
            continue

        if not page_text or not page_text.strip():
            missing_page_text.append(user_title)
            continue

        page_text = page_text.rstrip() + "\n"

        if DRY_RUN:
            write_dry_run_page(final_title, page_text)
        else:
            if site is None:
                raise RuntimeError("site is None but DRY_RUN is False")
            create_or_update_page(site, final_title, page_text)

    if missing_item_ids_or_names:
        missing_path = os.path.join(preview_output_directory, "missing_item_name_map.txt")
        write_text(missing_path, "\n".join(missing_item_ids_or_names) + "\n")
        print(f"🛠️ Missing name->id mappings written to: {missing_path}")

    if missing_page_text:
        missing_path = os.path.join(preview_output_directory, "missing_page_text.txt")
        write_text(missing_path, "\n".join(missing_page_text) + "\n")
        print(f"🛠️ Items with missing page text written to: {missing_path}")


if __name__ == "__main__":
    main()
