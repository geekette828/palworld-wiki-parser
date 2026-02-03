from typing import Optional

TYPE_SUMMARIES = {
    "Ammo": (
        "Ammo is used by ranged weapons such as bows, crossbows, firearms, and specialized launchers. "
        "Different ammo types determine the damage dealt, elemental effects applied, and which weapons they are compatible with. "
        "Some ammo inflicts additional effects—such as elemental damage or status buildup—while others simply enhance raw damage output. "
        "Most ammunition can be crafted at workbenches or purchased from merchants, making proper ammo selection an important part of combat preparation."
    ),
    "Armor": (
        "Armor is equipment worn to reduce damage taken and provide defensive bonuses. "
        "Different armor pieces offer varying levels of protection and may include additional effects or stat modifiers. "
        "Armor effectiveness is determined by its base stats, rarity, and upgrade level. "
        "Armor can be obtained through crafting, merchants, drops, or rewards and is used to improve survivability in combat."
    ),
    "Implant": (
        "Implants are modules used to modify or grant passive skills to Pals. "
        "They are used at a Pal Surgery Table—a structure unlocked through technology and built in the player's base—to add new passive abilities or replace existing ones on a Pal. "
        "Implants provide various bonuses such as stat increases, work or movement enhancements, or utility effects."
    ),
    "Schematic": (
        "Schematics are items that unlock or upgrade crafting recipes. "
        "Possessing a schematic allows the associated item to be crafted at the appropriate workbench. "
        "Higher-tier schematics typically enable enhanced versions of items with improved stats or modified crafting requirements. "
        "Schematics are obtained through various in-game sources, including merchants, rewards, and combat-related drops."
    ),
    "Sphere": (
        "Pal Spheres are items used to capture Pals. "
        "When thrown at a weakened Pal, a Pal Sphere attempts to contain it, with success determined by the sphere's tier and the Pal's condition. "
        "Higher-tier Pal Spheres improve capture success rates. Pal Spheres are obtained through crafting, merchants, or rewards and are consumed on use."
    ),
    "Weapon": (
        "Weapons are items used to deal damage to enemies. "
        "They include melee and ranged types, each with distinct attack behaviors, damage values, and usage requirements. "
        "Weapon effectiveness is influenced by factors such as base stats, durability, upgrade level, and compatible ammunition or effects. "
        "Weapons can be obtained through crafting, merchants, drops, or rewards, and are a core component of combat."
    ),
}

SUBTYPE_SUMMARIES = {
    "Food": (
        "Food items are consumables typically crafted from ingredients. They provide greater "
        "restorative effects or bonuses than their individual components and are used to sustain the "
        "player or Pals during gameplay. Food is primarily obtained through crafting and is consumed "
        "on use."
    ),
    "Ingredient": (
        "Ingredients are basic items used primarily in crafting and cooking recipes. "
        "They are commonly combined to create food or other consumable items with enhanced effects. "
        "Ingredients may also be used in various production or processing recipes and are obtained through gathering, farming, drops, or purchases."
    ),
    "Pal Gear": (
        "Pal Gear refers to a special category of items designed specifically for individual [[Pals]]. When unlocked, Pal Gear enables or enhances a Pal's unique [[Partner Skills|partner skill]], often changing how that Pal behaves in combat, exploration, or support roles. Some Pal Gear provides healing or support effects for the player. Pal Gear is unlocked through the [[Technology]] tree, typically after capturing the associated Pal, and must be crafted at a [[Pal Gear Workbench]] using materials such as leather, fiber, ingots, organs, and [[Paldium Fragment]]s."
        "<br><br>Pal Gear cannot be transferred between different Pal species, as each item is uniquely tied to a specific Pal and its corresponding partner skill."
    ),
    "Skill Fruit": (
        "Skill Fruits are consumable items that permanently teach a specific Skill to a Pal when used. Each Skill Fruit grants one unique ability, allowing players to customize a Pal's moveset beyond its natural skill pool. "
        "Skill Fruits are typically obtained through exploration, merchants, or special rewards, making them a valuable resource for building specialized combat or utility Pals. "
        "/n"
        "Once a skill fruit has been obtained, they can be placed in a [[Skillfruit Orchard]] to grow additional fruits of the same element."
    ),
    "Support Whistle": (
        "Support Whistles are passive accessory items that provide continuous stat bonuses to a Pal fighting alongside the player while equipped. Rather than issuing commands or requiring activation, these whistles automatically enhance a Pal's combat effectiveness, "
        "most commonly by increasing damage for a specific elemental type or by boosting overall attack or defense. Support Whistles come in multiple tiers, with higher versions granting stronger bonuses, and only apply while worn in an accessory slot. "
        "They are typically obtained from treasure chests, bosses, vendors, or other loot sources, and are intended to let the player subtly optimize Pal performance without changing gameplay flow or requiring direct interaction. "
    ),
}

def get_item_page_blurb(item_type: Optional[str], item_subtype: Optional[str]) -> Optional[str]:
    if item_subtype and item_subtype in SUBTYPE_SUMMARIES:
        return SUBTYPE_SUMMARIES[item_subtype]

    if item_type and item_type in TYPE_SUMMARIES:
        return TYPE_SUMMARIES[item_type]

    return None
