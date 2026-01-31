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
