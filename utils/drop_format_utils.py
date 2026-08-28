from typing import Any, Optional

from utils.english_text_utils import EnglishText


def format_chance(rate_value: Any) -> str:
    try:
        f = float(rate_value)
    except Exception:
        return str(rate_value)

    if f.is_integer():
        return str(int(f))
    return str(f).rstrip("0").rstrip(".")


def get_item_display_name(en: EnglishText, item_id: str) -> str:
    item_id = str(item_id).strip()
    name = en.get_item_name(item_id)
    return name if name else item_id


def extract_drop_list(drop_row: Optional[dict], en: EnglishText) -> str:
    if not isinstance(drop_row, dict):
        return ""

    parts = []
    for i in range(1, 11):
        item_id = drop_row.get(f"ItemId{i}")
        rate = drop_row.get(f"Rate{i}")
        min_qty = drop_row.get(f"min{i}")
        max_qty = drop_row.get(f"Max{i}")

        if not item_id or str(item_id).lower() == "none":
            continue

        try:
            rate_f = float(rate)
        except Exception:
            rate_f = 0.0

        if rate_f <= 0:
            continue

        try:
            min_int = int(min_qty)
            max_int = int(max_qty)
        except Exception:
            continue

        if min_int <= 0 and max_int <= 0:
            continue

        item_name = get_item_display_name(en, item_id)

        qty_text = str(min_int) if min_int == max_int else f"{min_int}-{max_int}"
        chance_text = format_chance(rate)

        parts.append(f"{item_name}*{qty_text}@{chance_text}")

    return "; ".join(parts)
