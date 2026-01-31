import os
import re
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Any, Dict, Optional, List, Tuple, TypedDict
from config import constants
from functools import lru_cache
from utils.english_text_utils import EnglishText, clean_english_text
from utils.json_datatable_utils import extract_datatable_rows
from utils.console_utils import force_utf8_stdout
force_utf8_stdout()

#Paths
item_input_file = os.path.join(constants.INPUT_DIRECTORY, "Item", "DT_ItemDataTable.json")
en_name_file = constants.EN_ITEM_NAME_FILE
en_description_file = constants.EN_ITEM_DESC_FILE
en_skill_name_file = constants.EN_SKILL_NAME_FILE


_CACHED_ITEM_ROWS: Optional[Dict[str, Dict[str, Any]]] = None
_CACHED_ENGLISH_NAME_TO_ITEM_ID: Optional[Dict[str, str]] = None

_BARE_ITEM_ID_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9]*_[0-9]+)\b")
_TOKEN_RE = re.compile(r"<\s*(\w+)\s+id=\|\s*([^|]+)\s*\|/>([ \t\r\n]*)", re.IGNORECASE)
_NUM_TAG_RE = re.compile(r"<Num(?:Blue|Red)_\d+>", re.IGNORECASE)
_COMMON_TOKEN_RE = re.compile(r"\bCOMMON_[A-Za-z0-9_]+\b")

