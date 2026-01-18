import os
import re
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import constants
from utils.english_text_utils import EnglishText
from utils.json_datatable_utils import extract_datatable_rows
from typing import Any, Dict, List, Optional, Tuple, TypedDict


recipe_input_file = os.path.join(constants.INPUT_DIRECTORY, "Item", "DT_ItemRecipeDataTable.json")
item_input_file = os.path.join(constants.INPUT_DIRECTORY, "Item", "DT_ItemDataTable.json")

_VARIANT_SUFFIX_RE = re.compile(r"^(?P<base>.+)_(?P<num>[2-5])$")
_SCHEMATIC_SUFFIX_RE = re.compile(r"\s+\d+$")


class RecipeRow(TypedDict, total=False):
    Product_Id: str
    Product_Count: Any
    WorkAmount: Any
    WorkableAttribute: Any
    UnlockItemID: str
    DenyRecipeChain: Any

    Material1_Id: str
    Material1_Count: Any
    Material2_Id: str
    Material2_Count: Any
    Material3_Id: str
    Material3_Count: Any
    Material4_Id: str
    Material4_Count: Any
    Material5_Id: str
    Material5_Count: Any


class CraftingRecipeVariant(TypedDict, total=False):
    workload: str
    ingredients: str


class CraftingRecipeModel(TypedDict, total=False):
    product: str
    yield_count: str
    workbench: str
    workload: str
    ingredients: str
    schematic: str
    variants: Dict[int, CraftingRecipeVariant]  # {2: {"workload": "...", "ingredients": "..."}, ...}


def _normalize_schematic_name(name: str) -> str:
    name = (name or "").strip()
    return _SCHEMATIC_SUFFIX_RE.sub("", name)


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _trim(v: Any) -> str:
    return str(v or "").strip()


def _is_none_text(v: Any) -> bool:
    s = _trim(v)
    return s == "" or s.lower() == "none"


def _format_number(v: Any) -> str:
    if v is None:
        return ""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return _trim(v)

    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return str(n).rstrip("0").rstrip(".")


def _format_workload(v: Any) -> str:
    if v is None:
        return ""
    try:
        n = float(v) / 100.0
    except (TypeError, ValueError):
        return _trim(v)

    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return str(n).rstrip("0").rstrip(".")


def _english_item_name(en: EnglishText, item_id: str) -> str:
    item_id = _trim(item_id)
    if not item_id or _is_none_text(item_id):
        return ""
    return en.get_item_name(item_id) or item_id


def _load_item_rows(*, input_path: str = item_input_file) -> Dict[str, Dict[str, Any]]:
    raw = _load_json(input_path)
    return extract_datatable_rows(raw, source=os.path.basename(input_path)) or {}


def _find_variant_item_ids_for_base(
    *,
    base_id: str,
    items_by_id: Dict[str, Dict[str, Any]],
) -> List[str]:
    """
    Variant rule:
    - Base item has OverrideName == "None"
    - Variants share ItemActorClass with base
    - Variant.OverrideName == "ITEM_NAME_<base_id>"
    """
    base_id = _trim(base_id)
    if not base_id:
        return []

    base_item = items_by_id.get(base_id)
    if not isinstance(base_item, dict):
        return []

    base_override = _trim(base_item.get("OverrideName"))
    if not _is_none_text(base_override):
        return []

    base_actor = _trim(base_item.get("ItemActorClass"))
    if _is_none_text(base_actor):
        return []

    base_name_key = f"ITEM_NAME_{base_id}"

    out: List[str] = []
    for item_id, row in items_by_id.items():
        if not isinstance(row, dict):
            continue

        actor = _trim(row.get("ItemActorClass"))
        override = _trim(row.get("OverrideName"))

        if actor != base_actor:
            continue
        if override != base_name_key:
            continue

        out.append(item_id)

    return out


def _build_ingredients(en: EnglishText, row: Dict[str, Any]) -> str:
    parts: List[str] = []

    for idx in (1, 2, 3, 4, 5):
        mat_id = _trim(row.get(f"Material{idx}_Id"))
        mat_count = _format_number(row.get(f"Material{idx}_Count"))

        if _is_none_text(mat_id):
            continue
        if not mat_count or mat_count == "0":
            continue

        mat_name = _english_item_name(en, mat_id)
        parts.append(f"{mat_name}*{mat_count}")

    return "; ".join(parts)


def _variant_info_from_product_id(product_id: str) -> Tuple[str, Optional[int]]:
    """
    Returns (base_id, variant_num).
    If not a variant, variant_num is None.
    """
    product_id = _trim(product_id)
    m = _VARIANT_SUFFIX_RE.match(product_id)
    if not m:
        return product_id, None
    return m.group("base"), int(m.group("num"))


