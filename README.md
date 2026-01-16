Collection of Parser Items for the Palworld wiki found at: https://palworld.wiki.gg/ <br>
Putting these into output files, so we can do a compare between patches, and only update pages that need it.

# File Structure
```
Palworld Parser/
├── _output/
├── _input/
│
├── config/
│   ├── constants.py.sample
│   └── name_map.py
│
├── format_tools/
│   ├── active_skill_infobox.py
│   ├── pal_breeding.py
│   ├── pal_drops.py
│   ├── pal_infobox.py
│   └── passive_skill_infobox.py
│
├── pwb/                                    → Pywikibot engine, set up for palworld.wiki.gg
│   ├── pwb.py
│   ├── pywikibot/
│   ├── scripts/
│   ├── families/
│   │   └── palworld_family.py
│   ├── user-config.py                      → Your wiki credentials - update this
│   └── user-password.py                    → Your wiki credentials - update this
│
├── pywikibot_tools/
│   ├── page_audit_tools/
│   │   ├── active_skill_page_audit.py      → Checks the wiiki for which active skills have pages, and outputs a list of missing active skills.
│   │   ├── pal_page_audit.py               → Checks the wiiki for which pals have pages, nd outputs a list of missing pals.
│   │   └── passive_skill_page_audit.py     → Checks the wiiki for which passive skills have pages, and outputs a list of missing passives.
│   ├── create_page_active_skill.py         → Creates missing active skill pages.
│   ├── create_page_item.py                 → Creates missing item pages.
│   ├── create_page_pal.py                  → Creates missing pal pages.
│   └── create_page_passive_skill.py        → Creates missing passive skill pages.
│
├── utils/
│   ├── console_utils.py
│   ├── english_text_utils.py
│   ├── jason_datatable_utils.py
│   ├── name_utils.py
├── .gitignore
├── pwb.ps1                                 → Recommended launcher script for pywikibot stuff
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
│   └── DT_WazaMasterLevel                  → Raw Active Skill Data
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