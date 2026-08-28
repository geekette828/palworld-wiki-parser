# config/partner_skill_icon_map.py
from typing import List, Tuple

# (icon_name, required_phrases, banned_phrases)
PARTNER_SKILL_ICON_RULES: List[Tuple[str, List[str], List[str]]] = [
    ("Mount",   ["can be ridden"], 
                ["flying", "travel on water", "across water"]),

    ("Flying Mount", ["Can be ridden as a flying mount"], []),
    
    ("Water Mount", ["can be ridden to travel on water"], []),
    ("Water Mount", ["can be ridden to travel quickly across water"], []),

    ("Glider", ["modifies the performance of the equipped glider"], []),

    ("Farming", ["when assigned to a Ranch"], ["can be ridden"]),
    ("Farming", ["when assigned to the ranch"], ["can be ridden"]),

    ("Drop Boost", ["pals drop more items when defeated."], []),

    ("Neutral Boost", ["While in team, increases Attack of Neutral Pals"], ["While at a base"]),
    ("Ground Boost", ["While in team, increases Attack of Ground Pals"], ["assigned to the ranch"]),
    ("Fire Boost", ["While in team, increases Attack of Fire Pals."], []),

    
    ("Heal", ["restores", "health"], []),

    ("Transport", ["carry", "transport"], []),
]

# (skill_name, required_phrases, banned_phrases)
PARTNER_SKILL_LEVEL_RULES: List[Tuple[str, List[str], List[str]]] = [
    ("ItemWeightReduction_CrudeOil_PartnerSkill_*",   
        ["decreasing the weight of crude oil"], 
        [],
        "raw"),

    ("ItemWeightReduction_Armor_PartnerSkill_*",   
        ["decreasing the weight of armor"], 
        [],
        "raw"),

    ("ItemWeightReduction_Gun_PartnerSkill_*",   
        ["decreasing the weight of weapons"], 
        [],
        "raw"),

    ("MoveSpeed_Up_GrassType_PartnerSkill_*",   
        ["increases player's movement speed", "attack type to Grass"], 
        [],
        "raw"),

    ("LifeSteal_*",   
        ["While fighting together", "grants the player and", "life steal effect"], 
        [],
        "raw"),

# Enhancing Elemental Attacks
    ("ElementBoost_Dark_PAL_PartnerSKill_*",
        ["Enhances Dark attacks while mounted"],
        [],
        "raw"),
    ("ElementBoost_Dark_PAL_PartnerSKill_*",
        ["While in team", "increases Attack of Dark Pals"],
        [],
        "percent_div5"),

    ("ElementBoost_Dragon_PAL_PartnerSKill_*",   
        ["Enhances Dragon attacks while mounted"], 
        [],
        "raw"),     
    ("ElementBoost_Dragon_PAL_PartnerSKill_*",   
        ["While in team", "increases Attack of Dragon Pals"],
        [],
        "percent_div5"),
            
    ("ElementBoost_Electricity_PAL_PartnerSKill_*",   
        ["Enhances Electric attacks while mounted"], 
        [],
        "raw"),
    ("ElementBoost_Electricity_PAL_PartnerSKill_*",   
        ["While in team", "increases Attack of Electric Pals"],
        [],
        "percent_div5"),

    ("ElementBoost_Fire_PAL_PartnerSKill_*",   
        ["Enhances Fire attacks while mounted"], 
        [],
        "raw"),
    ("ElementBoost_Fire_PAL_PartnerSKill_*",   
        ["While in team", "increases Attack of Fire Pals"],
        [],
        "percent_div5"),

    ("ElementBoost_Leaf_PAL_PartnerSKill_*",   
        ["Enhances Grass attacks while mounted"], 
        [],
        "raw"),
    ("ElementBoost_Leaf_PAL_PartnerSKill_*",   
        ["While in team", "increases Attack of Grass Pals"],
        [],
        "percent_div5"),

    ("ElementBoost_Earth_PAL_PartnerSKill_*",   
        ["Enhances Ground attacks while mounted"], 
        [],
        "raw"),
    ("ElementBoost_Earth_PAL_PartnerSKill_*",   
        ["While in team", "increases Attack of Ground Pals"],
        [],
        "percent_div5"),

    ("ElementBoost_Ice_PAL_PartnerSKill_*",   
        ["Enhances Ice attacks while mounted"], 
        [],
        "raw"),
    ("ElementBoost_Ice_PAL_PartnerSKill_*",   
        ["While in team", "increases Attack of Ice Pals"],
        [],
        "percent_div5"),

    ("ElementBoost_Normal_PAL_PartnerSKill_*",   
        ["Enhances Neutral attacks while mounted"], 
        [],
        "raw"),
    ("ElementBoost_Normal_PAL_PartnerSKill_*",   
        ["While in team", "increases Attack of Neutral Pals"],
        [],
        "percent_div5"),

    ("ElementBoost_Water_PAL_PartnerSKill_*",   
        ["Enhances Water attacks while mounted"], 
        [],
        "raw"),
    ("ElementBoost_Water_PAL_PartnerSKill_*",   
        ["While in team", "increases Attack of Water Pals"],
        [],
        "percent_div5"),

# Increase Item Drop Rate
    ("ElementAddDrop_Dark_*_PAL",   
        ["While fighting together", "Dark Pals drop more items"],
        [],
        "percent_raw"),
    ("ElementAddDrop_Dragon_*_PAL",   
        ["While fighting together", "Dragon Pals drop more items"],
        [],
        "percent_raw"),
    ("ElementAddDrop_Thunder_*_PAL",   
        ["While fighting together", "Electric Pals drop more items"],
        [],
        "percent_raw"),
    ("ElementAddDrop_Fire_*_PAL",   
        ["While fighting together", "Fire Pals drop more items"],
        [],
        "percent_raw"),
    ("ElementAddDrop_Leaf_*_PAL",   
        ["While fighting together", "Grass Pals drop more items"],
        [],
        "percent_raw"),
     ("ElementAddDrop_Earth_*_PAL",   
        ["While fighting together", "Ground Pals drop more items"],
        [],
        "percent_raw"),
     ("ElementAddDrop_Ice_*_PAL",   
        ["While fighting together", "Ice Pals drop more items"],
        [],
        "percent_raw"),
     ("ElementAddDrop_Normal_*_PAL",   
        ["While fighting together", "Neutral Pals drop more items"],
        [],
        "percent_raw"),
    ("ElementAddDrop_Aqua_*_PAL",   
        ["While fighting together", "Water Pals drop more items"],
        [],
        "percent_raw"),

# Trainer Skills
    ("TrainerLogging_up_PartnerSkill_*",   
        ["While in team", "improves efficiency of cutting trees"],
        [],
        "percent_raw"),
]