def _list_from_any(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        out = []
        for x in v:
            s = _trim(x)
            if s and not _is_none_text(s):
                out.append(s)
        return out
    return []


def _true_variant_info_from_product_id(
    product_id: str,
    *,
    items_by_id: Dict[str, Dict[str, Any]],
) -> Tuple[str, Optional[int]]:
    """
    Returns (base_id, variant_num) ONLY if the product_id is a TRUE variant,
    according to ItemActorClass + OverrideName rules.

    If product_id looks like a suffix variant (e.g., Spear_2) but is NOT a true variant,
    returns (product_id, None) so it is treated as a standalone item.
    """
    product_id = _trim(product_id)

    m = _VARIANT_SUFFIX_RE.match(product_id)
    if not m:
        return product_id, None

    base_id = _trim(m.group("base"))
    variant_num = int(m.group("num"))

    if not base_id:
        return product_id, None

    variant_item_ids = _find_variant_item_ids_for_base(
        base_id=base_id,
        items_by_id=items_by_id,
    )

    if product_id in set(variant_item_ids):
        return base_id, variant_num

    return product_id, None


def _index_rows_by_product_id(rows: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    DT export row name is not guaranteed to equal Product_Id,
    so we build an index by Product_Id.
    """
    by_pid: Dict[str, Dict[str, Any]] = {}
    for _, row in (rows or {}).items():
        if not isinstance(row, dict):
            continue
        pid = _trim(row.get("Product_Id"))
        if not pid or _is_none_text(pid):
            continue
        if pid not in by_pid:
            by_pid[pid] = row
    return by_pid


def _load_recipe_rows(*, input_path: str = recipe_input_file) -> Dict[str, Dict[str, Any]]:
    raw = _load_json(input_path)
    return extract_datatable_rows(raw, source=os.path.basename(input_path)) or {}


def _build_model_for_base_and_variants(
    *,
    base_row: Dict[str, Any],
    variant_rows_by_num: Dict[int, Dict[str, Any]],
    en: EnglishText,
) -> CraftingRecipeModel:
    product_id = _trim(base_row.get("Product_Id"))
    product_name = _english_item_name(en, product_id)

    model: CraftingRecipeModel = {
        "product": product_name,
        "yield_count": _format_number(base_row.get("Product_Count")),
        "workbench": "",
        "workload": _format_workload(base_row.get("WorkAmount")),
        "ingredients": _build_ingredients(en, base_row),
    }

    if variant_rows_by_num:
        schematic = ""
        for n in sorted(variant_rows_by_num.keys()):
            unlock_id = _trim(variant_rows_by_num[n].get("UnlockItemID"))
            if unlock_id and not _is_none_text(unlock_id):
                raw_name = _english_item_name(en, unlock_id)
                if raw_name:
                    schematic = _normalize_schematic_name(raw_name)
                    break

        if not schematic:
            schematic = f"{product_name} Schematic" if product_name else ""

        model["schematic"] = schematic
        model["variants"] = {}

        for n, vrow in variant_rows_by_num.items():
            model["variants"][n] = {
                "workload": _format_workload(vrow.get("WorkAmount")),
                "ingredients": _build_ingredients(en, vrow),
            }

    return model


def build_item_recipe_model_by_id(
    product_id: str,
    *,
    recipe_path: str = recipe_input_file,
    item_path: str = item_input_file,
) -> Optional[CraftingRecipeModel]:
    """
    Mapping builder:
    Pass a Product_Id (internal) and get a canonical recipe model.
    """
    product_id = _trim(product_id)
    if not product_id:
        return None

    en = EnglishText()
    rows = _load_recipe_rows(input_path=recipe_path)
    by_pid = _index_rows_by_product_id(rows)

    items_by_id = _load_item_rows(input_path=item_path)

    base_id, variant_num = _true_variant_info_from_product_id(product_id, items_by_id=items_by_id)
    if variant_num is not None:
        product_id = base_id

    base_row = by_pid.get(product_id)
    if not isinstance(base_row, dict):
        return None

    variant_rows_by_num: Dict[int, Dict[str, Any]] = {}

    deny = _list_from_any(base_row.get("DenyRecipeChain"))
    if deny:
        for vid in deny:
            vrow = by_pid.get(vid)
            if not isinstance(vrow, dict):
                continue

            _, n = _true_variant_info_from_product_id(_trim(vrow.get("Product_Id")), items_by_id=items_by_id)
            if n is None:
                continue
            if 2 <= n <= 5:
                variant_rows_by_num[n] = vrow
    else:
        variant_item_ids = _find_variant_item_ids_for_base(
            base_id=product_id,
            items_by_id=items_by_id,
        )

        for vid in variant_item_ids:
            vrow = by_pid.get(vid)
            if not isinstance(vrow, dict):
                continue

            _, n = _variant_info_from_product_id(vid)
            if n is None:
                continue
            if 2 <= n <= 5:
                variant_rows_by_num[n] = vrow

    return _build_model_for_base_and_variants(
        base_row=base_row,
        variant_rows_by_num=variant_rows_by_num,
        en=en,
    )


def crafting_recipe_model_to_params(model: CraftingRecipeModel) -> Dict[str, str]:
    """
    Mapping helper for comparer:
    Converts model -> flat dict matching template param names.
    """
    if not model:
        return {}

    params: Dict[str, str] = {
        "product": _trim(model.get("product")),
        "yield": _trim(model.get("yield_count")),
        "workbench": _trim(model.get("workbench")),
        "ingredients": _trim(model.get("ingredients")),
        "workload": _trim(model.get("workload")),
    }

    variants = model.get("variants") or {}
    if variants:
        params["schematic"] = _trim(model.get("schematic"))

        for n in (2, 3, 4, 5):
            v = variants.get(n)
            if not v:
                continue
            params[f"{n}_workload"] = _trim(v.get("workload"))
            params[f"{n}_ingredients"] = _trim(v.get("ingredients"))
    else:
        params["schematic"] = _trim(model.get("schematic"))

    return params


def render_crafting_recipe(model: CraftingRecipeModel) -> str:
    if not model:
        return ""

    lines: List[str] = []
    lines.append("{{Crafting Recipe")
    lines.append(f"|product = {model.get('product', '')}")
    lines.append(f"|yield = {model.get('yield_count', '')}")
    lines.append(f"|workbench = {model.get('workbench', '')}")
    lines.append(f"|ingredients = {model.get('ingredients', '')}")
    lines.append(f"|workload = {model.get('workload', '')}")

    variants = model.get("variants") or {}
    if variants:
        lines.append(f"|schematic = {model.get('schematic', '')}")

        lines.append("")

        first = True
        for n in (2, 3, 4, 5):
            v = variants.get(n)
            if not v:
                continue

            if not first:
                lines.append("")
            first = False

            lines.append(f"|{n}_workload = {v.get('workload', '')}")
            lines.append(f"|{n}_ingredients = {v.get('ingredients', '')}")

    lines.append("}}")
    return "\n".join(lines).rstrip() + "\n"


def build_item_recipe_wikitext(product_id: str, *, input_path: str = recipe_input_file) -> str:
    """
    Renderer wrapper:
    Pass a Product_Id (internal) and get a Crafting Recipe template wikitext.
    """
    model = build_item_recipe_model_by_id(
        product_id,
        recipe_path=input_path,
        item_path=item_input_file,
    )
    if not model:
        return ""
    return render_crafting_recipe(model)


def build_all_item_recipes_text(*, input_path: str = recipe_input_file) -> str:
    """
    Returns a single wikitext blob containing all Crafting Recipe templates.
    Import-safe: no file writes.
    """
    blocks = build_all_item_recipe_blocks(input_path=input_path)

    parts: List[str] = []
    for _, wikitext in blocks:
        parts.append(wikitext.rstrip())

    return ("\n\n".join(parts).rstrip() + "\n") if parts else ""


def build_all_item_recipes_export_text(*, input_path: str = recipe_input_file) -> str:
    """
    Returns a single wikitext blob of all recipes with headers:
    ## Production Name (Internal Name)
    """
    en = EnglishText()
    rows = _load_recipe_rows(input_path=input_path)
    by_pid = _index_rows_by_product_id(rows)

    base_ids: List[str] = []
    seen: set[str] = set()

    items_by_id = _load_item_rows(input_path=item_input_file)

    for pid in by_pid.keys():
        base_id, variant_num = _true_variant_info_from_product_id(pid, items_by_id=items_by_id)
        if variant_num is not None:
            continue
        if base_id in seen:
            continue
        seen.add(base_id)
        base_ids.append(base_id)

    base_ids.sort(key=lambda x: (_english_item_name(en, x) or x).casefold())

    entries: List[str] = []
    for base_id in base_ids:
        production_name = _english_item_name(en, base_id) or base_id
        header = f"## {production_name} ({base_id})"

        recipe_text = build_item_recipe_wikitext(base_id, input_path=input_path).rstrip()
        if not recipe_text:
            continue

        entries.append(f"{header}\n{recipe_text}")

    return ("\n\n".join(entries).rstrip() + "\n") if entries else ""


def build_all_item_recipe_blocks(*, input_path: str = recipe_input_file) -> List[Tuple[str, str]]:
    """
    Returns a sorted list of (product_name, wikitext).
    Import-safe: no file writes.
    """
    en = EnglishText()
    rows = _load_recipe_rows(input_path=input_path)
    by_pid = _index_rows_by_product_id(rows)

    blocks: List[Tuple[str, str]] = []
    seen_base: set[str] = set()

    items_by_id = _load_item_rows(input_path=item_input_file)

    for pid, row in by_pid.items():
        if not isinstance(row, dict):
            continue

        base_id, variant_num = _true_variant_info_from_product_id(pid, items_by_id=items_by_id)
        if variant_num is not None:
            continue

        if base_id in seen_base:
            continue
        seen_base.add(base_id)

        text = build_item_recipe_wikitext(base_id, input_path=input_path)
        if not text:
            continue

        product_name = _english_item_name(en, base_id) or base_id
        blocks.append((product_name, text))

    blocks.sort(key=lambda x: x[0].casefold())
    return blocks
