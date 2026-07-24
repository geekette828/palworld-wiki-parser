from pathlib import Path
import json
from typing import List, TypedDict

from pydantic import BaseModel, ConfigDict, model_validator

from collections.abc import MutableMapping


class TextDataChild(TypedDict):
    Namespace: str
    Key: str
    SourceString: str
    LocalizedString: str


class TextData(TypedDict):
    TextData: TextDataChild


class UnrealObject(BaseModel, MutableMapping):
    """
    This is so I can use . instead of []
    for stuff in the json data.


    """

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def _convert_nested(cls, value):
        if isinstance(value, dict):
            return {k: cls._convert_nested(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [cls._convert_nested(v) for v in value]
        return value

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]

        extra = getattr(self, "__pydantic_extra__", None)
        if extra and name in extra:
            return extra[name]

        return None

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, key):
        delattr(self, key)

    def __iter__(self):
        return iter(self.model_dump())

    def __len__(self):
        return len(self.model_dump())

    def keys(self):
        return self.model_dump().keys()

    def values(self):
        return self.model_dump().values()

    def items(self):
        return self.model_dump().items()


class UnrealAsset(UnrealObject):
    model_config = ConfigDict(extra="allow")
    Type: str
    Name: str

    Class: str | None = None
    Flags: str | None = None
    Package: str | None = None
    Properties: UnrealObject | None = None


def load_datatable_json_tree(root_dir: str, AsUEObj=False):
    "Load ALL the DataTable json files detected from root_dir."
    root = Path(root_dir)
    result = {}

    for json_file in root.rglob("*.json"):
        relative = json_file.relative_to(root)
        parts = list(relative.parts)

        # Remove the .json extension
        parts[-1] = json_file.stem

        current = result
        for part in parts[:-1]:
            print(parts)
        current = current.setdefault(parts[0], {})

        with json_file.open("r", encoding="utf-8") as f:
            # print(json_file)
            target = json.load(f)[0]

            if target["Type"] in ["DataTable", "CompositeDataTable"]:
                if target["Name"] in current:
                    current[target["Name"]].append(target["Rows"])
                else:
                    if AsUEObj:
                        current[target["Name"]] = [
                            {
                                key: UnrealObject(**targ)
                                for key, targ in target["Rows"].items()
                            }
                        ]
                    else:
                        current[target["Name"]] = [target["Rows"]]
            else:
                print(target["Type"], target["Name"])

    return result


def l10n_localization_importer(root_dir=""):
    root = Path(root_dir)
    result = {}

    # Get top-level language folders
    language_dirs = [p for p in root.iterdir() if p.is_dir()]

    print(result.keys())
    print([p.name for p in language_dirs])

    for lang_dir in language_dirs:
        datatable_dir = lang_dir / "Pal" / "DataTable"

        if not datatable_dir.is_dir():
            continue

        print(f"Loading {datatable_dir}")

        result[lang_dir.name] = load_datatable_json_tree(datatable_dir)

    print(result.keys())
    return result


def get_blueprint(blueprint_name, root_dir="./Blueprint") -> List[UnrealAsset]:
    """Looks for a blueprint json file with the name "blueprint_name"
    in the Blueprint directory in root_dir"""
    root = Path(root_dir)

    for json_file in root.rglob("*.json"):
        if json_file.stem == blueprint_name:
            with json_file.open("r", encoding="utf-8") as f:
                inputv = json.load(f)
                new = []
                for bptype in inputv:
                    new.append(UnrealAsset(**bptype))
                return new

    return None
