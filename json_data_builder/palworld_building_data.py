# This script builds up a json data file for each building.

import json
from pathlib import Path
import re

from collections import defaultdict

from palworld_data_load import (
    get_blueprint,
    l10n_localization_importer,
    load_datatable_json_tree,
)
from palworld_text_util import (
    TextTable
)

# Define root input dir
root_input_dir=r"_input/v1.0.1"
blueprint_dir = root_input_dir+r"/Blueprint"
mega_dict = load_datatable_json_tree(root_input_dir+"/DataTable", AsUEObj=True)

# Import localization
lionlocal = l10n_localization_importer(root_input_dir+"/L10N")

# build alltext table.
alltext = TextTable(lionlocal["en"])


# print(organized.keys())
def build_pal_labor_settings(val, alltext):

    typeuidisplay = val["WorkSuitability"].split("::")[-1]

    workrank = val["WorkSuitabilityRank"]

    can_player_work = val["bPlayerWorkable"]

    can_base_camp_worker_work = val["bBaseCampWorkerWorkable"]
    minsize = val["WorkableSizeMax"].split("::")[-1]
    maxsize = val["WorkableSizeMax"].split("::")[-1]

    work_type = val["WorkType"].split("::")[-1]
    work_action_type = val["WorkActionType"].split("::")[-1]
    max_workers = val["WorkerMaxNum"]
    san_effect = val["AffectSanityValue"]
    full_stomach_effect = val["AffectFullStomachValue"]
    multiwork = []
    for i in range(1, 3):
        val[f"MultiWorkSuitability{i}"].split("::")[-1]
        mworksuit = val[f"MultiWorkSuitability{i}"].split("::")[-1]
        mworktype = val[f"MultiWorkType{i}"].split("::")[-1]
        mworkactiontype = val[f"MultiWorkActionType{i}"].split("::")[-1]
        mrank = val[f"MultiRequiredRank{i}"]
        if mworksuit != "None":
            print(val)
            print(mworksuit)
            print(mworktype)
            print(mworkactiontype)
            print(mrank)
            multiwork.append(
                {
                    "suitability": alltext.get_string(
                         "COMMON_WORK_SUITABILITY", mworksuit
                    ),
                    "work_type": alltext.get_string("COMMON_WORK_TYPE", mworktype),
                    "rank_needed": mrank,
                }
            )
            # input()
    work_settings = {
        "suitability": alltext.get_string( "COMMON_WORK_SUITABILITY", typeuidisplay),
        "rank_needed": workrank,
        "can_player_work": can_player_work,
        "can_basecamp_worker_work": can_base_camp_worker_work,
        "san_impact": san_effect,
        "full_stomach_impact": full_stomach_effect,
    }
    if minsize != "None":
        work_settings["min_pal_size"] = minsize
    if maxsize != "None":
        work_settings["max_pal_size"] = maxsize
    if work_type != "None":
        work_settings["work_type"] = alltext.get_string( "COMMON_WORK_TYPE", work_type)
        # work_settings['work_action_type']=work_action_type
    if max_workers:
        work_settings["max_workers"] = max_workers
    return work_settings


def build_farm_crop_data(mapobjectfarmcrop, cropkey):
    print(cropkey)
    cropdata = mapobjectfarmcrop[cropkey]

    growth_time = cropdata["GrowupTime"]
    crop_number = cropdata["CropItemNum"]

    planting_work = cropdata["SeedingWorkAmount"]
    watering_work = cropdata["WateringWorkAmount"]
    harvest_work = cropdata["HarvestWorkAmount"]
    cropitem = cropdata["CropItemId"]

    return {
        "crop_item": cropitem,
        "growth_time": growth_time,
        "planting_workload": planting_work,
        "watering_workload": watering_work,
        "harvest_workload": harvest_work,
        "crop_yield": crop_number,
    }


