from typing import Dict
import re


from palworld_data_load import (
    TextData,
    TextDataChild,
    l10n_localization_importer,
    load_datatable_json_tree,
)


from collections import Counter


# Localized text has inline xml tags.
# That need to be replaced.
TAG_RE = re.compile(r"<(\w+)\s+([^>]*)/>")
ATTR_RE = re.compile(r"(\w+)=\|([^|]*)\|")

TAG_HANDLERS = {
    "mapObjectName": "MAPOBJECT_NAME",
    "MapObjectName": "MAPOBJECT_NAME",
    "mapObjectname": "MAPOBJECT_NAME",
    "characterName": "PAL_NAME",
    "characterName": "PAL_NAME",
    "itemName": "ITEM_NAME",
    "activeSkillName": "ACTION_SKILL",
    "uiCommon": None,
    "img": None,
}

known_text_subs = {
    "cloth": "Cloth",
    "FIber": "Fiber",
    "cloth2": "Cloth2",
    "wood": "Wood",
    "stone": "Stone",
}


def build_text_table(mega_dict: Dict[str, TextData]) -> Dict[str, TextDataChild]:
    "Build the table of all localized text."
    alltext = {}
    for t, v in mega_dict["Text"].items():
        for stringkey, data in v[0].items():
            alltext[stringkey.lower()] = data["TextData"]
    return alltext


def buildup_text_tree(alltext: Dict[str, TextDataChild]):

    # Create a string key tree.
    # This is for debugging.
    prefix_counts = Counter()
    organized = {}
    for stringkey, data in alltext.items():
        parts = stringkey.split("_")

        for i in range(1, len(parts)):
            prefix = "_".join(parts[:i])
            prefix_counts[prefix] += 1
        d = organized
        for part in parts[:-1]:
            d = d.setdefault(part, {})

        d[parts[-1]] = {"value": data["Key"]}

    def print_tree(node, file, prefix="", path=""):
        items = list(node.items())

        for i, (key, value) in enumerate(items):
            print(key, value)
            last = i == len(items) - 1
            branch = "└── " if last else "├── "

            full_path = f"{path}_{key}" if path else key
            count = prefix_counts.get(full_path, 1)

            print(f"{prefix}{branch}{key} ({count})", file=file)

            if isinstance(value, dict):
                if "value" not in value or len(value) > 1:
                    next_prefix = prefix + ("    " if last else "│   ")
                    print_tree(value, file, next_prefix, full_path)

    with open("tree.txt", "w", encoding="utf-8") as f:
        print_tree(organized, f)


class TextTable:
    def __init__(self, mega_dict: Dict[str, TextData]):
        self.alltext = build_text_table(mega_dict)

    def replace_tags(self, text,overriders):
        def repl(match):
            tag_name = match.group(1)
            attrs = dict(ATTR_RE.findall(match.group(2)))

            if tag_name not in TAG_HANDLERS:
                print("Unknown tag:", tag_name, text)

                raise Exception()
                return match.group(0)

            target = attrs.get("id")
            if target is None:
                return match.group(0)

            # Handle image tags
            # Currently, just remove them.
            if tag_name == "img":
                return ""  # match.group(0)

            # Handle uiCommon
            if tag_name == "uiCommon":
                print("Is ui common")
                print(f"|{target}|")
                # Example:
                # <uiCommon id=|COMMON_ELEMENT_NAME_Fire| style=|Elem_Fire|/>
                replacement = self.get_string("", target,overriders)
                print(replacement)
                return replacement if replacement else match.group(0)

            # Normal string lookup
            prefix = TAG_HANDLERS[tag_name]

            replacement = self.get_string(prefix, target,overriders)

            return replacement if replacement is not None else match.group(0)

        return TAG_RE.sub(repl, text)

    def get_string(self, pre, target, overriders={}):
        if target in known_text_subs:
            target = known_text_subs[target]
        keypre = (pre + "_" + target).lower()
        if not pre:
            keypre = target.lower()
        # print(keypre)
        if keypre.lower() in overriders:
            keypre = overriders.get(keypre.lower()).lower()
        if keypre in self.alltext:
            targettext = self.alltext.get(keypre)["LocalizedString"]
            inp = self.replace_tags(targettext,overriders)
            return inp.replace("\r\n", " ")
       
            inp = self.replace_tags(targettext)


if __name__ == "__main__":
    mega_dict = load_datatable_json_tree("_input/v1.0.1/DataTable", AsUEObj=True)

    # Import localization
    lionlocal = l10n_localization_importer("_input/v1.0.1/L10N")

    # build alltext table.
    alltext = TextTable(lionlocal["en"])

    buildup_text_tree(alltext.alltext)
