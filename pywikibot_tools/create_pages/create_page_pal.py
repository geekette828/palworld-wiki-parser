import os
import sys
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from utils.console_utils import force_utf8_stdout
from utils.english_text_utils import EnglishText

from builders.pal_infobox import load_rows, build_pal_order
from builders.pal_page import build_pal_page_from_files, PalPageOptions

force_utf8_stdout()

preview_output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Pal Pages")
missing_pages_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Missing_Pals.txt")
PARAM_INPUT_FILE = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json",)

DRY_RUN = True
OVERWRITE_EXISTING = True

# Only used when DRY_RUN = True
TEST_PAGES = [
    "Lamball",
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
    page.save(summary="Create Pal page from create-plate template.")
    print(f"✅ Page saved: {title}")


def build_title_to_base_map(rows: dict, en: EnglishText) -> Dict[str, str]:
    """
    Build a case-insensitive map:
      - display name -> base
      - base -> base (so passing internal IDs works too)
    """
    out: Dict[str, str] = {}

    for base in build_pal_order(rows):
        display = en.get_pal_name(base) or base

        out[normalize_title(display).casefold()] = base
        out[normalize_title(base).casefold()] = base

    return out


def resolve_base_and_title(
    user_title: str,
    *,
    title_to_base: Dict[str, str],
    en: EnglishText,
) -> Tuple[Optional[str], str]:
    """
    Returns (base_id, final_page_title)

    - If user_title is a display name: use it as the final title.
    - If user_title is an internal base id: final title becomes the display name.
    """
    raw_title = normalize_title(user_title)
    if not raw_title:
        return None, ""

    base = title_to_base.get(raw_title.casefold())
    if not base:
        return None, raw_title

    # If they passed the internal id, title should be the displayed pal name.
    if raw_title.casefold() == normalize_title(base).casefold():
        final_title = normalize_title(en.get_pal_name(base) or raw_title)
        return base, final_title

    # Otherwise, keep their given display title (normalized)
    return base, raw_title


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
            print("Usage: python create_page_pal.py \"Lamball\" \"Cattiva\"")
            print(f"Or populate this file with one page title per line: {missing_pages_file}")
            return

    rows = load_rows(PARAM_INPUT_FILE, source="DT_PalMonsterParameter")
    en = EnglishText()
    title_to_base = build_title_to_base_map(rows, en)

    site = pywikibot.Site() if not DRY_RUN else None

    missing_base: List[str] = []
    missing_page_text: List[str] = []

    options = PalPageOptions(include_placeholders=True)

    for user_title in pages_to_process:
        base, final_title = resolve_base_and_title(
            user_title,
            title_to_base=title_to_base,
            en=en,
        )

        if not base:
            missing_base.append(user_title)
            continue

        page_text = build_pal_page_from_files(base, options=options).strip()
        if not page_text:
            missing_page_text.append(user_title)
            continue

        page_text = page_text.rstrip() + "\n"

        if DRY_RUN:
            write_dry_run_page(final_title, page_text)
        else:
            if site is None:
                raise RuntimeError("site is None but DRY_RUN is False")
            create_or_update_page(site, final_title, page_text)

    if missing_base:
        missing_path = os.path.join(preview_output_directory, "missing_pal_name_map.txt")
        write_text(missing_path, "\n".join(missing_base) + "\n")
        print(f"🛠️ Missing title->base mappings written to: {missing_path}")

    if missing_page_text:
        missing_path = os.path.join(preview_output_directory, "missing_pal_page_entries.txt")
        write_text(missing_path, "\n".join(missing_page_text) + "\n")
        print(f"🛠️ Missing pal page builder entries written to: {missing_path}")

    if DRY_RUN:
        dir_uri = Path(preview_output_directory).as_uri()
        print(f"✅ DRY_RUN complete. Preview files written to: {dir_uri}")
    else:
        print("✅ Done.")


if __name__ == "__main__":
    main()