@lru_cache(maxsize=1)
def _load_common_text_map() -> Dict[str, str]:
    """
    Load constants.EN_COMMON_TEXT_FILE and return:
      COMMON_* -> LocalizedString (fallback SourceString)

    Handles DataTable format (preferred) and a couple fallback shapes.
    Also normalizes DataTable keys by stripping a trailing "_TextData".
    """
    out: Dict[str, str] = {}

    try:
        with open(constants.EN_COMMON_TEXT_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return out

    # Prefer DataTable extraction first
    try:
        rows = extract_datatable_rows(raw, source=os.path.basename(constants.EN_COMMON_TEXT_FILE)) or {}
        if isinstance(rows, dict) and rows:
            for key, entry in rows.items():
                if not isinstance(key, str) or not key:
                    continue
                if not isinstance(entry, dict):
                    continue

                text_data = entry.get("TextData") or {}
                if not isinstance(text_data, dict):
                    continue

                localized = text_data.get("LocalizedString") or text_data.get("SourceString")
                if not isinstance(localized, str) or not localized.strip():
                    continue

                clean_key = key
                if clean_key.endswith("_TextData"):
                    clean_key = clean_key[:-9]

                out[clean_key] = localized.strip()

            return out
    except Exception:
        pass

    # Fallback shapes (if not DataTable)
    items: List[Tuple[str, Any]] = []

    if isinstance(raw, dict):
        items = [(k, v) for k, v in raw.items()]

    elif isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue

            key = entry.get("Key") or entry.get("Name")
            if isinstance(key, str) and key:
                items.append((key, entry))
                continue

            if len(entry) == 1:
                k = next(iter(entry.keys()))
                v = entry.get(k)
                if isinstance(k, str) and k:
                    items.append((k, v))

    for key, entry in items:
        if not isinstance(key, str) or not key:
            continue

        text_data: Dict[str, Any] = {}
        if isinstance(entry, dict):
            text_data = entry.get("TextData") or {}
        if not isinstance(text_data, dict):
            continue

        localized = text_data.get("LocalizedString") or text_data.get("SourceString")
        if not isinstance(localized, str) or not localized.strip():
            continue

        clean_key = key
        if clean_key.endswith("_TextData"):
            clean_key = clean_key[:-9]

        out[clean_key] = localized.strip()

    return out

def _resolve_common_tokens(s: str) -> str:
    if not s:
        return ""

    mapping = _load_common_text_map()
    mapping_cf = {str(k).casefold(): v for k, v in mapping.items()}

    def repl(m: re.Match) -> str:
        token = m.group(0)
        return mapping.get(token) or mapping_cf.get(token.casefold(), token)

    return _COMMON_TOKEN_RE.sub(repl, s)

def _resolve_ui_common(token_id: str) -> str:
    token_id = (token_id or "").strip()
    if not token_id:
        return ""

    try:
        from config.name_map import RARITY_NAME_MAP, WORK_SUITABILITY_MAP  # type: ignore
    except Exception:
        RARITY_NAME_MAP = {}
        WORK_SUITABILITY_MAP = {}

    # Rarity token like RARITY_RARE
    mapped = None
    if isinstance(RARITY_NAME_MAP, dict):
        mapped = RARITY_NAME_MAP.get(token_id)
    if mapped:
        return str(mapped).strip()

    # Work suitability token like COMMON_WORK_SUITABILITY_GenerateElectricity
    if token_id.startswith("COMMON_WORK_SUITABILITY_"):
        suffix = token_id[len("COMMON_WORK_SUITABILITY_"):]
        internal = f"WorkSuitability_{suffix}"
        if isinstance(WORK_SUITABILITY_MAP, dict):
            ws = WORK_SUITABILITY_MAP.get(internal)
            if ws:
                return str(ws).strip()
        return suffix.replace("_", " ").strip()

    mapped_common = _load_common_text_map().get(token_id)
    if mapped_common:
        return mapped_common

    return token_id

def _resolve_active_skill_name(english: EnglishText, skill_id: str) -> str:
    skill_id = _trim(skill_id)
    if not skill_id or skill_id.lower() == "none":
        return ""

    # Try a few common key patterns used by Palworld text tables.
    # Return the first match; fall back to the raw id if nothing resolves.
    candidates = [
        skill_id,
        f"WAZA_{skill_id}",
        f"SKILL_{skill_id}",
        f"ACTIVE_{skill_id}",
    ]

    for k in candidates:
        name = english.get(en_skill_name_file, k)
        if name:
            return name

    return skill_id

def _resolve_passive_skill_name(english: EnglishText, passive_id: str) -> str:
    passive_id = _trim(passive_id)
    if not passive_id or passive_id.lower() == "none":
        return ""

    key = f"PASSIVE_{passive_id}"
    name = english.get(en_skill_name_file, key)
    return name or passive_id

def _resolve_passive_skill_list(english: EnglishText, row: Dict[str, Any]) -> str:
    ids = [
        _trim(row.get("PassiveSkillName")),
        _trim(row.get("PassiveSkillName2")),
        _trim(row.get("PassiveSkillName3")),
        _trim(row.get("PassiveSkillName4")),
    ]

    names: List[str] = []
    for pid in ids:
        if not pid or pid.lower() == "none":
            continue
        names.append(_resolve_passive_skill_name(english, pid))

    return " / ".join([n for n in names if n])

def _resolve_bare_item_ids_in_text(english: EnglishText, text: str) -> str:
    if not text:
        return ""

    def repl(m: re.Match) -> str:
        token_id = (m.group(1) or "").strip()
        if not token_id:
            return ""
        name = english.get_item_name(token_id)
        return name or token_id

    return _BARE_ITEM_ID_RE.sub(repl, text)

def _normalize_item_type(type_a: str) -> str:
    if type_a == "Blueprint":
        return "Schematic"
    return type_a

def _normalize_item_type_by_id(item_id: str, type_a: str, item_name: str) -> str:
    if type_a == "Essential":
        if item_id.startswith("BossDefeatReward_"):
            return "Pal Bounty Token"
        if item_id.startswith("SkillUnlock_"): #Pal Gear ID
            return "Key Item"
        if item_id.startswith("PalPassiveSkillChange_"):
            return "Implant"

    if type_a == "SpecialWeapon":
        if item_name.endswith("Sphere"):
            return "Sphere"

    return type_a

def _format_corruption_seconds(v: Any) -> str:
    if v is None:
        return ""
    try:
        hours = float(v)
    except (TypeError, ValueError):
        return ""

    if abs(hours) < 1e-12:
        return ""

    seconds = int(round(hours * 3600.0))
    return "" if seconds == 0 else str(seconds)

def _resolve_map_object_name(english: EnglishText, token_id: str) -> str:
    token_id = (token_id or "").strip()
    if not token_id:
        return ""

    keys = [
        token_id,
        f"MAPOBJECT_NAME_{token_id}",
        f"MAP_OBJECT_NAME_{token_id}",
        f"BUILD_OBJECT_{token_id}",
        f"BUILDOBJECT_{token_id}",
    ]

    v = english.get_first(constants.EN_BUILD_OBJECT_NAME_FILE, keys)
    return v or token_id


def _replace_description_tokens(english: EnglishText, text: str) -> str:
    if not text:
        return ""

    s = text.replace("\r", "").strip()

    # Remove numeric color wrappers, but keep the important token tags.
    s = _NUM_TAG_RE.sub("", s)
    s = s.replace("</>", "")

    def repl(m: re.Match) -> str:
        tag = (m.group(1) or "").strip().lower()
        token_id = (m.group(2) or "").strip()
        trailing_ws = m.group(3) or ""

        if tag == "itemname":
            return (english.get_item_name(token_id) or token_id) + trailing_ws

        if tag == "charactername":
            return (english.get_pal_name(token_id) or token_id) + trailing_ws

        if tag == "uicommon":
            return (_resolve_ui_common(token_id) or token_id) + trailing_ws
        
        if tag in ("skillname", "wazaname"):
            return (_resolve_active_skill_name(english, token_id) or token_id) + trailing_ws

        if tag == "mapobjectname":
            return (_resolve_map_object_name(english, token_id) or token_id) + trailing_ws

        return token_id + trailing_ws


    s = _TOKEN_RE.sub(repl, s)

    # Light whitespace cleanup
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


class ItemInfoboxModel(TypedDict, total=False):
    item_id: str
    display_name: str
    description: str
    type: str
    subtype: str
    rarity: str
    sell: str
    weight: str
    technology: str

    nutrition: str
    san: str
    corruption: str
    consumeEffect: str

    qualities: str
    durability: str
    health: str
    defense: str
    attack: str
    magazine: str
    shield: str
    equip_effect: str

def item_infobox_model_to_params(model: ItemInfoboxModel) -> Dict[str, str]:
    """
    Mapping helper for comparer:
    Converts model -> flat dict matching {{Item}} template param names.
    """
    if not model:
        return {}

    keys = [
        # core
        "description", "type", "subtype", "rarity", "sell", "weight", "technology",

        # equipment
        "qualities", "durability", "health", "defense", "attack", "magazine", "shield", "equip_effect",

        # consumable
        "nutrition", "san", "corruption", "consumeEffect",
    ]

    out: Dict[str, str] = {}
    for k in keys:
        out[k] = _trim(model.get(k, ""))

    # If the page uses the combined variant format (qualities),
    # the single-stat equipment params should not be compared/expected.
    if _trim(out.get("qualities")):
        for k in ("durability", "health", "defense", "attack", "magazine", "shield", "equip_effect"):
            out[k] = ""

    return out


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _trim(v: Any) -> str:
    return str(v or "").strip()


def _leaf_enum(v: Any) -> str:
    s = _trim(v)
    if "::" in s:
        return s.split("::", 1)[1].strip()
    return s


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

def _format_weight(v: Any) -> str:
    if v is None:
        return ""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""

    # Keep decimals when present; if whole number, show as int string.
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))

    return str(f).rstrip("0").rstrip(".")


