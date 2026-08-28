import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from typing import Dict, List
from utils.console_utils import force_utf8_stdout
from builders.pal_infobox import build_all_pal_infobox_models, PalInfoboxModel
from builders.pal_partner_skill import build_all_partner_skill_models, PartnerSkillModel

force_utf8_stdout()

output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "pal_partner_skills.txt")


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _format_percent_div5(value: str) -> str:
    if value is None:
        return ""

    s = str(value).strip()
    if s == "":
        return ""

    try:
        n = float(s)
    except ValueError:
        return s

    out = n / 5.0

    if abs(out - round(out)) < 1e-9:
        return f"{int(round(out))}%"

    return f"{out}%".rstrip("0").rstrip(".")

def _format_effect_value(value: str, value_format: str) -> str:
    vf = (value_format or "raw").strip().lower()
    s = str(value or "").strip()
    if s == "":
        return ""

    try:
        n = float(s)
    except ValueError:
        return s

    if vf == "percent_div5":
        out = n / 5.0
        if abs(out - round(out)) < 1e-9:
            return f"{int(round(out))}%"
        return f"{out}%".rstrip("0").rstrip(".")

    if vf == "percent_raw":
        if abs(n - round(n)) < 1e-9:
            return f"{int(round(n))}%"
        return f"{n}%".rstrip("0").rstrip(".")

    return s

def render_partner_skill_block(
    pal_model: PalInfoboxModel,
    partner_model: PartnerSkillModel,
) -> str:
    base_id = (pal_model.get("base_id") or "").strip()
    display_name = (pal_model.get("display_name") or base_id).strip()

    partner_skill_name = (partner_model.get("partner_skill_name") or "").strip()
    partner_skill_desc = (partner_model.get("partner_skill_desc") or "").strip()

    lines: List[str] = []
    lines.append(f"# {display_name} ({base_id})")
    lines.append(f"Partner Skill: {partner_skill_name}")
    lines.append(f"Description: {partner_skill_desc}")

    effect_groups = partner_model.get("effect_groups") or []
    for group in effect_groups:
        effect_group_name = (group.get("effect_group") or "").strip()
        if effect_group_name == "":
            continue

        value_format = (group.get("value_format") or "raw").strip()

        lines.append(f"Effect Group: {effect_group_name}")

        levels: Dict[int, Dict[str, str]] = group.get("levels") or {}
        for lvl in [1, 2, 3, 4, 5]:
            level_row = levels.get(lvl) or {}

            effect_type = (level_row.get("effect_type") or "").strip()
            raw_value = (level_row.get("effect_value") or "").strip()
            target_type = (level_row.get("target_type") or "").strip()

            if effect_type == "" and raw_value == "" and target_type == "":
                continue

            formatted_value = _format_effect_value(raw_value, value_format)

            lines.append(f"Level {lvl}_effect_type: {effect_type}")
            lines.append(f"Level {lvl}_effect_value: {formatted_value}")
            lines.append(f"Level {lvl}_target_type: {target_type}")

    return "\n".join(lines).rstrip() + "\n"


def build_all_partner_skills_text() -> str:
    pals = build_all_pal_infobox_models()

    pal_ids: List[str] = []
    for _, pal_model in pals:
        base_id = (pal_model.get("base_id") or "").strip()
        if base_id:
            pal_ids.append(base_id)

    partner_by_id = build_all_partner_skill_models(pal_ids=pal_ids)

    blocks: List[str] = []
    for _, pal_model in pals:
        base_id = (pal_model.get("base_id") or "").strip()
        if not base_id:
            continue

        partner_model = partner_by_id.get(base_id) or {}
        blocks.append(render_partner_skill_block(pal_model, partner_model))
        blocks.append("\n")

    return "".join(blocks).rstrip() + "\n"


def main() -> None:
    print("🔄 Building partner skill export text...")
    text = build_all_partner_skills_text()

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    line_count = text.count("\n") + (1 if text else 0)
    print(f"✅ Done. Wrote {line_count} lines.")


if __name__ == "__main__":
    main()
