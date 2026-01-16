import os
import sys
import pywikibot
import importlib.util

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import Dict, List, Optional
from pathlib import Path
from utils.console_utils import force_utf8_stdout

force_utf8_stdout()

preview_output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Active Skill Pages")
missing_pages_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Missing_Active_Skills.txt")

DRY_RUN = False
OVERWRITE_EXISTING = True

# Only used when DRY_RUN = True
TEST_PAGES = [
    "Aegis Charge"
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


def extract_element_from_infobox(infobox_wikitext: str) -> Optional[str]:
    for line in infobox_wikitext.splitlines():
        line = line.strip()
        if line.startswith("|element"):
            _, value = line.split("=", 1)
            value = value.strip()
            return value or None
    return None


def load_active_skill_infobox_module():
    try:
        from format_tools import active_skill_infobox as mod  # type: ignore
        return mod
    except Exception:
        script_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "format_tools", "active_skill_infobox.py")
        )
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Could not find active_skill_infobox.py at: {script_path}")

        spec = importlib.util.spec_from_file_location("active_skill_infobox", script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module spec for: {script_path}")

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


active_skill_infobox = load_active_skill_infobox_module()


def build_infobox_for_skill(skill_name: str) -> str:
    skill_name = normalize_title(skill_name)
    return active_skill_infobox.build_active_skill_infobox(skill_name)


def build_page_text(skill_name: str, infobox_wikitext: str) -> str:
    skill_name = normalize_title(skill_name)
    element = extract_element_from_infobox(infobox_wikitext) or ""

    page_lines: List[str] = []
    page_lines.append(infobox_wikitext.strip())
    page_lines.append("")

    if element:
        page_lines.append(
            f"'''{skill_name}''' is a {{{{i|{element}}}}}-[[Elements|elemental]] [[Skills#Active Skills|Active Skill]]."
        )
    else:
        page_lines.append(
            f"'''{skill_name}''' is an [[Skills#Active Skills|Active Skill]]."
        )

    page_lines.append("")
    page_lines.append("<!--==Useage==")
    page_lines.append("Any notes on how it is used or specific cirmstances go here.")
    page_lines.append("-->")
    page_lines.append("==Learned By==")
    page_lines.append("Some Active Skills are learned naturally by certain [[Pals]] as they level up.")
    page_lines.append("{{Active Skills Query")
    page_lines.append(f"|learnedskill = {skill_name}")
    page_lines.append("|hide = Description; Element; CT; Power")
    page_lines.append("|show = Pal; Level  }}")
    page_lines.append("")
    page_lines.append("<!--==Media==")
    page_lines.append("<gallery>")
    page_lines.append("FileName.png|File Description")
    page_lines.append("</gallery>")
    page_lines.append("")
    page_lines.append("==Trivia==")
    page_lines.append("*")
    page_lines.append("-->")
    page_lines.append("==History==")
    page_lines.append("* [[?.?.?]]")
    page_lines.append("** Introduced.")
    page_lines.append("")
    page_lines.append("")
    page_lines.append("{{Navbox Active Skills}}")
    page_lines.append("")

    return "\n".join(page_lines)


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
    page.save(summary="Create active skill page from create-plate template.")
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
            print("Usage: python create_page_active_skill.py \"Acid Rain\" \"Fire Tackle\"")
            print(f"Or populate this file with one page title per line: {missing_pages_file}")
            return

    site = pywikibot.Site() if not DRY_RUN else None

    missing_infobox: List[str] = []
    for skill_name in pages_to_process:
        infobox = build_infobox_for_skill(skill_name)

        # Remove the markdown header (## Skill Name) – only used in mass-infobox output
        if infobox.startswith("##"):
            infobox = infobox.split("\n", 1)[1]
            infobox = infobox.lstrip()

        if not infobox:
            missing_infobox.append(skill_name)
            continue

        page_text = build_page_text(skill_name, infobox)

        if DRY_RUN:
            write_dry_run_page(skill_name, page_text)
        else:
            create_or_update_page(site, skill_name, page_text)

    if missing_infobox:
        missing_path = os.path.join(preview_output_directory, "missing_infobox_entries.txt")
        write_text(missing_path, "\n".join(missing_infobox) + "\n")
        print(f"🛠️ Missing infobox entries written to: {missing_path}")

    if DRY_RUN:
        dir_uri = Path(preview_output_directory).as_uri()
        print(f"✅ DRY_RUN complete. Preview files written to: {dir_uri}")
    else:
        print("✅ Done.")


if __name__ == "__main__":
    main()