def _format_sell_from_price(price: Any) -> str:
    if price is None:
        return ""
    try:
        n = float(price)
    except (TypeError, ValueError):
        return ""

    # Buy price in data; sell is /10 
    sell = n / 10.0
    if abs(sell - round(sell)) < 1e-9:
        return str(int(round(sell)))
    return str(sell).rstrip("0").rstrip(".")


def _normalize_rarity(rarity_value: Any) -> str:
    s = _format_number(rarity_value)
    if not s:
        return ""

    try:
        n = int(float(s))
    except (TypeError, ValueError):
        return s

    try:
        from config.name_map import RARITY_NAME_MAP  # type: ignore
        if isinstance(RARITY_NAME_MAP, dict):
            mapped = RARITY_NAME_MAP.get(n)
            if mapped:
                return str(mapped).strip()
    except Exception:
        pass

    return str(n)

def _is_none_text(v: Any) -> bool:
    s = _trim(v)
    return s == "" or s.lower() == "none"


def _armor_subtype(type_b_leaf: str, has_variants: bool) -> str:
    if type_b_leaf == "ArmorBody":
        return "Body Armor"
    if type_b_leaf == "ArmorHead":
        return "Head Armor" if has_variants else "Hat"
    if type_b_leaf == "Shield":
        return "Shield"
    return ""

def _weapon_subtype(type_b_leaf: str, display_name: str) -> str:
    ranged = {
        "WeaponBow",
        "WeaponAssaultRifle",
        "WeaponShotgun",
        "WeaponCrossbow",
        "WeaponFlameThrower",
        "WeaponRocketLauncher",
        "WeaponHandgun",
        "WeaponGatlingGun",
    }

    if type_b_leaf in ranged:
        return "Ranged"

    if type_b_leaf == "WeaponThrowObject":
        return "Grenade"

    if type_b_leaf in {"WeaponFishingRod", "WeaponGrapplingGun", "WeaponMetalDetector"}:
        return "Tool"

    if type_b_leaf == "WeaponMelee":
        # Tool override by production name (case sensitive as requested)
        if (" Pickaxe" in display_name) or (" Axe" in display_name) or ("Sphere Launcher" in display_name):
            return "Tool"
        return "Melee"

    return ""

