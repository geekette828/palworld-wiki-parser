# config/partner_skill_icon_map.py
from typing import List, Tuple

# (icon_name, required_phrases, banned_phrases)
PARTNER_SKILL_ICON_RULES: List[Tuple[str, List[str], List[str]]] = [
    ("Mount",   ["can be ridden"], 
                ["flying", "travel on water", "across water"]),

    ("Flying Mount", ["Can be ridden as a flying mount"], []),
    
    ("Water Mount", ["can be ridden to travel on water"], []),
    ("Water Mount", ["can be ridden to travel quickly across water"], []),

    ("Glider", ["modifies the performance of the equipped glider"], 
                []),

    ("Weapon", ["equipped", "weapon"], []),
    ("Shield", ["shield"], []),
    ("Healer", ["restores", "heal"], []),
    ("Transport", ["carry", "transport"], []),
]
