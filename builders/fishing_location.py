import os
import sys
import json
from typing import Any, Dict, List, Tuple, Optional
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.json_datatable_utils import extract_datatable_rows
from utils.english_text_utils import EnglishText


FISHING_INPUT_DIR = os.path.join(constants.INPUT_DIRECTORY, "Fishing")

FISHING_SPOT_LOTTERY_PATH = os.path.join(
    FISHING_INPUT_DIR, "DT_PalFishingSpotLotteryDataTable.json"
)
FISH_SHADOW_PATH = os.path.join(
    FISHING_INPUT_DIR, "DT_PalFishShadowDataTable.json"
)
FISH_POND_LOTTERY_PATH = os.path.join(
    FISHING_INPUT_DIR, "DT_PalFishPondLotteryDataTable.json"
)


def load_rows(path: str, *, source: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return extract_datatable_rows(data, source=source)


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0

def _enum_suffix(v: Any) -> str:
    s = "" if v is None else str(v).strip()
    if s == "":
        return ""
    if "::" in s:
        return s.split("::")[-1].strip()
    return s

def _fmt_time_only(v: Any) -> str:
    s = "" if v is None else str(v).strip()
    if s == "" or s.lower() == "none":
        return ""
    return s


def _tod_code(only_time: str) -> str:
    t = _fmt_time_only(only_time)
    if t == "":
        return "a"
    t_low = t.lower()
    if "day" in t_low:
        return "d"
    if "night" in t_low:
        return "n"
    return "a"


def _rarity_code(lottery_name: str) -> str:
    name = (lottery_name or "").strip().lower()
    if "_rare" in name:
        return "r"
    return "c"


def _pal_name(en: EnglishText, pal_id: str) -> str:
    pal_id = (pal_id or "").strip()
    if pal_id == "":
        return ""

    if pal_id.startswith("BOSS_"):
        base_id = pal_id[len("BOSS_") :].strip()
        if base_id == "":
            return pal_id
        real = en.get_pal_name(base_id) or base_id
        return f"Alpha {real}"

    return en.get_pal_name(pal_id) or pal_id


def _parse_spot_tier_and_water(spot_name: str) -> Tuple[str, str]:
    name = (spot_name or "").strip()
    if name == "":
        return ("", "Pond")

    parts = name.split("_")
    tier = ""
    if len(parts) >= 2 and parts[0] == "FishingSpot":
        tier = parts[1]

    if "Ocean" in parts:
        return (tier, "Ocean")
    if "River" in parts:
        return (tier, "River")

    return (tier, "Pond")

def _build_spot_zone_index(
    fishing_spot_rows: dict,
    fish_shadow_rows: dict,
    *,
    en: EnglishText,
) -> Dict[str, Dict[Tuple[str, str], List[Dict[str, Any]]]]:
    shadow_to_pal: Dict[str, str] = {}

    for shadow_id, row in (fish_shadow_rows or {}).items():
        if not isinstance(row, dict):
            continue
        pal_id = (row.get("PalId") or "").strip()
        if pal_id:
            shadow_to_pal[str(shadow_id)] = pal_id

    zone_map: Dict[str, Dict[Tuple[str, str], List[Dict[str, Any]]]] = {}

    for _, row in (fishing_spot_rows or {}).items():
        if not isinstance(row, dict):
            continue

        zone = (row.get("GainItemLotteryName") or "").strip()
        if not zone:
            continue

        group = (row.get("LotteryName") or "").strip()
        only_time = _fmt_time_only(row.get("OnlyTime"))

        shadow_id = (row.get("FishShadowId") or "").strip()
        pal_id = shadow_to_pal.get(shadow_id)
        if not pal_id:
            continue

        zone_map.setdefault(zone, {}).setdefault((group, only_time), []).append(
            {
                "pal_id": pal_id,
                "pal_name": _pal_name(en, pal_id),
                "weight": _safe_float(row.get("Weight")),
                "lvl_min": row.get("MinLevel"),
                "lvl_max": row.get("MaxLevel"),
                "spot_difficulty": row.get("FishingSpotDifficulty"),
            }
        )

    for group_map in zone_map.values():
        for entries in group_map.values():
            entries.sort(key=lambda e: (e.get("pal_name") or "").lower())

    return zone_map


def _build_pond_zone_index(
    fish_pond_rows: dict,
    *,
    en: EnglishText,
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    zone_map: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    for _, row in (fish_pond_rows or {}).items():
        if not isinstance(row, dict):
            continue

        zone = (row.get("GainItemLotteryName") or "").strip()
        if not zone:
            continue

        size = (row.get("LotteryName") or "").strip()
        pal_id = (row.get("CharacterID") or "").strip()
        if not pal_id:
            continue

        zone_map.setdefault(zone, {}).setdefault(size, []).append(
            {
                "pal_id": pal_id,
                "pal_name": _pal_name(en, pal_id),
                "weight": _safe_float(row.get("Weight")),
                "lvl_min": row.get("CharacterLevelMin"),
                "lvl_max": row.get("CharacterLevelMax"),
            }
        )

    for size_map in zone_map.values():
        for entries in size_map.values():
            entries.sort(key=lambda e: (e.get("pal_name") or "").lower())

    return zone_map


def _build_deduped_spot_index(
    spot_by_zone: Dict[str, Dict[Tuple[str, str], List[Dict[str, Any]]]]
) -> Dict[Tuple[str, str, str, str], List[Tuple[str, str]]]:
    deduped: Dict[Tuple[str, str, str, str], Dict[str, Tuple[str, str]]] = {}

    for zone, group_map in (spot_by_zone or {}).items():
        for (spot_name, only_time), entries in (group_map or {}).items():
            tier, water = _parse_spot_tier_and_water(spot_name)
            time_label = only_time or "Any time"

            key = (zone, tier, water, time_label)
            if key not in deduped:
                deduped[key] = {}

            for e in entries:
                pal_id = (e.get("pal_id") or "").strip()
                pal_name = (e.get("pal_name") or "").strip()
                if pal_id == "" or pal_name == "":
                    continue

                if pal_id not in deduped[key]:
                    deduped[key][pal_id] = (pal_name, pal_id)

    out: Dict[Tuple[str, str, str, str], List[Tuple[str, str]]] = {}
    for key, pal_map in deduped.items():
        pals = list(pal_map.values())
        pals.sort(key=lambda t: (t[0].lower(), t[1].lower()))
        out[key] = pals

    return out


def _build_deduped_pond_index(
    pond_by_zone: Dict[str, Dict[str, List[Dict[str, Any]]]]
) -> Dict[Tuple[str, str, str, str], List[Tuple[str, str]]]:
    deduped: Dict[Tuple[str, str, str, str], Dict[str, Tuple[str, str]]] = {}

    for zone, size_map in (pond_by_zone or {}).items():
        for size_name, entries in (size_map or {}).items():
            tier = "Pond"
            water = "Pond"
            time_label = "Any time"

            key = (zone, tier, water, time_label)
            if key not in deduped:
                deduped[key] = {}

            for e in entries:
                pal_id = (e.get("pal_id") or "").strip()
                pal_name = (e.get("pal_name") or "").strip()
                if pal_id == "" or pal_name == "":
                    continue
                if pal_id not in deduped[key]:
                    deduped[key][pal_id] = (pal_name, pal_id)

    out: Dict[Tuple[str, str, str, str], List[Tuple[str, str]]] = {}
    for key, pal_map in deduped.items():
        pals = list(pal_map.values())
        pals.sort(key=lambda t: (t[0].lower(), t[1].lower()))
        out[key] = pals

    return out


def build_pal_fishing_locations_text(
    *,
    include_weights: bool = True,
    include_percent: bool = True,
) -> str:
    en = EnglishText()

    fishing_spot_rows = load_rows(
        FISHING_SPOT_LOTTERY_PATH,
        source="DT_PalFishingSpotLotteryDataTable",
    )
    fish_shadow_rows = load_rows(
        FISH_SHADOW_PATH,
        source="DT_PalFishShadowDataTable",
    )
    fish_pond_rows = load_rows(
        FISH_POND_LOTTERY_PATH,
        source="DT_PalFishPondLotteryDataTable",
    )

    spot_by_zone = _build_spot_zone_index(
        fishing_spot_rows,
        fish_shadow_rows,
        en=en,
    )
    pond_by_zone = _build_pond_zone_index(
        fish_pond_rows,
        en=en,
    )

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


def build_pal_fishing_locations_deduped_text() -> str:
    en = EnglishText()

    fishing_spot_rows = load_rows(
        FISHING_SPOT_LOTTERY_PATH,
        source="DT_PalFishingSpotLotteryDataTable",
    )
    fish_shadow_rows = load_rows(
        FISH_SHADOW_PATH,
        source="DT_PalFishShadowDataTable",
    )
    fish_pond_rows = load_rows(
        FISH_POND_LOTTERY_PATH,
        source="DT_PalFishPondLotteryDataTable",
    )

    spot_by_zone = _build_spot_zone_index(
        fishing_spot_rows,
        fish_shadow_rows,
        en=en,
    )
    pond_by_zone = _build_pond_zone_index(
        fish_pond_rows,
        en=en,
    )

    spot_deduped = _build_deduped_spot_index(spot_by_zone)
    pond_deduped = _build_deduped_pond_index(pond_by_zone)

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


def build_pal_fishing_locations_wikiformat_text() -> str:
    en = EnglishText()

    fishing_spot_rows = load_rows(
        FISHING_SPOT_LOTTERY_PATH,
        source="DT_PalFishingSpotLotteryDataTable",
    )
    fish_shadow_rows = load_rows(
        FISH_SHADOW_PATH,
        source="DT_PalFishShadowDataTable",
    )

    spot_by_zone = _build_spot_zone_index(
        fishing_spot_rows,
        fish_shadow_rows,
        en=en,
    )

    blocks: List[str] = []
    blocks.append("# Fishing Wiki Format\n")
    blocks.append("# Key format: <rarity>_<tod>_<idx>_<field>")
    blocks.append("# rarity: c=common, r=rare")
    blocks.append("# tod: d=day, n=night, a=any\n")

    # Index: (zone, tier, water) -> (rarity, tod) -> list[entry]
    index: Dict[Tuple[str, str, str], Dict[Tuple[str, str], List[Dict[str, Any]]]] = {}

    # Track a representative difficulty per (zone,tier,water)
    diff_map: Dict[Tuple[str, str, str], str] = {}

    for zone, group_map in (spot_by_zone or {}).items():
        for (lottery_name, only_time), entries in (group_map or {}).items():
            tier, water = _parse_spot_tier_and_water(lottery_name)
            if tier == "":
                continue

            key = (zone, tier, water)

            r_code = _rarity_code(lottery_name)
            t_code = _tod_code(only_time)

            index.setdefault(key, {}).setdefault((r_code, t_code), []).extend(entries)

            if key not in diff_map:
                for e in entries:
                    d = e.get("spot_difficulty")
                    d_clean = _enum_suffix(d)
                    if d_clean != "":
                        diff_map[key] = d_clean
                        break

    keys_sorted = sorted(index.keys(), key=lambda k: (k[0].lower(), k[1].lower(), k[2].lower()))

    for (zone, tier, water) in keys_sorted:
        blocks.append(f"## {zone} | Tier {tier} | {water}")
        blocks.append("{{Fishing Chances")

        # Combined location name (per your request)
        blocks.append(f"|location_name = {zone} {tier}")

        # Keep water type, but normalize to Ocean/River/Pond
        blocks.append(f"|water_type = {water}")

        difficulty = diff_map.get((zone, tier, water), "")
        if difficulty != "":
            blocks.append(f"|difficulty = {difficulty}")

        # stable output order:
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
                    weight = _safe_float(e.get("weight"))

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