def _accessory_subtype(display_name: str) -> str:
    # Support Whistle subtype by name (case sensitive)
    if "Support Whistle" in display_name:
        return "Support Whistle"
    return ""

def _consumable_type_and_subtype(item_id: str, type_a_leaf: str, type_b_leaf: str) -> Tuple[str, str]:
    # Food is a Consumable on the wiki
    if type_a_leaf == "Food":
        wiki_type = "Consumable"

        # FoodDish* => Food
        if type_b_leaf.startswith("FoodDish"):
            return wiki_type, "Food"

        # Food* (not dish) => Ingredient
        if type_b_leaf.startswith("Food"):
            return wiki_type, "Ingredient"

        return wiki_type, ""

    # Consume is also a Consumable on the wiki
    if type_a_leaf == "Consume":
        wiki_type = "Consumable"

        # WorkSuitability_AddTicket_* => Pal Stat Boost
        if item_id.startswith("WorkSuitability_AddTicket_"):
            return wiki_type, "Pal Stat Boost"

        if type_b_leaf == "ConsumeTechnologyBook":
            return wiki_type, "Technical Manual"
        if type_b_leaf in {"ConsumeMedicine", "ConsumeDrug"}:
            return wiki_type, "Medicine"
        if type_b_leaf == "ConsumeWazaMachine":
            return wiki_type, "Skill Fruit"
        if type_b_leaf == "ConsumeOther":
            return wiki_type, ""

        return wiki_type, ""

    return type_a_leaf, ""

def _build_consume_effect(row: Dict[str, Any]) -> str:
    parts: List[str] = []

    for idx in (1, 2, 3):
        effect_id = _format_number(row.get(f"GrantEffect{idx}Id"))
        effect_time = _format_number(row.get(f"GrantEffect{idx}Time"))

        if effect_id and effect_id != "0":
            if effect_time and effect_time != "0":
                parts.append(f"{effect_id} ({effect_time}s)")
            else:
                parts.append(effect_id)

    return ", ".join(parts)


def _build_weapon_quality_line(quality_name: str, row: Dict[str, Any]) -> str:
    parts: List[str] = []

    sell = _format_sell_from_price(row.get("Price"))
    if sell:
        parts.append(f"sell={sell}")

    durability = _equipment_value_int(row.get("Durability"))
    if durability and durability != "0":
        parts.append(f"durability={durability}")

    attack = _equipment_value_int(row.get("PhysicalAttackValue"))
    if attack and attack != "0":
        parts.append(f"attack={attack}")

    magazine = _equipment_value_int(row.get("MagazineSize"))
    if magazine and magazine != "0":
        parts.append(f"magazine={magazine}")

    if not parts:
        return ""

    return f"{quality_name}: " + ", ".join(parts)


def _equipment_value_int(v: Any) -> str:
    if v is None:
        return ""
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return ""
    if n == 0:
        return ""
    return str(n)


def _build_quality_line(english: EnglishText, quality_name: str, row: Dict[str, Any]) -> str:
    parts: List[str] = []

    sell = _format_sell_from_price(row.get("Price"))
    if sell:
        parts.append(f"sell={sell}")

    durability = _equipment_value_int(row.get("Durability"))
    if durability and durability != "0":
        parts.append(f"durability={durability}")

    defense = _equipment_value_int(row.get("PhysicalDefenseValue"))
    if defense and defense != "0":
        parts.append(f"defense={defense}")

    health = _equipment_value_int(row.get("HPValue"))
    if health and health != "0":
        parts.append(f"health={health}")

    equip = _resolve_passive_skill_list(english, row)
    if equip:
        parts.append(f"equip_effect={equip}")

    if not parts:
        return ""

    return f"{quality_name}: " + ", ".join(parts)


def _load_item_rows() -> Dict[str, Dict[str, Any]]:
    global _CACHED_ITEM_ROWS
    if _CACHED_ITEM_ROWS is not None:
        return _CACHED_ITEM_ROWS

    data = _load_json(item_input_file)
    _CACHED_ITEM_ROWS = extract_datatable_rows(data, source=os.path.basename(item_input_file)) or {}
    return _CACHED_ITEM_ROWS


