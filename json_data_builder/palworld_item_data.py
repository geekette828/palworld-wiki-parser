# This script builds up a json data file for each item.

import json
from pathlib import Path
from typing import Any, Dict, List


from palworld_data_load import (
    UnrealObject,
    l10n_localization_importer,
    load_datatable_json_tree,
)
from palworld_text_util import (
    build_text_table,
    get_string,
)
# Not dealing with configs and path inheritance
#from config.name_map import RARITY_NAME_MAP

# Define root input dir
root_input_dir=r"_input/v1.0.1"
blueprint_dir = root_input_dir+r"/Blueprint"
mega_dict = load_datatable_json_tree(root_input_dir+r"/DataTable", AsUEObj=True)

# Import localization
lionlocal = l10n_localization_importer(root_input_dir+r"/L10N")

# build alltext table.
alltext = build_text_table(lionlocal["en"])

RARITY_NAME_MAP = {
    0: "Common",
    1: "Uncommon",
    2: "Rare",
    3: "Epic",
    4: "Legendary",

    "RARITY_COMMON": "Common",
    "RARITY_UNCOMMON": "Uncommon",
    "RARITY_RARE": "Rare",
    "RARITY_EPIC": "Epic",
    "RARITY_LEGENDARY": "Legendary",
}

def _resolve_passive_skill_list(alltext, row: UnrealObject) -> str:
    ids = [
        row.PassiveSkillName,
        row.PassiveSkillName2,
        row.PassiveSkillName3,
        row.PassiveSkillName4,
    ]

    names = []
    for pid in ids:
        if not pid or pid.lower() == "none":
            continue
        names.append(get_string(alltext, "PASSIVE", pid))

    return names


def assign_valid(
    inputdict: UnrealObject, outputdict: Dict[str, Any], sourcename: str, newname: str
):
    """Add the field if it isn't nullable."""
    if sourcename in inputdict:
        if inputdict.get(sourcename):
            outputdict[newname] = inputdict.get(sourcename)


def _weapon_subtype(type_b_leaf: str) -> str:
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
        # if (
        #     (" Pickaxe" in display_name)
        #     or (" Axe" in display_name)
        #     or ("Sphere Launcher" in display_name)
        # ):
        #     return "Tool"
        return "Melee"

    return ""


def _armor_subtype(type_b_leaf: str) -> str:
    if type_b_leaf == "ArmorBody":
        return "Body Armor"
    if type_b_leaf == "ArmorHead":
        return "Head Armor"
    if type_b_leaf == "Shield":
        return "Shield"
    return ""


def _build_consume_effect(
    key: str,
    value_object: UnrealObject,
    food_effects: Dict[str, UnrealObject],
    talent_up_items: Dict[str, UnrealObject],
    gain_status_points: Dict[str, UnrealObject],
    fishing_bait: Dict[str, UnrealObject],
) -> str:
    """Attempt to build the consume effect"""
    parts: List[str] = []

    for idx in (1, 2, 3):
        effect_id = value_object.get(f"GrantEffect{idx}Id")
        effect_time = value_object.get(f"GrantEffect{idx}Time")

        if effect_id and effect_id != "0":
            if effect_time and effect_time != "0":
                parts.append(f"{effect_id} ({effect_time}s)")
            else:
                parts.append(effect_id)
    skillname = value_object.WazaID.split("::")[-1]
    if skillname != "None":
        # Add a new skill?
        # TODO: Add if needed
        pass
        # parts.append(f"{effecttype} {'+'+ str(effectvalue) if effectvalue else ""} ({effect_time}s)")
    if key in food_effects:
        food_effect = food_effects[key]
        effect_time = food_effect["EffectTime"]
        for idx in (1, 2):
            effecttype = food_effect.get(f"EffectType{idx}").split("::")[-1]
            effectvalue = food_effect.get(f"EffectValue{idx}")
            if effecttype != "None":
                parts.append(
                    f"{effecttype} {'+' + str(effectvalue) if effectvalue else ''} ({effect_time}s)"
                )
    if key in talent_up_items:
        food_effect = talent_up_items[key]
        effecttype = food_effect.get("TalentType").split("::")[-1]
        effectvalue = food_effect.get("addValue")
        if effecttype != "None":
            parts.append(
                f"{effecttype} {'+' + str(effectvalue) if effectvalue else ''}"
            )
    if key in gain_status_points:
        status_point_change = gain_status_points[key]
        mapping = {
            "MaxHP": "Health",
            "MaxSP": "Stamina",
            "Power": "Attack",
            "WorkSpeed": "Work Speed",
            "MaxInventoryWeight": "Weight",
        }
        for k, name in mapping.items():
            if status_point_change[k]:
                parts.append(f"{name} {'+' + str(status_point_change[k])}")
    if key in fishing_bait:
        pass

    return ", ".join(parts)


