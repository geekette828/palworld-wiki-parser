import os
import re
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from pathlib import Path
from config.name_map import ELEMENT_NAME_MAP
from utils.english_text_utils import clean_english_text
from utils.console_utils import force_utf8_stdout

force_utf8_stdout()

# Paths
param_input_file = os.path.join(constants.INPUT_DIRECTORY, "PassiveSkill", "DT_PassiveSkill_Main.json")
en_name_file = constants.EN_SKILL_NAME_FILE
en_description_file = constants.EN_SKILL_DESC_FILE
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "passive_skill_infobox.txt")


def normalize_title(s: str) -> str:
    s = str(s or "").strip()
    return " ".join(s.split())


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_directory(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def extract_localized_text(entry) -> str:
    if entry is None:
        return ""

    if isinstance(entry, str):
        return entry.strip()

    if isinstance(entry, dict):
        text_data = entry.get("TextData")
        if isinstance(text_data, dict):
            s = text_data.get("LocalizedString") or text_data.get("SourceString") or ""
            return str(s).strip()

        s = entry.get("LocalizedString") or entry.get("SourceString") or ""
        return str(s).strip()

    return ""


def extract_datatable_rows(data, *, source: str = "") -> dict:
    if isinstance(data, list):
        dt_obj = None
        for entry in data:
            if isinstance(entry, dict) and isinstance(entry.get("Rows"), dict):
                dt_obj = entry
                break
        if not isinstance(dt_obj, dict):
            raise ValueError(f"{source} JSON list did not contain a DataTable object with 'Rows'")
        data = dt_obj

    if not isinstance(data, dict):
        raise ValueError(f"{source} JSON must be an object or list containing a DataTable object")

    rows = data.get("Rows")
    if not isinstance(rows, dict):
        keys = ", ".join(list(data.keys())[:25])
        raise ValueError(f"{source} JSON missing 'Rows'. Top-level keys: {keys}")

    return rows


def load_text_table(path: str) -> dict:
    raw = load_json(path)
    rows = extract_datatable_rows(raw, source=os.path.basename(path))

    out = {}
    for k, v in rows.items():
        out[str(k)] = extract_localized_text(v)

    return out


def enum_leaf(v: str) -> str:
    v = str(v or "")
    if "::" in v:
        return v.split("::")[-1]
    return v


def is_placeholder_name(s: str) -> bool:
    s = str(s or "").strip()
    return s == "" or s.lower() == "en text"


def is_displayable_passive(row_id: str, row: dict, *, english_name: str) -> bool:
    category_leaf = enum_leaf(row.get("Category", ""))
    if category_leaf == "SortNotDisplayable":
        return False

    if is_placeholder_name(english_name):
        return False

    rid = str(row_id or "")
    if rid.lower().startswith("test"):
        return False

    return True


def humanize_effect_type(effect_type_leaf: str) -> str:
    effect_type_leaf = str(effect_type_leaf or "").strip()
    if effect_type_leaf == "":
        return ""

    mapping = {
        "ShotAttack": "Attack",
        "MeleeAttack": "Melee Attack",
        "Defense": "Defense",
        "MaxHP": "Max HP",
        "CraftSpeed": "Work Speed",
        "WorkSpeed": "Work Speed",
        "MoveSpeed": "Movement Speed",
        "Stamina": "Stamina",
        "Hunger": "Hunger",
        "SAN": "Sanity",
        "CoolTime": "Cooldown",
        "PalCaptureRate": "Capture Rate",
        "ExpRate": "EXP",
        "Weight": "Weight",
        "GainItemDrop": "Item Drop",
    }

    if effect_type_leaf.startswith("ElementBoost_"):
        raw_element = effect_type_leaf.split("_", 1)[1].strip()
        element = ELEMENT_NAME_MAP.get(raw_element, raw_element)
        return f"Element Boost {element}"

    if effect_type_leaf.startswith("ElementResist_"):
        raw_element = effect_type_leaf.split("_", 1)[1].strip()
        element = ELEMENT_NAME_MAP.get(raw_element, raw_element)
        return f"Element Resist {element}"

    if effect_type_leaf in mapping:
        return mapping[effect_type_leaf]

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", effect_type_leaf)
    spaced = spaced.replace("_", " ").strip()
    return spaced


def format_effect_value(v) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return ""

    if abs(n - round(n)) < 1e-9:
        n_str = str(int(round(n)))
    else:
        n_str = str(n).rstrip("0").rstrip(".")
    return f"{n_str}%"


def get_effect_slots(passive_row: dict) -> list:
    slots = []
    indices = []

    for k in passive_row.keys():
        m = re.match(r"^EffectType(\d+)$", str(k))
        if m:
            indices.append(int(m.group(1)))

    for i in sorted(set(indices)):
        effect_type = passive_row.get(f"EffectType{i}")
        effect_value = passive_row.get(f"EffectValue{i}")
        target_type = passive_row.get(f"TargetType{i}")

        effect_type_leaf = enum_leaf(effect_type)

        if effect_type_leaf.lower() == "no":
            continue

        try:
            n = float(effect_value)
        except (TypeError, ValueError):
            continue

        if abs(n) < 1e-12:
            continue

        slots.append(
            {
                "index": i,
                "effect_type_leaf": effect_type_leaf,
                "effect_label": humanize_effect_type(effect_type_leaf),
                "effect_value_raw": n,
                "effect_value_text": format_effect_value(effect_value),
                "target_type_leaf": enum_leaf(target_type),
            }
        )

    return slots


def build_description_from_effects(effect_slots: list) -> str:
    if not effect_slots:
        return ""

    parts = []
    for e in effect_slots:
        label = e["effect_label"]
        val = e["effect_value_text"]

        if label and val:
            parts.append(f"{label} {val}")

    return "\n".join(parts)


def escape_pipe(v: str) -> str:
    return str(v or "").replace("|", "{{!}}")


def is_none_text(v) -> bool:
    s = str(v or "").strip()
    return s == "" or s.lower() == "none"


def first_text(table: dict, keys: list) -> str:
    for k in keys:
        if is_none_text(k):
            continue
        s = table.get(str(k), "")
        if s:
            return str(s).strip()
    return ""


def build_infobox_wikitext(*, title: str, description: str, rank, effects: str) -> str:
    lines = []
    lines.append("{{Passive Skill Infobox")
    lines.append(f"|title = {escape_pipe(title)}")
    lines.append(f"|description = {escape_pipe(description)}")
    lines.append(f"|rank = {escape_pipe(str(rank or ''))}")
    lines.append(f"|effects = {escape_pipe(effects)}")
    lines.append("}}")
    return "\n".join(lines).rstrip() + "\n"


def build_infobox_entry(
    row_id: str,
    row: dict,
    *,
    en_skill_names: dict,
    en_skill_desc: dict,
) -> tuple[str, str, str]:
    row_id = str(row_id)

    name_keys = [
        row.get("OverrideNameTextID"),
        row.get("OverrideSummaryTextId"),
        f"PASSIVE_{row_id}",
        row_id,
    ]
    desc_keys = [
        row.get("OverrideDescMsgID"),
        f"PASSIVE_{row_id}",
        row_id,
    ]

    english_name = first_text(en_skill_names, name_keys)
    if english_name:
        english_name = clean_english_text(english_name)

    if not english_name:
        english_name = row_id

    english_desc = first_text(en_skill_desc, desc_keys)
    if english_desc:
        english_desc = clean_english_text(english_desc, row=row)

    rank = row.get("Rank", "")

    effect_slots = get_effect_slots(row)

    if not english_desc:
        english_desc = build_description_from_effects(effect_slots)

    effects_out_parts = []
    for e in effect_slots:
        label = e["effect_label"]
        val = e["effect_value_text"]
        if label and val:
            effects_out_parts.append(f"{label}*{val}")

    effects_out = "; ".join(effects_out_parts)

    wikitext = build_infobox_wikitext(
        title=english_name,
        description=english_desc,
        rank=rank,
        effects=effects_out,
    )

    return normalize_title(english_name), wikitext, english_name


def build_infobox_map() -> dict[str, str]:
    """Return { "English Name": "{{Passive Skill Infobox...}}\n" } for displayable passive skills."""
    print("🔍 Loading English text tables...")
    en_skill_names = load_text_table(en_name_file)
    en_skill_desc = load_text_table(en_description_file)

    print("🔍 Loading passive skills...")
    raw_passive_data = load_json(param_input_file)
    passive_data = extract_datatable_rows(raw_passive_data, source="DT_PassiveSkill_Main.json")

    out: dict[str, str] = {}
    total = len(passive_data)
    processed = 0
    kept = 0

    for passive_id, row in passive_data.items():
        if not isinstance(row, dict):
            continue

        processed += 1
        if processed % 250 == 0:
            print(f"🔄 Processed {processed}/{total} passive skills...")

        name, wikitext, english_name = build_infobox_entry(
            str(passive_id),
            row,
            en_skill_names=en_skill_names,
            en_skill_desc=en_skill_desc,
        )

        if not is_displayable_passive(str(passive_id), row, english_name=english_name):
            continue

        out[name] = wikitext
        kept += 1

    print(f"✅ Kept {kept}/{total} passive skills after filtering.")
    return out


def get_infobox_for_skill(skill_name: str, *, infobox_map: dict[str, str] | None = None) -> str:
    """Convenience helper for page builders: returns the infobox wikitext for a given skill name."""
    skill_name = normalize_title(skill_name)
    if infobox_map is None:
        infobox_map = build_infobox_map()
    return infobox_map.get(skill_name, "")


def main() -> None:
    infobox_map = build_infobox_map()

    ensure_directory(output_file)
    ordered_names = sorted(infobox_map.keys(), key=lambda s: s.casefold())
    lines = []
    for name in ordered_names:
        lines.append(infobox_map[name].rstrip())
        lines.append("")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    file_uri = Path(output_file).as_uri()
    print(f"✅ Wrote {len(ordered_names)} passive skill infobox entries to: {file_uri}")


if __name__ == "__main__":
    main()