def _alt_item_name_ids(item_id: str) -> List[str]:
    item_id = _trim(item_id)
    if not item_id:
        return []

    out = [item_id]

    m = re.match(r"^(.*?)(\d+)$", item_id)
    if m:
        base = m.group(1)
        num = m.group(2)
        out.append(f"{base}_{num}")

    return out


def _normalize_english_key(s: str) -> str:
    s = re.sub(r"\s+", " ", _trim(s))
    return s.casefold()


def _build_english_name_to_item_id_map(english: EnglishText) -> Dict[str, str]:
    """
    Invert DT_ItemNameText_Common entries so we can accept English item names as inputs.
    We accept keys like:
      ITEM_NAME_<id>
      ITEM_<id>
    If collisions happen, ITEM_NAME_ wins.
    """
    raw = _load_json(en_name_file)
    rows = extract_datatable_rows(raw, source=os.path.basename(en_name_file)) or {}

    mapping: Dict[str, str] = {}

    prefixes = ["ITEM_NAME_", "ITEM_"]

    for prefix in prefixes:
        for key in rows.keys():
            if not isinstance(key, str):
                continue
            if not key.startswith(prefix):
                continue

            item_id = key[len(prefix):].strip()
            if not item_id:
                continue

            en_name = english.get(en_name_file, key)
            if not en_name:
                continue

            k = _normalize_english_key(en_name)
            if k not in mapping:
                mapping[k] = item_id

    return mapping



def resolve_item_id_from_english_name(english_item_name: str, english: Optional[EnglishText] = None) -> str:
    global _CACHED_ENGLISH_NAME_TO_ITEM_ID
    english = english or EnglishText()

    if _CACHED_ENGLISH_NAME_TO_ITEM_ID is None:
        _CACHED_ENGLISH_NAME_TO_ITEM_ID = _build_english_name_to_item_id_map(english)

    key = _normalize_english_key(english_item_name)
    return _CACHED_ENGLISH_NAME_TO_ITEM_ID.get(key, "")


def _get_item_description(english: EnglishText, item_id: str, row: Optional[Dict[str, Any]]) -> str:
    for candidate_id in _alt_item_name_ids(item_id):
        keys = [
            f"ITEM_DESC_{candidate_id}",
            f"ITEM_DESCRIPTION_{candidate_id}",
            f"ITEM_{candidate_id}",
        ]

        for k in keys:
            raw = english.get_raw(en_description_file, k)
            if raw:
                return _replace_description_tokens(english, raw)

    return ""

def build_item_infobox_wikitext_by_id(item_id: str, *, include_heading: bool = False) -> str:
    """
    Renderer wrapper:
    Pass an internal item_id and get rendered infobox wikitext back.
    """
    model = build_item_infobox_model_by_id(item_id)
    if not model:
        return ""
    return render_item_infobox(model, include_heading=include_heading)

