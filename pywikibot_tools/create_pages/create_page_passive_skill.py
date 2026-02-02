import os
import sys
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants
from typing import Dict, List
from pathlib import Path
from builders.passive_skill_infobox import build_all_passive_skill_models, PassiveSkillModel
from export_passive_skill_infoboxes import render_passive_skill_infobox
from utils.console_utils import force_utf8_stdout
force_utf8_stdout()

preview_output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Passive Skill Pages")
missing_pages_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Missing_Passive_Skills.txt")

DRY_RUN = True
OVERWRITE_EXISTING = True

# Only used when DRY_RUN = True
TEST_PAGES = [
    "Celestial Emperor"
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

def first_effect_string(model: PassiveSkillModel) -> str | None:
    effects = model.get("effects", []) or []
    if not effects:
        return None
    e = effects[0]
    label = (e.get("label") or "").strip()
    val = (e.get("value_text") or "").strip()
    if not label or not val:
        return None
    return f"{label}*{val}"

def build_passive_skill_summary_from_effect(effect: str | None) -> str:
    """
    effect format: '<EffectName>*<number>%'
    Example: 'Defense*-20%'
    """

    if not effect or "*" not in effect:
        return "is a passive skill with unique effects that influence a Pal's performance."

    effect_name, value_part = effect.split("*", 1)
    value_part = value_part.replace("%", "").strip()

    try:
        value = float(value_part)
    except ValueError:
        return "is a passive skill with unique effects that influence a Pal's performance."

    key = " ".join(effect_name.lower().split())

    if key.startswith("element boost ") or key.startswith("elementboost_"):
        if key.startswith("element boost "):
            element = effect_name.split(" ", 2)[2].strip()
        else:
            element = effect_name.split("_", 1)[1].strip()

        return (
            f"is a combat-focused passive skill that increases the damage dealt by "
            f"{{{{i|{element}}}}}-element attacks. It is best suited for Pals aligned with that "
            f"element or builds that rely heavily on {element}-type damage, enhancing offensive "
            f"output without affecting other combat stats or non-combat activities."
        )

    if key.startswith("element resist ") or key.startswith("elementresist_"):
        if key.startswith("element resist "):
            element = effect_name.split(" ", 2)[2].strip()
        else:
            element = effect_name.split("_", 1)[1].strip()

        return (
            f"is a defensive passive skill that reduces damage taken from "
            f"{{{{i|{element}}}}}-element attacks, improving survivability against that damage type."
        )

    if key in {"attack", "defense"}:
        if value > 0:
            return (
                "is a combat-oriented passive skill that increases a Pal's core combat stats. "
                "It is best suited for battle-focused roles where maximizing damage output and/or "
                "survivability is important."
            )
        else:
            return (
                "is a combat-oriented passive skill that reduces a Pal's core combat stats. "
                "This skill negatively impacts damage output and/or survivability, making it "
                "poorly suited for combat-focused roles."
            )

    if key == "workspeed":
        if value > 0:
            return (
                "is a productivity-focused passive skill that increases a Pal's efficiency when "
                "performing base tasks, allowing work to be completed more quickly."
            )
        else:
            return (
                "is a productivity-focused passive skill that reduces a Pal's efficiency when "
                "performing base tasks, causing work to be completed more slowly."
            )

    if key == "sanitydecrease":
        if value < 0:
            return (
                "is a sustainability-focused passive skill that reduces how quickly a Pal's "
                "sanity is depleted during extended activity, allowing the Pal to remain active "
                "for longer periods before requiring rest."
            )
        else:
            return (
                "is a sustainability-focused passive skill that increases how quickly a Pal's "
                "sanity is depleted during extended activity, causing the Pal to require rest "
                "more frequently."
            )

    if key == "fullstomachdecrease":
        if value < 0:
            return (
                "is a sustainability-focused passive skill that reduces how quickly a Pal's "
                "hunger is depleted, allowing the Pal to remain fed for longer periods."
            )
        else:
            return (
                "is a sustainability-focused passive skill that increases how quickly a Pal's "
                "hunger is depleted, requiring food more frequently."
            )

    if key == "movementspeed" and value > 0:
        return (
            "is a movement-focused passive skill that increases how quickly a Pal can move "
            "while being ridden, improving travel speed and mounted mobility."
        )

    return "is a passive skill with unique effects that influence a Pal's performance."

def build_page_text(skill_name: str, model: PassiveSkillModel) -> str:
    skill_name = normalize_title(skill_name)

    infobox_wikitext = render_passive_skill_infobox(model)

    page_lines = []
    page_lines.append(infobox_wikitext.strip())
    page_lines.append("")

    effect = first_effect_string(model)
    summary_text = build_passive_skill_summary_from_effect(effect)

    page_lines.append(f"'''{skill_name}''' {summary_text}")
    page_lines.append("")
    page_lines.append(
        "[[Passive Skills]] are permanent traits that modify a Pal's behavior and stats, influencing how effective they are in combat, base work, or other activities. "
        "A Pal may have anywhere from zero to four passive skills at once, and while the same passive cannot appear more than once on a single Pal, different passives "
        "affecting the same stat will stack together, increasing their overall impact. These traits are typically determined when a Pal is obtained or bred, and the "
        "combination of passives a Pal has can dramatically shape its strengths and weaknesses."
    )
    page_lines.append("")
    page_lines.append("==Acquisition==")
    page_lines.append("===Merchants===")
    page_lines.append(
        "Once the player gains access to passive modification services, certain passive skills can be surgically added or removed in exchange for gold coins. "
        "Only a limited selection of passive skills are eligible for modification, with some available by default and others requiring purchase before they can be used."
    )
    page_lines.append("")
    page_lines.append("{{Shops}}")
    page_lines.append("")
    page_lines.append("===Natural Pals===")
    page_lines.append(
        "Some Pals can naturally spawn with specific passive skills. The Pals listed below are known to appear with this passive skill without breeding or modification."
    )
    page_lines.append("")
    page_lines.append("{{Passive Natural Pals}}")
    page_lines.append("")
    page_lines.append("==Related Skills==")
    page_lines.append("===Stat-Related Passives===")
    page_lines.append(
        "These passive skills influence the same stat as this skill and may interact with it depending on their effects."
    )
    page_lines.append("")
    page_lines.append("{{Stat Related Passives}}")
    page_lines.append("")
    page_lines.append("===Opposing Passives===")
    page_lines.append(
        "Some passive skills can interfere with this skill by working in the opposite direction. The passive skills below oppose this skill and may weaken its overall impact."
    )
    page_lines.append("")
    page_lines.append("{{Opposing Passive Skills}}")
    page_lines.append("")
    page_lines.append("==Mechanics==")
    page_lines.append("===System Interactions===")
    page_lines.append(
        "Passive skills may interact with other game systems beyond their direct stat effects. The details below explain how this passive skill behaves when combined with related mechanics or features."
    )
    page_lines.append("<!--* List interactions with game systems-->")
    page_lines.append("")
    page_lines.append("===Limitations===")
    page_lines.append(
        "Passive skills may have restrictions on when or how their effects apply. The limitations listed below describe any known conditions that can prevent this passive skill from functioning as expected."
    )
    page_lines.append("* No known limitations")
    page_lines.append("")
    page_lines.append("<!--==Trivia==")
    page_lines.append("* ")
    page_lines.append("")
    page_lines.append("==Media==")
    page_lines.append("<gallery>")
    page_lines.append("</gallery>")
    page_lines.append("")
    page_lines.append("==History==")
    page_lines.append("* [[0.?.?.?]]")
    page_lines.append("** Introduced.")
    page_lines.append("-->")
    page_lines.append("")
    page_lines.append("{{Navbox Passive Skills}}")
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
    page.save(summary="Create passive skill page from create-plate template.")
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
            print(f"Usage: python create_page_passive_skill.py \"Hooligan\" \"Celestial Emperor\"")
            print(f"Or populate this file with one page title per line: {missing_pages_file}")
            return

    models = build_all_passive_skill_models()
    model_map: Dict[str, PassiveSkillModel] = {normalize_title(m.get("display_name", "")): m for m in models if m.get("display_name")}

    missing = [p for p in pages_to_process if p not in model_map]
    if missing:
        missing_path = os.path.join(preview_output_directory, "missing_model_entries.txt")
        write_text(missing_path, "\n".join(missing) + "\n")
        print(f"🛠️ Missing models written to: {missing_path}")

    site = pywikibot.Site() if not DRY_RUN else None

    for skill_name in pages_to_process:
        model = model_map.get(skill_name)
        if not model:
            print(f"🛠️ No model found for: {skill_name}")
            continue

        page_text = build_page_text(skill_name, model)

        if DRY_RUN:
            write_dry_run_page(skill_name, page_text)
        else:
            create_or_update_page(site, skill_name, page_text)

    if DRY_RUN:
        dir_uri = Path(preview_output_directory).as_uri()
        print(f"✅ DRY_RUN complete. Preview files written to: {dir_uri}")
    else:
        print("✅ Done.")

if __name__ == "__main__":
    main()
