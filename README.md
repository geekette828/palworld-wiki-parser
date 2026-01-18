Collection of Parser Items for the Palworld wiki found at: https://palworld.wiki.gg/ <br>
Reads the data, and outputs files into a format useable by the wiki. Uses pywikibot to auto create pages where applicable.

# File Structure
```
Palworld Parser/
├── _output/                                → Generated output files (wiki-formatted text, previews, logs)
├── _input/                                 → Raw data extracted from the Palworld data-mine
│
├── config/
│   ├── constants.py.sample                 → Paths & configuration template
│   └── name_map.py                         → Canonical normalization maps 
│
├── builders/                               → Canonical builders
│   ├── active_skill_infobox.py
│   ├── passive_skill_infobox.py
│   ├── pal_infobox.py
│   ├── pal_breeding.py
│   ├── pal_drops.py
│   └── pal_page.py
│
├── exports/                                → Mass-export scripts (call builders, write files)
│   ├── export_active_skill_infoboxes.py    → Outputs all Active Skill infoboxes
│   ├── export_passive_skill_infoboxes.py   → Outputs all Passive Skill infoboxes
│   ├── export_pal_infoboxes.py             → Outputs all Pal infoboxes
│   ├── export_pal_breeding.py              → Outputs all Pal breeding data
│   └── export_pal_drops.py                 → Outputs all Pal drop data
│
├── pwb/                                    → Pywikibot engine (palworld.wiki.gg)
│   ├── pwb.py
│   ├── pywikibot/
│   ├── scripts/
│   ├── families/
│   │   └── palworld_family.py
│   ├── user-config.py                      → Wiki credentials (local only)
│   └── user-password.py                    → Wiki credentials (local only)
│
├── pywikibot_tools/
│   ├── page_audit_tools/                   → Wiki audits (find missing pages)
│   │   ├── active_skill_page_audit.py
│   │   ├── item_page_audit.py
│   │   ├── pal_page_audit.py
│   │   └── passive_skill_page_audit.py
│   │
│   ├── create_pages/                       → Page creation scripts
│   │   ├── create_page_active_skill.py
│   │   ├── create_page_item.py
│   │   ├── create_page_pal.py
│   │   └── create_page_passive_skill.py
│   │
│   └── page_compare_tools/                 → Page comparison & fix scripts (future)
│
├── utils/
│   ├── console_utils.py
│   ├── english_text_utils.py
│   ├── json_datatable_utils.py
│   └── name_utils.py
│
├── .gitignore
├── pwb.ps1                                 → Recommended launcher for Pywikibot scripts
└── README.md
```

# Using the Parser
## Asset Directory Structure
### Data Tables
```
DataTable/
├── Arena/
├── BaseCamp/
├── Character/
│   ├── DT_PalDropItem.json                 → Raw Drop Data
│   └── DT_PalMonsterParameter.json         → Raw Pal Data
├── CharacterCreation/
├── CharacterTeamMission/
├── Common/
├── Debug/
├── Dungeon/
├── Environment/
├── Exp/
├── Fishing/
├── Friendship/
├── HelpGuide/
├── Incident/
├── Invader/
├── Item/
│   ├── DT_ItemDataTable.json               → Raw Item Data
│   └── DT_ItemRecipeDataTable              → Raw Item Recipe Data
├── ItemShop/
├── Lab/
├── MapObject/
├── NPCtalk/
├── NoteData/
├── Option/
├── PalShop/
├── PartnerSkill/
├── PassiveSkill/
│   └── DT_PassiveSkill_Main.json           → Raw Passive Skill Data
├── PickingGame/
├── Player/
├── Quest/
├── Randomizer/
├── Skin/
├── Sound/
├── Spawner/
├── Technology/
├── Text/
├── Tutorial/
├── UI/
├── Waza/
│   ├── DT_WazaDataTable.json               → Raw Active Skill Data
│   └── DT_WazaMasterLevel.json             → Raw Pal Active Skill Learnset Data
├── WorldMapAreaData/
├── WorldMapUIData/
└── WorldSecurity/
```
Copy all of the file folders in `DataTable` and paste into `_input/PATCHNUMBER/` (INPUT_DIRECTORY). 

### Localization Files
```
L10N/
├── de/
├── en/                                     → English Localization Files
├── es/
├── es-MX/
├── fr/
├── id/
├── it/
├── ko/
├── pl/
├── pt-BR/
├── ru/
├── th/
├── tr/
├── vi/
├── zh-Hans/
└── zh-Hant/
```
Copy the `en` file folder and paste into `_input/PATCHNUMBER/` (INPUT_DIRECTORY).