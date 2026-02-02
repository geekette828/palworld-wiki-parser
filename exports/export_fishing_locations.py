import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from typing import List, Optional

force_utf8_stdout()

output_directory = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "Fishing")

output_file_detailed = os.path.join(output_directory, "Pal_Fishing_Locations.txt")
output_file_deduped = os.path.join(output_directory, "Pal_Fishing_Locations_Deduped.txt")
output_file_wikiformat = os.path.join(output_directory, "fishing_wikiformat.txt")

INCLUDE_WEIGHTS = True
INCLUDE_PERCENT = True

from builders.fishing_location import build_all_fishing_location_models


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def render_pal_fishing_locations_text(
    model: dict,
    *,
    include_weights: bool = True,
    include_percent: bool = True,
) -> str:
    spot_by_zone = model.get("spot_by_zone") or {}
    pond_by_zone = model.get("pond_by_zone") or {}

    zones = sorted(set(spot_by_zone) | set(pond_by_zone), key=str.lower)

    out: List[str] = []
    out.append("# Pal Fishing Locations\n")

    for zone in zones:
        out.append(f"== {zone} ==\n")

        spot_groups = spot_by_zone.get(zone, {})
        out.append("=== Fishing Spots ===\n")

        if not spot_groups:
            out.append("(none)\n")
        else:
            for (group, only_time), entries in sorted(
                spot_groups.items(),
                key=lambda kv: (kv[0][0], kv[0][1]),
            ):
                time_label = only_time or "Any time"
                out.append(f"* {group} ({time_label})")

                total_w = sum(e["weight"] for e in entries) or 0.0

                for e in entries:
                    bits: List[str] = []
                    if include_weights:
                        bits.append(f"w={e['weight']:g}")
                    if include_percent and total_w > 0:
                        bits.append(f"{(e['weight'] / total_w) * 100:.2f}%")

                    lvl_min = e.get("lvl_min")
                    lvl_max = e.get("lvl_max")
                    lvl = ""
                    if lvl_min is not None or lvl_max is not None:
                        lvl = f" Lv {lvl_min}-{lvl_max}"

                    suffix = f" [{' | '.join(bits)}]" if bits else ""
                    out.append(f"  - {e['pal_name']} ({e['pal_id']}){lvl}{suffix}")

                out.append("")

        pond_groups = pond_by_zone.get(zone, {})
        out.append("=== Fish Ponds ===\n")

        if not pond_groups:
            out.append("(none)\n")
        else:
            for size, entries in sorted(pond_groups.items()):
                out.append(f"* {size}")

                total_w = sum(e["weight"] for e in entries) or 0.0

                for e in entries:
                    lvl = ""
                    if e["lvl_min"] is not None or e["lvl_max"] is not None:
                        lvl = f" Lv {e['lvl_min']}-{e['lvl_max']}"

                    bits: List[str] = []
                    if include_weights:
                        bits.append(f"w={e['weight']:g}")
                    if include_percent and total_w > 0:
                        bits.append(f"{(e['weight'] / total_w) * 100:.2f}%")

                    suffix = f" [{' | '.join(bits)}]" if bits else ""
                    out.append(f"  - {e['pal_name']} ({e['pal_id']}){lvl}{suffix}")

                out.append("")

        out.append("")

    return "\n".join(out).rstrip() + "\n"


def render_pal_fishing_locations_deduped_text(model: dict) -> str:
    spot_deduped = model.get("spot_deduped") or {}
    pond_deduped = model.get("pond_deduped") or {}

    all_keys = sorted(
        set(spot_deduped.keys()) | set(pond_deduped.keys()),
        key=lambda k: (k[0].lower(), k[1].lower(), k[2].lower(), k[3].lower()),
    )

    out: List[str] = []
    out.append("# Pal Fishing Locations (Deduped)\n")
    out.append("Columns: Zone, Spot Tier, Water Type, Time of Day\n")

    current_zone: Optional[str] = None
    for (zone, tier, water, time_label) in all_keys:
        if current_zone != zone:
            current_zone = zone
            out.append(f"== {zone} ==\n")

        out.append(f"=== Tier {tier} | {water} | {time_label} ===")

        pals = spot_deduped.get((zone, tier, water, time_label))
        if pals is None:
            pals = pond_deduped.get((zone, tier, water, time_label)) or []

        if not pals:
            out.append("(none)\n")
            continue

        for pal_name, pal_id in pals:
            out.append(f"* {pal_name} ({pal_id})")

        out.append("")

    return "\n".join(out).rstrip() + "\n"


def render_pal_fishing_locations_wikiformat_text(model: dict) -> str:
    index = model.get("wikiformat_index") or {}
    diff_map = model.get("wikiformat_difficulty") or {}

    blocks: List[str] = []
    blocks.append("# Fishing Wiki Format\n")
    blocks.append("# Key format: <rarity>_<tod>_<idx>_<field>")
    blocks.append("# rarity: c=common, r=rare")
    blocks.append("# tod: d=day, n=night, a=any\n")

    keys_sorted = sorted(index.keys(), key=lambda k: (k[0].lower(), k[1].lower(), k[2].lower()))

    for (zone, tier, water) in keys_sorted:
        blocks.append(f"## {zone} | Tier {tier} | {water}")
        blocks.append("{{Fishing Chances")

        blocks.append(f"|location_name = {zone} {tier}")
        blocks.append(f"|water_type = {water}")

        difficulty = diff_map.get((zone, tier, water), "")
        if difficulty != "":
            blocks.append(f"|difficulty = {difficulty}")

        rarity_order = ["c", "r"]
        tod_order = ["d", "n", "a"]

        group_map = index.get((zone, tier, water), {})

        for r_code in rarity_order:
            for t_code in tod_order:
                rows = group_map.get((r_code, t_code), [])
                if not rows:
                    continue

                rows_sorted = sorted(
                    rows,
                    key=lambda e: (
                        (e.get("pal_name") or "").lower(),
                        (e.get("pal_id") or "").lower(),
                    ),
                )

                for idx, e in enumerate(rows_sorted, start=1):
                    pal_name = (e.get("pal_name") or "").strip()
                    weight = float(e.get("weight") or 0.0)

                    lvl_min = e.get("lvl_min")
                    lvl_max = e.get("lvl_max")

                    prefix = f"{r_code}_{t_code}_{idx}_"

                    blocks.append(f"  |{prefix}name = {pal_name}")
                    blocks.append(f"   |{prefix}weight = {weight:g}")

                    if lvl_min is not None:
                        blocks.append(f"   |{prefix}min = {lvl_min}")
                    if lvl_max is not None:
                        blocks.append(f"   |{prefix}max = {lvl_max}")

        blocks.append("}}")
        blocks.append("")

    return "\n".join(blocks).rstrip() + "\n"


def main() -> None:
    model = build_all_fishing_location_models()

    detailed = render_pal_fishing_locations_text(
        model,
        include_weights=INCLUDE_WEIGHTS,
        include_percent=INCLUDE_PERCENT,
    )
    write_text(output_file_detailed, detailed)
    print(f"Wrote: {output_file_detailed}")

    deduped = render_pal_fishing_locations_deduped_text(model)
    write_text(output_file_deduped, deduped)
    print(f"Wrote: {output_file_deduped}")

    wikiformat = render_pal_fishing_locations_wikiformat_text(model)
    write_text(output_file_wikiformat, wikiformat)
    print(f"Wrote: {output_file_wikiformat}")


if __name__ == "__main__":
    main()