def build_full_building_data_json():
    allbuildings = mega_dict["MapObject"]["DT_BuildObjectDataTable"][0]
    mapobjects = mega_dict["MapObject"]["DT_MapObjectMasterDataTable"][0]
    mapobjectitemproduct = mega_dict["MapObject"]["DT_MapObjectItemProductDataTable"][0]
    mapobjectassigndata = mega_dict["MapObject"]["DT_MapObjectAssignData"][0]
    mapobjectfarmcrop = mega_dict["MapObject"]["DT_MapObjectFarmCrop"][0]
    items = mega_dict["Item"]["DT_ItemDataTable"][0]

    # Post processing for mapobjectassigndata
    new_rows = defaultdict(list)
    for key, value in mapobjectassigndata.items():
        new_key = re.sub(r"_\d+$", "", key)
        new_rows[new_key].append(value)

    mapobjectassigndata = dict(new_rows)

    full_building_data_json = {}

    for key, value_object in allbuildings.items():

        typename = value_object["TypeA"].split("::")[-1]
        typenameb = value_object["TypeB"].split("::")[-1]

        typeuidisplay = value_object["TypeUIDisplay"].split("::")[-1]
        k = value_object["MapObjectId"]
        if k == "Campfire":
            k = "CampFire"
        if k in mapobjects:
            mapobject = mapobjects[k]
        else:
            mapobject = mapobjects[key]

        cata = alltext.get_string( "CATEGORY_TYPE_A", typename)
        catb = alltext.get_string( "CATEGORY_TYPE_B", typenameb)

        catui = alltext.get_string( "CATEGORY_TYPE_UI", typeuidisplay)
        print(k, typename, typenameb, typeuidisplay, cata, catb, catui)

        name = alltext.get_string( "MAPOBJECT_NAME", k)
        desc = alltext.get_string( "BUILDOBJECT_DESC", k)

        output_building_data = {
            "name": name,
            "description": desc,
            "hp": mapobject["Hp"],
            "defense": mapobject["Defense"],
            "pvp_hp": mapobject["Hp_PVP"],
            "pvp_defense": mapobject["Defense_PVP"],
            "deterioration": mapobject["DeteriorationDamage"],
            "burn_extinguish_workload": mapobject["ExtinguishBurnWorkAmount"],
            "category": cata,
            "category2": catui if catui else None,
            "rank": value_object["Rank"],
            "sort_id": value_object["SortId"],
            "build_cap": value_object["BuildCapacity"],
            "workload_to_build": value_object["RequiredBuildWorkAmount"],
        }
        if mapobject["Hp"] <= 0:
            continue

        palpower = value_object["RequiredEnergyType"].split("::")[-1]
        if palpower != "None":
            print(palpower)
            if palpower != "Electric":
                input()
            output_building_data["energy"] = palpower
            output_building_data["energy_cost"] = value_object["ConsumeEnergySpeed"]

        build_cost = {}
        for i in range(1, 5):
            matid = value_object[f"Material{i}_Id"]

            matcount = value_object[f"Material{i}_Count"]
            if matid != "None":
                if matid == "stone":
                    matid = "Stone"
                if matid == "cement":
                    matid = "Cement"
                if matid in items:
                    item_name = alltext.get_string( "ITEM_NAME", matid)

                    item_desc = alltext.get_string( "ITEM_DESC", matid)
                    item_amount = matcount
                    build_cost[i] = {"item": item_name, "amount": item_amount}
                    pass
                else:
                    print(matid, "Not in items")
                    input()
        if build_cost:
            output_building_data["build_cost"] = build_cost
        output_building_data["needs_blueprint"] = None
        if value_object["BlueprintItemID"] != "None":
            print(value_object["BlueprintItemID"])
            item_name = alltext.get_string(
                "ITEM_NAME", value_object["BlueprintItemID"]
            )
            output_building_data["needs_blueprint"] = item_name
        if value_object["OverrideDescMsgID"] != "None":
            input()
        output_building_data["neighbor_threshold"] = value_object[
            "InstallNeighborThreshold"
        ]

        if value_object["InstallNeighborThreshold"]:
            print(value_object["InstallNeighborThreshold"])

        baselonly = value_object["bIsInstallOnlyOnBase"]
        indooronly = value_object["bIsInstallOnlyInDoor"]
        hubonly = value_object["bIsInstallOnlyHubAround"]

        restrictions = ""
        if baselonly:
            restrictions += "{{*}} Can only be built indoors.\n"
        if indooronly:
            restrictions += "{{*}} Can only be built inside doors.\n"
        if hubonly:
            restrictions += "{{*}} Can only be built around a base.\n"

        if value_object["InstallMaxNumInBaseCamp"]:
            restrictions += (
                "{{*}}"
                + f"Can only build {value_object.InstallMaxNumInBaseCamp} in a base.\n"
            )

        if value_object["bIsProhibitedInRaidBossArea"]:
            restrictions += "{{*}}" + f"Cannot be built in a Raid Boss Area.\n"
        if value_object["MaxBuildCountInRaidBossArea"]:
            restrictions += (
                "{{*}}"
                + f"Can only build {value_object.MaxBuildCountInRaidBossArea} in a Raid Boss Area.\n"
            )

        output_building_data["paintable"] = value_object.bIsPaintable
        output_building_data["restrictions"] = restrictions

        output_building_data["exp_build_rate"] = value_object["BuildExpRate"]
        pallabor = []
        if key in mapobjectassigndata:
            for val in mapobjectassigndata[key]:
                inputv = build_pal_labor_settings(val, alltext)
                if inputv["suitability"] is not None:
                    pallabor.append(inputv)

        output_building_data["labors"] = pallabor

        if key in mapobjectitemproduct:
            productval = mapobjectitemproduct[key]
            item_product = alltext.get_string( "ITEM_NAME", productval["Product_Id"])
            required_work = productval["RequiredWorkAmount"]
            output_building_data["item_production"] = {
                "item_name": item_product,
                "required_work": required_work,
            }

        if key in mapobjectfarmcrop:
            print(key, mapobjectfarmcrop)
            # input()

        # Get more data from blueprints.
        nameblueprint = mapobject.BlueprintClassName
        targetclassbp = mapobject.BlueprintClassSoft
        assetpathclass = targetclassbp["AssetPathName"].rsplit(".", 1)[-1]
        blueprint = get_blueprint(nameblueprint, root_dir=blueprint_dir)
        if blueprint:
            print(f"Found Blueprint '{nameblueprint}' with {assetpathclass}")
            crop_data = []
            craftable = {}
            clinic = {}
            # Yeah, the blueprints are a total mess.
            for b in blueprint:
                if b.Type == assetpathclass:
                    if b.Properties.get("CropDataId"):
                        crop_data.append(
                            build_farm_crop_data(
                                mapobjectfarmcrop, b.Properties.CropDataId["Key"]
                            )
                        )

                if b.Type == "PalMapObjectItemConverterParameterComponent":
                    # Crafting Table Stuff
                    type_a = b.Properties.TargetTypesA or []
                    type_b = b.Properties.TargetTypesB or []
                    target_max_rank = b.Properties.TargetRankMax
                    work_speed_additional_rate = b.Properties.WorkSpeedAdditionalRate
                    print(type_a, type_b)
                    craftable = {
                        "craftable_item_categories_a": [
                            typev.split("::")[-1] for typev in type_a
                        ],
                        "craftable_item_categories_b": [
                            typev.split("::")[-1] for typev in type_b
                        ],
                        "craftable_item_max_rank": target_max_rank,
                        "work_speed_additional_rate": work_speed_additional_rate,
                    }
                if (
                    b.Type
                    == "PalMapObjectBaseCampPassiveEffectClinicParameterComponent"
                ):
                    clinic = {
                        "base_san_suppress_rate": b.Properties.BaseSanitySuppressRate,
                        "clinic_assigned_san_rate": b.Properties.ClinicAssignedSanityRate,
                        "base_sick_supress_rate": b.Properties.BaseSicknessSuppressRate,
                    }

            if crop_data:
                output_building_data["crop_data"] = crop_data

            if craftable:
                output_building_data["craftable_item_range"] = craftable
            if clinic:
                output_building_data["clinic"] = clinic

        if (
            name is not None
            and desc is not None
            and name != "en Text"
            and desc != "en Text"
        ):
            full_building_data_json[name] = output_building_data
        else:
            print(f"NO VALID NAME FOR {key}/{k}")
            # input()
            
    export_dir = Path("./_output")
    export_dir.mkdir(exist_ok=True)

    with open(export_dir / "building_data.json", "w", encoding="utf-8") as f:
        json.dump(full_building_data_json, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    build_full_building_data_json()
