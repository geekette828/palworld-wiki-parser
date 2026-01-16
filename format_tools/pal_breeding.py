import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText

# Define paths
param_input_file = os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json")
output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "pal_breeding.txt")

EGG_SIZE_BY_RARITY = [
    (1, 4, "Regular"),
    (5, 7, "Large"),
    (8, 10, "Huge"),
]

EGG_ELEMENT_MAP = {
    "Neutral": "Common",
    "Ground": "Rocky",
    "Water": "Damp",
    "Electric": "Electric",
    "Grass": "Verdant",
    "Fire": "Scorching",
    "Ice": "Frozen",
    "Dark": "Dark",
    "Dragon": "Dragon",
}


def egg_size_from_rarity(rarity):
    if rarity is None:
        return ""
    try:
        r = int(rarity)
    except (TypeError, ValueError):
        return ""

    if r == 20:
        return "Huge"

    for low, high, label in EGG_SIZE_BY_RARITY:
        if low <= r <= high:
            return label

    return ""


def egg_type_from_element(element):
    if not element:
        return ""

    e = str(element).strip()
    if e.lower() == "normal":
        e = "Neutral"

    return EGG_ELEMENT_MAP.get(e, "")


def normalize_element(element):
    if not element:
        return ""

    e = str(element).strip()

    lower = e.lower()
    if lower == "normal":
        return "Neutral"
    if lower == "leaf":
        return "Grass"
    if lower == "electricity":
        return "Electric"
    if lower == "earth":
        return "Ground"

    return e


def after_double_colon(v):
    if v is None:
        return ""
    s = str(v)
    if "::" in s:
        return s.split("::", 1)[1]
    return s


def build_breeding_egg(row):
    if not isinstance(row, dict):
        return ""

    rarity = row.get("Rarity")
    element_raw = normalize_element(after_double_colon(row.get("ElementType1")))

    size = egg_size_from_rarity(rarity)
    egg_type = egg_type_from_element(element_raw)

    if not size or not egg_type:
        return ""

    if size == "Regular":
        return f"{egg_type} Egg"

    return f"{size} {egg_type} Egg"


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v)
    return str(v)


def zukan_no(zukan_index, zukan_suffix):
    if zukan_index is None:
        return ""
    try:
        idx = int(zukan_index)
    except (TypeError, ValueError):
        return ""

    if idx < 0:
        return ""

    base = str(idx).zfill(3)

    suf = "" if zukan_suffix is None else str(zukan_suffix).strip()
    if suf == "":
        return base
    return f"{base}{suf}"


def get_pal_display_name(en: EnglishText, pal_id: str) -> str:
    pal_id = str(pal_id).strip()
    return en.get_pal_name(pal_id) or pal_id


def main():
    with open(param_input_file, "r", encoding="utf-8") as f:
        param_data = json.load(f)

    rows = extract_datatable_rows(param_data, source="DT_PalMonsterParameter")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    en = EnglishText()

    pal_order = []

    for key, row in rows.items():
        if not isinstance(key, str):
            continue
        if not key.startswith("BOSS_"):
            continue

        base = key.replace("BOSS_", "")
        normal = rows.get(base)
        if not isinstance(normal, dict):
            continue

        pal_no = zukan_no(normal.get("ZukanIndex"), normal.get("ZukanIndexSuffix"))
        if pal_no == "":
            continue

        pal_order.append((pal_no, base))

    pal_order.sort(key=lambda x: (int(x[0][:3]), x[0][3:]))
    base_names = [base for _, base in pal_order]

    output_lines = []

    for base in base_names:
        normal = rows.get(base)
        boss = rows.get(f"BOSS_{base}")

        if not isinstance(normal, dict) or not isinstance(boss, dict):
            continue

        pal_display_name = get_pal_display_name(en, base)

        # Header comment so it's easy to find blocks
        output_lines.append(f"# {pal_display_name} ({base})")

        output_lines.append("==Breeding==")
        output_lines.append(
            "[[Breeding]] allows Pals to be paired together to produce offspring, with outcomes determined by various breeding statistics and special parent combinations. "
        )
        output_lines.append("{{Breeding")
        output_lines.append(f"|breeding_rank = {fmt(normal.get('CombiRank'))}")
        output_lines.append(f"|male_probability = {fmt(normal.get('MaleProbability'))}")
        output_lines.append(f"|combi_duplicate_priority = {fmt(normal.get('CombiDuplicatePriority'))}")
        output_lines.append(f"|egg = {build_breeding_egg(normal)}")
        output_lines.append("|uniqueCombos = ")
        output_lines.append("}}")
        output_lines.append("")
        output_lines.append("")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"✅ Wrote pal breeding data to: {output_file}")


if __name__ == "__main__":
    main()