def create_recipe(key: str, value: UnrealObject, recipes: Dict[str, UnrealObject]):
    newrecipe = {}
    if key in recipes:
        print("has recipie", key)

        recipe = recipes[key]
        work_amount = recipe.WorkAmount
        required_blueprint = recipe.UnlockItemID
        prod_count = recipe.Product_Count

        materials = []
        for i in (1, 2, 3, 4, 5):
            matid = recipe[f"Material{i}_Id"]
            matcount = recipe[f"Material{i}_Count"]
            print(matid)
            if matid != "None" and matcount > 0:
                name = get_string(alltext, "ITEM_NAME", matid)
                if name and name != "en Text":
                    materials.append(f"{name}*{matcount}")
                else:
                    print(f"{matid}, {name}")
                    input("Invalid Item detected!")

        craft_exp = recipe.CraftExpRate

        newrecipe = {
            "materials": materials,
            "work_amount": work_amount,
            "production_count": prod_count,
            "craft_exp_rate": craft_exp,
        }
        if required_blueprint != "None":
            newrecipe["required_schematic"] = get_string(
                alltext, "ITEM_NAME", required_blueprint
            )

    return newrecipe


def handle_item_types(typea, typeb):
    '''Estimate the filter type.'''
    # Estimate filter type.
    filter_types = [
        "Weapons",
        "Armors",
        "Accessories",
        "Gliders",
        "Spheres",
        "Ammo",
        "Ingredients",
        "Food",
        "Wood",
        "Stone",
        "Pal Materials",
        "Ores",
        "Pal Eggs",
        "Production Goods",
        "Ingots",
        "Other Materials",
        "Schematics",
        "Skill Fruits",
        "Enhancement Items",
        "Other Consumables",
        "Key Items",
    ]
    common_itemtype_keypre = "COMMON_ITEMTYPE_A"
    typev = get_string(alltext, common_itemtype_keypre, typea)
    print(typev, typea, typeb)
    filter_type = ""
    wiki_type = ""
    wiki_subtype = ""
    # There's probably a better way to do this,
    # But I needed something readable for the time being.
    if typev == "Key Items":
        filter_type = "Key Items"
        return "Key Items", "Key Item", "NA"
    if typea == "Ammo":
        filter_type = "Ammo"
        wiki_type = "Ammo"
        wiki_subtype = "Ammo"
    if typea == "Weapon":
        filter_type = "Weapons"
        wiki_type = "Weapon"
        wiki_subtype = _weapon_subtype(typeb)
    if typea == "SpecialWeapon":
        filter_type = "Spheres"
        wiki_type = "Sphere"
        wiki_subtype = "Sphere"
    if typea == "Armor":
        filter_type = "Armors"
        wiki_type = "Armor"
        wiki_subtype = _armor_subtype(typeb)
    if typea == "Food":
        wiki_type = "Consumable"
        wiki_subtype = "Ingredient"
        filter_type = "Ingredients"
        print(typeb)
        if "FoodDish" in typeb:
            filter_type = "Food"
            wiki_subtype = "Food"
    if typea == "Glider":
        wiki_type = "Glider"
        filter_type = "Gliders"
        wiki_subtype = "Glider"
    if typea == "Material":
        wiki_type = "Material"
        if typeb == "Money":
            wiki_subtype = "Currency"
            filter_type = "Other Materials"
        if typeb == "MaterialIngot":
            wiki_subtype = "Ingot"
            filter_type = "Ingots"
        if typeb == "MaterialProccessing":
            wiki_subtype = "Produced Good"
            filter_type = "Production Goods"
        if typeb == "MaterialOre":
            wiki_subtype = "Ore"
            filter_type = "Ores"
        if typeb == "MaterialWood":
            wiki_subtype = "Wood"
            filter_type = "Wood"
        if typeb == "MaterialStone":
            wiki_subtype = "Stone"
            filter_type = "Stone"
        if typeb == "Drug":
            wiki_subtype = "Resource"
            filter_type = "Other Materials"
        if typeb == "MaterialMonster":
            wiki_subtype = "Pal Item"
            filter_type = "Pal Materials"
        if typeb == "MaterialPalEgg":
            wiki_subtype = "Egg"
            filter_type = "Pal Eggs"
        if typeb == "MaterialJewelry":
            wiki_subtype = "Other"
            filter_type = "Other Materials"
    if typea == "Accessory":
        filter_type = "Accessories"
        wiki_type = "Accessory"
        if typeb == "Accessory":
            wiki_subtype = "Accessory"
    if typea == "CaptureItemModifier":
        filter_type = "Accessories"
        wiki_type = "Accessory"
        if typeb == "CaptureItemModifier":
            wiki_subtype = "Sphere Module"
    if typea == "Blueprint":
        filter_type = "Schematics"
        wiki_type = "Schematics"
        wiki_subtype = "Schematics"
    if typea == "Consume":
        wiki_type = "Consumable"
        if typeb == "ConsumeFishingBait":
            wiki_subtype = "Fishing Bait"
            filter_type = "Other Consumables"
        if typeb == "Medicine":
            wiki_subtype = "Medicine"
            filter_type = "Other Consumables"
        if typeb == "Drug":
            wiki_subtype = "Medicine"
            filter_type = "Other Consumables"
        if typeb == "ConsumeGainStatusPoints":
            wiki_subtype = "Medicine"
            filter_type = "Enhancement Items"
        if typeb == "ConsumePalRevive":
            wiki_subtype = "Medicine"
            filter_type = "Other Consumables"
        if typeb == "ConsumePalGainExp":
            wiki_subtype = "Enhancement Item"
            filter_type = "Enhancement Items"
        if typeb == "ConsumePalTalentUp":
            wiki_subtype = "Enhancement Item"
            filter_type = "Enhancement Items"
        if typeb == "ConsumePassiveSkillChange":
            wiki_subtype = "Enhancement Item"
            filter_type = "Enhancement Items"
        if typeb == "ConsumePalWorkSuitabilityUp":
            wiki_subtype = "Enhancement Item"
            filter_type = "Enhancement Items"
        if typeb == "ConsumePalGainFriendshipPoint":
            wiki_subtype = "Enhancement Item"
            filter_type = "Enhancement Items"
        if typeb == "ConsumePalAwakening":
            wiki_subtype = "Enhancement Item"
            filter_type = "Enhancement Items"
        if typeb == "ConsumePalRankUp":
            wiki_subtype = "Enhancement Item"
            filter_type = "Enhancement Items"
        if typeb == "ConsumePalLevelUp":
            wiki_subtype = "Enhancement Item"
            filter_type = "Enhancement Items"
        if typeb == "ConsumeTechnologyBook":
            wiki_subtype = "Enhancement Item"
            filter_type = "Enhancement Items"
        if typeb == "ConsumeAncientTechnologyBook":
            wiki_subtype = "Enhancement Item"
            filter_type = "Enhancement Items"
        if typeb == "ConsumeWazaMachine":
            wiki_subtype = "Skill Fruit"
            filter_type = "Skill Fruits"
        if typeb == "ConsumeOther":
            wiki_subtype = "Other"
            filter_type = "Other Consumables"
        if typeb == "ConsumeTreasureMap":
            wiki_subtype = "Other"
            filter_type = "Other Consumables"
        if typeb == "ConsumeWorldTreeHolyWater":
            wiki_subtype = "Other"
            filter_type = "Other Consumables"
        if typeb == "ReturnToBaseCamp":
            wiki_subtype = "Other"
            filter_type = "Other Consumables"
    if not filter_type or not wiki_type or not wiki_subtype:
        print(f"{typea} with {typeb} NEEDS NEW TYPE CLASSIFICATION!")
        input()
    return filter_type, wiki_type, wiki_subtype