def build_item_infobox_model_for_page(item_id: str) -> ItemInfoboxModel:
    """
    Page-builder entry-point:
    - For Armor/Weapon variants that share ItemActorClass + TypeA + TypeB, return a single combined model
      with |qualities=... using the Common (rarity 0) item as the base when available.
    - Otherwise, return the normal single-item model.
    """
    item_id = _trim(item_id)
    if not item_id:
        return {}

    english = EnglishText()
    item_rows = _load_item_rows()

    row = item_rows.get(item_id)
    if not isinstance(row, dict):
        return {}
    
    display_name = ""
    for candidate_id in _alt_item_name_ids(item_id):
        display_name = english.get_item_name(candidate_id)
        if display_name:
            break
    if not display_name:
        display_name = item_id

    raw_type_a = _leaf_enum(row.get("TypeA"))
    type_a = _normalize_item_type(raw_type_a)
    type_a = _normalize_item_type_by_id(item_id, type_a, display_name)
    type_b = _leaf_enum(row.get("TypeB"))
    actor = _trim(row.get("ItemActorClass"))

    # Only Armor/Weapon can be merged into a variant-style infobox
    if type_a not in {"Armor", "Weapon"}:
        return build_item_infobox_model_by_id(item_id)

    # If there is no meaningful actor class, treat as single-item
    if not actor or actor.lower() == "none":
        return build_item_infobox_model_by_id(item_id)

    # Collect all item ids in the same variant group (actor + type_a + type_b)
    group_ids: List[str] = []
    for iid, r in item_rows.items():
        if not isinstance(r, dict):
            continue
        if r.get("bLegalInGame") is False:
            continue

        r_actor = _trim(r.get("ItemActorClass"))
        if not r_actor or r_actor.lower() == "none":
            continue

        if r_actor != actor:
            continue

        r_type_a = _normalize_item_type(_leaf_enum(r.get("TypeA")))
        r_name = ""
        for candidate_id in _alt_item_name_ids(iid):
            r_name = english.get_item_name(candidate_id)
            if r_name:
                break
        if not r_name:
            r_name = iid

        r_type_a = _normalize_item_type_by_id(iid, r_type_a, r_name)
        r_type_b = _leaf_enum(r.get("TypeB"))

        if r_type_a == type_a and r_type_b == type_b:
            group_ids.append(iid)

    # If only one item in the group, don’t use qualities format
    if len(group_ids) <= 1:
        return build_item_infobox_model_by_id(item_id)

    def rarity_num(i: str) -> int:
        rr = item_rows.get(i, {}).get("Rarity")
        try:
            return int(float(rr))
        except Exception:
            return 999

    ids_sorted = sorted(group_ids, key=rarity_num)

    # Prefer Common (rarity 0) as the base
    base_id = ids_sorted[0]
    for i in ids_sorted:
        if rarity_num(i) == 0:
            base_id = i
            break

    base_model = build_item_infobox_model_by_id(base_id)
    if not base_model:
        return {}

    display_name = _trim(base_model.get("display_name"))
    if not display_name:
        return {}

    # subtype behavior changes when variants exist (matches your existing export logic)
    if type_a == "Armor":
        base_model["subtype"] = _armor_subtype(type_b, has_variants=True)
    elif type_a == "Weapon":
        base_model["subtype"] = _weapon_subtype(type_b, display_name)

    # Build qualities lines
    quality_lines: List[str] = []
    for iid in ids_sorted:
        r = item_rows.get(iid)
        if not isinstance(r, dict):
            continue

        q = _normalize_rarity(r.get("Rarity"))
        if not q:
            continue

        if type_a == "Armor":
            line = _build_quality_line(english, q, r)
        else:
            line = _build_weapon_quality_line(q, r)

        if line:
            quality_lines.append(line)

    if quality_lines:
        base_model["qualities"] = ";\n  ".join(quality_lines)

        # When using qualities, top-level rarity/sell should not appear
        base_model["rarity"] = ""
        base_model["sell"] = ""

    return base_model


def build_item_infobox_model_by_id(item_id: str) -> ItemInfoboxModel:
    english = EnglishText()
    item_rows = _load_item_rows()
    row = item_rows.get(item_id)
    if not isinstance(row, dict):
        return {}

    display_name = ""
    for candidate_id in _alt_item_name_ids(item_id):
        display_name = english.get_item_name(candidate_id)
        if display_name:
            break
    if not display_name:
        display_name = item_id


    description = _get_item_description(english, item_id, row)
    description = _replace_description_tokens(english, description)
    description = _resolve_bare_item_ids_in_text(english, description)


    raw_type_a = _leaf_enum(row.get("TypeA"))
    type_a = _normalize_item_type(raw_type_a)
    type_a = _normalize_item_type_by_id(item_id, type_a, display_name)
    type_b = _leaf_enum(row.get("TypeB"))
    wiki_type, wiki_subtype = _consumable_type_and_subtype(item_id, type_a, type_b)
    if wiki_type == "Accessory":
        wiki_subtype = _accessory_subtype(display_name) or wiki_subtype
    
    if item_id.startswith("SkillUnlock_"):
        if wiki_type == "Key Item":
            wiki_subtype = "Pal Gear"

    model: ItemInfoboxModel = {
        "item_id": item_id,
        "display_name": display_name,
        "description": description,
        "type": wiki_type,
        "subtype": wiki_subtype,
        "rarity": _normalize_rarity(row.get("Rarity")),
        "sell": _format_sell_from_price(row.get("Price")),
        "weight": _format_weight(row.get("Weight")),
        "technology": "", #_format_number(row.get("TechnologyTreeLock")),
    }

    if wiki_type == "Armor":
        model["subtype"] = _armor_subtype(type_b, has_variants=False)

        # Body / Head armor
        if type_b in {"ArmorBody", "ArmorHead"}:
            model["durability"] = _equipment_value_int(row.get("Durability"))
            model["health"] = _equipment_value_int(row.get("HPValue"))
            model["defense"] = _equipment_value_int(row.get("PhysicalDefenseValue"))

            model["equip_effect"] = _resolve_passive_skill_list(english, row)

        # Shields
        elif type_b == "Shield":
            model["durability"] = _equipment_value_int(row.get("Durability"))
            model["shield"] = _equipment_value_int(row.get("ShieldValue"))
    
    elif wiki_type == "Weapon":
        model["subtype"] = _weapon_subtype(type_b, display_name)

        model["durability"] = _equipment_value_int(row.get("Durability"))
        model["attack"] = _equipment_value_int(row.get("PhysicalAttackValue"))
        model["magazine"] = _equipment_value_int(row.get("MagazineSize"))

    elif wiki_type == "Consumable":
        # Food & Consume types land here
        if wiki_subtype == "Skill Fruit":
            # Skill Fruits aren't food; the wiki leaves nutrition/san/corruption blank
            model["consumeEffect"] = _build_consume_effect(row)
        else:
            model["nutrition"] = _format_number(row.get("RestoreSatiety"))
            model["san"] = _format_number(row.get("RestoreSanity"))
            model["corruption"] = _format_corruption_seconds(row.get("CorruptionFactor"))
            model["consumeEffect"] = _build_consume_effect(row)

    # Resolve COMMON_* localization tokens in all string fields
    for k, v in list(model.items()):
        if isinstance(v, str):
            model[k] = _resolve_common_tokens(v)

    return model


