import os
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.console_utils import force_utf8_stdout
from builders.merchant_shop import (
    build_all_merchant_shop_models,
    MerchantItemModel,
    MerchantShopModel,
)
force_utf8_stdout()

output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Wiki Formatted", "merchant_shops.txt",)



def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

def _trim(v: object) -> str:
    return str(v or "").strip()

def _to_int(v: object, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default

def _render_merchant_template(
    *,
    merchant_name: str,
    shop_group: str,
    group_weight: int,
    items: List[MerchantItemModel],
) -> str:
    lines: List[str] = []

    lines.append("{{Merchant|" + merchant_name)
    lines.append(f"|shopGroup = {shop_group}")
    lines.append(f"|shopGroupWeight = {group_weight}")

    for idx, item in enumerate(items, start=1):
        item_name = _trim(item.get("itemName"))
        cost_amount = _to_int(item.get("costAmount"), default=0)
        currency = _trim(item.get("currency"))

        lines.append(f" |{idx}_itemName = {item_name}")
        lines.append(f"  |{idx}_costAmount = {cost_amount}")
        lines.append(f"  |{idx}_currency = {currency}")

        item_weight = item.get("itemWeight")
        if item_weight is not None:
            lines.append(f"  |{idx}_itemWeight = {int(item_weight)}")

    lines.append("}}")
    return "\n".join(lines)


def build_merchant_shops_wikitext(
    *,
    merchant_name_overrides: Optional[Dict[str, str]] = None,
    include_blank_line: bool = True,
) -> str:
    model = build_all_merchant_shop_models(
        merchant_name_overrides=merchant_name_overrides,
    )

    lines: List[str] = []

    for merchant_key in sorted(model.keys(), key=str.casefold):
        shop: MerchantShopModel = model[merchant_key]
        merchant_name = _trim(shop.get("merchantName"))

        lines.append(f"== {merchant_name} ==")
        lines.append(f"; Source key: {merchant_key}")

        for group in shop.get("shopGroups") or []:
            shop_group = _trim(group.get("shopGroup"))
            group_weight = _to_int(group.get("groupWeight"), default=0)
            items = group.get("items") or []

            lines.append(f"=== {shop_group} ===")
            lines.append(
                _render_merchant_template(
                    merchant_name=merchant_name,
                    shop_group=shop_group,
                    group_weight=group_weight,
                    items=items,
                )
            )

        if include_blank_line:
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"

def main() -> None:
    print("🔄 Building merchant shop export text...")

    text = build_merchant_shops_wikitext(include_blank_line=True)

    print(f"🔄 Writing output file: {output_file}")
    write_text(output_file, text)

    print(f"✅ Wrote: {output_file}")

if __name__ == "__main__":
    main()
