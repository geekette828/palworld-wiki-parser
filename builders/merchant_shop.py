import os
import sys
import json
from typing import Any, Dict, List, Optional, TypedDict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.english_text_utils import EnglishText
from utils.json_datatable_utils import extract_datatable_rows


itemshop_lottery_input_file = os.path.join(constants.INPUT_DIRECTORY, "ItemShop", "DT_ItemShopLotteryData.json")
itemshop_lottery_common_input_file = os.path.join(constants.INPUT_DIRECTORY, "ItemShop", "DT_ItemShopLotteryData_Common.json")

itemshop_create_input_file = os.path.join(constants.INPUT_DIRECTORY, "ItemShop", "DT_ItemShopCreateData.json")
itemshop_create_common_input_file = os.path.join(constants.INPUT_DIRECTORY, "ItemShop", "DT_ItemShopCreateData_Common.json")

itemshop_setting_input_file = os.path.join(constants.INPUT_DIRECTORY, "ItemShop", "DT_ItemShopSettingData.json")
itemshop_setting_common_input_file = os.path.join(constants.INPUT_DIRECTORY, "ItemShop", "DT_ItemShopSettingData_Common.json")


class MerchantItemModel(TypedDict, total=False):
    itemName: str
    itemId: str
    itemWeight: Optional[int]
    costAmount: int
    currency: str
    currencyId: str
    minQty: int
    maxQty: int
    productType: str
    stock: int


class MerchantShopGroupModel(TypedDict, total=False):
    shopGroup: str
    groupWeight: int
    currency: str
    currencyId: str
    items: List[MerchantItemModel]


class MerchantShopModel(TypedDict, total=False):
    merchantKey: str
    merchantName: str
    shopGroups: List[MerchantShopGroupModel]


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_rows(path: str) -> Dict[str, Dict[str, Any]]:
    raw = _load_json(path)
    return extract_datatable_rows(raw, source=os.path.basename(path)) or {}


def _to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _trim(v: Any) -> str:
    return str(v or "").strip()


def _english_item_name(en: EnglishText, item_id: str) -> str:
    item_id = _trim(item_id)
    if not item_id:
        return ""
    return en.get_item_name(item_id) or item_id


def _merge_rows(*paths: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for path in paths:
        if not os.path.exists(path):
            continue
        rows = _load_rows(path)
        for k, v in rows.items():
            if isinstance(k, str) and isinstance(v, dict):
                out[k] = v
    return out


def build_all_merchant_shop_models(
    *,
    merchant_name_overrides: Optional[Dict[str, str]] = None,
) -> Dict[str, MerchantShopModel]:
    """
    Returns a comparison-friendly model:

    {
      "<merchantKey>": {
         "merchantKey": "...",
         "merchantName": "...",
         "shopGroups": [
            {
               "shopGroup": "...",
               "groupWeight": 100,
               "currency": "Battle Ticket",
               "currencyId": "BattleTicket",
               "items": [
                  {"itemName": "...", "costAmount": 1500, "minQty": 1, "maxQty": 1, ...}
               ]
            }
         ]
      }
    }

    Notes:
    - merchantKey comes from DT_ItemShopLotteryData row key (e.g. ArenaShop1).
    - shopGroup comes from lottery entries (e.g. Arena_Shop_1).
    - itemWeight is None because the ItemShop Create table does not include per-item weights.
      If you later find item-level roll data, this field is already wired for it.
    """
    merchant_name_overrides = merchant_name_overrides or {}

    en = EnglishText()

    lottery_rows = _merge_rows(
        itemshop_lottery_common_input_file,
        itemshop_lottery_input_file,
    )

    create_rows = _merge_rows(
        itemshop_create_common_input_file,
        itemshop_create_input_file,
    )

    setting_rows = _merge_rows(
        itemshop_setting_common_input_file,
        itemshop_setting_input_file,
    )

    out: Dict[str, MerchantShopModel] = {}

    for merchant_key in sorted(lottery_rows.keys(), key=str.casefold):
        lottery_row = lottery_rows.get(merchant_key)
        if not isinstance(lottery_row, dict):
            continue

        lottery_array = lottery_row.get("lotteryDataArray")
        if not isinstance(lottery_array, list) or not lottery_array:
            continue

        merchant_name = merchant_name_overrides.get(merchant_key) or merchant_key

        shop_groups: List[MerchantShopGroupModel] = []

        for entry in lottery_array:
            if not isinstance(entry, dict):
                continue

            shop_group = _trim(entry.get("ShopGroupName"))
            group_weight = _to_int(entry.get("Weight"), default=0)

            if not shop_group:
                continue

            currency_id = ""
            currency_name = ""

            setting = setting_rows.get(shop_group)
            if isinstance(setting, dict):
                currency_id = _trim(setting.get("CurrencyItemID"))
                currency_name = _english_item_name(en, currency_id)

            create = create_rows.get(shop_group)
            items: List[MerchantItemModel] = []

            if isinstance(create, dict):
                product_array = create.get("productDataArray")
                if isinstance(product_array, list):
                    for prod in product_array:
                        if not isinstance(prod, dict):
                            continue

                        item_id = _trim(prod.get("StaticItemId"))
                        if not item_id:
                            continue

                        item_name = _english_item_name(en, item_id)
                        override_price = _to_int(prod.get("OverridePrice"), default=0)
                        product_num = _to_int(prod.get("ProductNum"), default=1)
                        stock = _to_int(prod.get("Stock"), default=0)
                        product_type = _trim(prod.get("ProductType"))

                        items.append(MerchantItemModel(
                            itemName=item_name,
                            itemId=item_id,
                            itemWeight=None,
                            costAmount=override_price,
                            currency=currency_name,
                            currencyId=currency_id,
                            minQty=product_num,
                            maxQty=product_num,
                            productType=product_type,
                            stock=stock,
                        ))

            # Stable ordering for comparisons and exports
            items_sorted = sorted(items, key=lambda d: (str(d.get("itemName") or "").casefold(), str(d.get("itemId") or "")))

            shop_groups.append(MerchantShopGroupModel(
                shopGroup=shop_group,
                groupWeight=group_weight,
                currency=currency_name,
                currencyId=currency_id,
                items=items_sorted,
            ))

        # Stable ordering of groups
        shop_groups_sorted = sorted(shop_groups, key=lambda d: (str(d.get("shopGroup") or "").casefold(), int(d.get("groupWeight") or 0)))

        out[merchant_key] = MerchantShopModel(
            merchantKey=merchant_key,
            merchantName=merchant_name,
            shopGroups=shop_groups_sorted,
        )

    return out