def build_item_infobox_model(english_item_name: str) -> ItemInfoboxModel:
    """
    Builder entry-point:
    Given an English item name, return canonical infobox fields (model).
    """
    english = EnglishText()
    item_id = resolve_item_id_from_english_name(english_item_name, english=english)
    if not item_id:
        return {}
    return build_item_infobox_model_by_id(item_id)


def render_item_infobox(model: ItemInfoboxModel, *, include_heading: bool = True) -> str:
    """
    Render entry-point:
    Convert an infobox model into canonical wikitext.
    """
    if not model:
        return ""

    display_name = (model.get("display_name") or "").strip()

    lines: List[str] = []

    if include_heading:
        lines.append(f"## {display_name}")

    lines.extend([
        "{{Item",
        f"|description = {model.get('description', '')}",
        f"|type = {model.get('type', '')}",
        f"|subtype = {model.get('subtype', '')}",
    ])

    # Only include rarity/sell in the top section when not using qualities
    if not _trim(model.get("qualities")):
        lines.append(f"|rarity = {model.get('rarity', '')}")
        lines.append(f"|sell = {model.get('sell', '')}")

    lines.extend([
        f"|weight = {model.get('weight', '')}",
        f"|technology = {model.get('technology', '')}",
    ])

    # Equipment section
    if _trim(model.get("qualities")) or _trim(model.get("durability")) or _trim(model.get("attack")) or _trim(model.get("magazine")) or _trim(model.get("health")) or _trim(model.get("defense")) or _trim(model.get("shield")) or _trim(model.get("equip_effect")):
        lines.append("<!-- Equipment Data -->")

        qualities = _trim(model.get("qualities"))
        if qualities:
            lines.append("|qualities =")
            lines.append(f"  {qualities}")
        else:
            if _trim(model.get("durability")):
                lines.append(f"|durability = {model.get('durability', '')}")
            if _trim(model.get("attack")):
                lines.append(f"|attack = {model.get('attack', '')}")
            if _trim(model.get("magazine")):
                lines.append(f"|magazine = {model.get('magazine', '')}")
            if _trim(model.get("health")):
                lines.append(f"|health = {model.get('health', '')}")
            if _trim(model.get("defense")):
                lines.append(f"|defense = {model.get('defense', '')}")
            if _trim(model.get("shield")):
                lines.append(f"|shield = {model.get('shield', '')}")
            if _trim(model.get("equip_effect")):
                lines.append(f"|equip_effect = {model.get('equip_effect', '')}")

    # Consumable section
    if _trim(model.get("nutrition")) or _trim(model.get("san")) or _trim(model.get("corruption")) or _trim(model.get("consumeEffect")):
        lines.append("<!-- Consumable Data -->")
        if _trim(model.get("nutrition")):
            lines.append(f"|nutrition = {model.get('nutrition', '')}")
        if _trim(model.get("san")):
            lines.append(f"|san = {model.get('san', '')}")
        if _trim(model.get("corruption")):
            lines.append(f"|corruption = {model.get('corruption', '')}")
        if _trim(model.get("consumeEffect")):
            lines.append(f"|consumeEffect = {model.get('consumeEffect', '')}")

    lines.extend([
        "}}",
        "",
        "",
    ])

    return "\n".join(lines)