def build_full_item_data_json():
    items = mega_dict["Item"]["DT_ItemDataTable"][0]
    food_effects = mega_dict["Item"]["DT_StatusEffectFood"][0]
    talent_up_items = mega_dict["Item"]["DT_TalentUpItem"][0]
    gain_status_points = mega_dict["Item"]["DT_GainStatusPointsItem"][0]
    fishing_bait = mega_dict["Item"]["DT_FishingBaitItem"][0]
    gain_work_suitability = mega_dict["Item"]["DT_GainWorkSuitabilityRankItem"][0]

    recipes = mega_dict["Item"]["DT_ItemRecipeDataTable"][0]
    complete_item_json = {}
    for key, value in items.items():
        value_object = value
        # print(v.keys())
        # print(v['TypeA'])
        # Get the itemtypes
        typename = value_object.TypeA.split("::")[-1]
        typenameb = value_object.TypeB.split("::")[-1]

        keypre = "COMMON_ITEMTYPE_A"
        type = get_string(alltext, keypre, typename)

        if value_object.bLegalInGame is False:
            continue

        # Name and description
        name = get_string(alltext, "ITEM_NAME", key)
        desc = get_string(alltext, "ITEM_DESC", key) or ""
        if value_object.OverrideName != "None":
            name = get_string(alltext, "", value_object.OverrideName)

        if value_object.OverrideDescription != "None":
            print("overriding description...")
            print(name, desc, "target", value_object.OverrideDescription)
            desc = get_string(alltext, "", value_object.OverrideDescription.strip())
        if desc == None:
            print(f"at {key} ({name}), this item has no valid description!")
            # input()
            continue
        print(name, desc.replace("\r\n", " "))
        if (
            name is not None
            and desc is not None
            and name != "en Text"
            and desc != "en Text"
        ):
            filter_type, wiki_type, wiki_subtype = handle_item_types(
                typename, typenameb
            )
            if key.startswith("SkillUnlock_"):
                if wiki_type == "Key Item":
                    wiki_subtype = "Pal Gear"

        else:
            continue
        item_output_dict = {
            "name": name,
            "description": desc,
            "type": type,
            "wiki_type": wiki_type,
            "subtype": wiki_subtype if wiki_subtype else None,
            "filter_type": filter_type,
            "othertypea": typename,
            "othertypeb": typenameb if typenameb else None,
            "rank": value_object["Rank"],
            "weight": value_object["Weight"],
            "rarity": RARITY_NAME_MAP.get(int(value_object.Rarity), "Common"),
            "sell": value_object["Price"],
            "sort_id": value_object.SortId,
            # "key":key
        }

        keys = [
            # core
            "description",
            "type",
            "subtype",
            "rarity",
            "sell",
            "weight",
            "technology",
            # equipment
            "qualities",
            "durability",
            "health",
            "defense",
            "attack",
            "magazine",
            "shield",
            "equip_effect",
            # consumable
            "nutrition",
            "san",
            "corruption",
            "consumeEffect",
        ]

        equipment_fields = {}
        assign_valid(value_object, equipment_fields, "Durability", "durability")

        assign_valid(value_object, equipment_fields, "PhysicalAttackValue", "attack")

        assign_valid(value_object, equipment_fields, "MagazineSize", "magazine")
        assign_valid(value_object, equipment_fields, "PhysicalDefenseValue", "defense")
        assign_valid(value_object, equipment_fields, "HPValue", "health")
        assign_valid(value_object, equipment_fields, "MagazineSize", "magazine")
        assign_valid(value_object, equipment_fields, "ShieldValue", "shield")

        allpassiveskills = _resolve_passive_skill_list(alltext, value_object)
        if allpassiveskills:
            equipment_fields["equip_effect"] = allpassiveskills

        consumable_fields = {}
        # Consumable
        assign_valid(value_object, consumable_fields, "RestoreSatiety", "nutrition")
        assign_valid(value_object, consumable_fields, "RestoreSanity", "san")
        assign_valid(value_object, consumable_fields, "CorruptionFactor", "corruption")

        consume_effect = _build_consume_effect(
            key,
            value_object,
            food_effects,
            talent_up_items,
            gain_status_points,
            fishing_bait,
        )
        if consume_effect:
            consumable_fields["consumeEffect"] = consume_effect

        if equipment_fields:
            item_output_dict["equipment"] = equipment_fields
        if consumable_fields:
            item_output_dict["consumable"] = consumable_fields

        recipe = create_recipe(key, value_object, recipes)

        if recipe:
            item_output_dict["recipe"] = recipe
        # item_output_dict["key"] = key
        # item_output_dict['nutrition']
        if (
            name is not None
            and desc is not None
            and name != "en Text"
            and desc != "en Text"
        ):
            if name not in complete_item_json:
                complete_item_json[name] = {}
            complete_item_json[name][
                RARITY_NAME_MAP.get(int(value_object["Rarity"]), "Common")
            ] = item_output_dict

    final_item_json = {}

    for name, rarities in complete_item_json.items():
        rarity_names = list(rarities.keys())
        first = rarities[rarity_names[0]]

        result = {}

        # Preserve the original field order
        for field in first:
            value = first[field]

            # Field must exist in every rarity
            if not all(field in rarities[r] for r in rarity_names[1:]):
                continue

            # Field must have the same value in every rarity
            if all(rarities[r][field] == value for r in rarity_names[1:]):
                result[field] = value

        # Build variants in the original order as well
        variants = {}
        for rarity in rarity_names:
            variant = {}
            for field, value in rarities[rarity].items():
                if field not in result:
                    variant[field] = value
            variants[rarity] = variant

        if len(rarity_names) > 1:
            result["variants"] = variants

        final_item_json[name] = result
        if "variants" in result:
            keys = list(result["variants"].keys())[0]
            final_item_json[name]["sort_id"] = result["variants"][keys]["sort_id"]

    # Export to _output
    export_dir = Path("./_output")
    export_dir.mkdir(exist_ok=True)

    with open(export_dir / "item_data.json", "w", encoding="utf-8") as f:
        json.dump(final_item_json, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    build_full_item_data_json()