def build_item_infobox(english_item_name: str) -> str:
    """
    Convenience wrapper:
    pass an English item name, get rendered infobox block back.
    """
    model = build_item_infobox_model(english_item_name)
    return render_item_infobox(model, include_heading=True)


def build_all_item_infobox_blocks() -> List[Tuple[str, str]]:
    english = EnglishText()
    item_rows = _load_item_rows()

    # Build groups (generic variant grouping)
    # Group key: (ItemActorClass, TypeA leaf, TypeB leaf) when ItemActorClass is meaningful.
    # Otherwise, each item is its own group.
    groups: Dict[Tuple[str, str, str], List[str]] = {}
    for item_id, row in item_rows.items():
        if not isinstance(row, dict):
            continue
        if row.get("bLegalInGame") is False:
            continue

        type_a = _leaf_enum(row.get("TypeA"))
        type_b = _leaf_enum(row.get("TypeB"))
        actor = _trim(row.get("ItemActorClass"))

        if actor and actor.lower() != "none":
            key = (actor, type_a, type_b)
        else:
            key = (item_id, type_a, type_b)

        groups.setdefault(key, []).append(item_id)

    blocks: List[Tuple[str, str]] = []

    for (actor, type_a, type_b), ids in groups.items():
        # Non-armor: emit each item individually (same as today)
        if type_a not in {"Armor", "Weapon"}:
            for item_id in ids:
                model = build_item_infobox_model_by_id(item_id)
                if not model:
                    continue

                display_name = _trim(model.get("display_name"))
                if not display_name:
                    continue

                block = render_item_infobox(model, include_heading=False)
                if block:
                    header = f"## {display_name} ({item_id})\n"
                    blocks.append((display_name, header + block))
            continue

        # Armor: if only one entry in the group, same behavior as today
        if len(ids) == 1:
            item_id = ids[0]
            model = build_item_infobox_model_by_id(item_id)
            if not model:
                continue

            display_name = _trim(model.get("display_name"))
            if not display_name:
                continue

            block = render_item_infobox(model, include_heading=False)
            if block:
                header = f"## {display_name} ({item_id})\n"
                blocks.append((display_name, header + block))
            continue

        # Variants: Armor and Weapon get combined into one infobox using the COMMON (rarity 0) item
        # Pick the base/common row if present, else the lowest rarity.
        def rarity_num(i: str) -> int:
            r = item_rows.get(i, {}).get("Rarity")
            try:
                return int(float(r))
            except Exception:
                return 999

        ids_sorted = sorted(ids, key=rarity_num)
        base_id = ids_sorted[0]
        for i in ids_sorted:
            if rarity_num(i) == 0:
                base_id = i
                break

        base_model = build_item_infobox_model_by_id(base_id)
        if not base_model:
            continue

        display_name = _trim(base_model.get("display_name"))
        if not display_name:
            continue

        # subtype: hat vs head armor depends on whether variants exist
        if type_a == "Armor":
            base_model["subtype"] = _armor_subtype(type_b, has_variants=True)
        elif type_a == "Weapon":
            base_model["subtype"] = _weapon_subtype(type_b, display_name)


        # Build qualities in Common -> Legendary order when present
        quality_lines: List[str] = []
        for item_id in ids_sorted:
            row = item_rows.get(item_id)
            if not isinstance(row, dict):
                continue

            q = _normalize_rarity(row.get("Rarity"))
            if not q:
                continue

            if type_a == "Armor":
                line = _build_quality_line(english, q, row)
            else:
                line = _build_weapon_quality_line(q, row)

            if line:
                quality_lines.append(line)


        base_model["qualities"] = ";\n  ".join(quality_lines)

        # Ensure top rarity/sell are not used for variants
        base_model["rarity"] = ""
        base_model["sell"] = ""

        # Clear single-item equipment fields for merged variants
        base_model["durability"] = ""
        base_model["health"] = ""
        base_model["defense"] = ""
        base_model["shield"] = ""
        base_model["equip_effect"] = ""
        base_model["attack"] = ""
        base_model["magazine"] = ""


        block = render_item_infobox(base_model, include_heading=False)
        if block:
            header = f"## {display_name} ({base_id})\n"
            blocks.append((display_name, header + block))

    blocks.sort(key=lambda x: x[0].casefold())
    return blocks


def build_all_item_infoboxes_text() -> str:
    """
    Returns the full mass-list text (concatenated blocks). No file IO.
    """
    blocks = build_all_item_infobox_blocks()
    return "".join(block for _, block in blocks)
