import os
import re
import json

from config import constants
from config.name_map import ELEMENT_NAME_MAP
from typing import Any, Dict, Iterable, List, Optional, Dict
from utils.json_datatable_utils import extract_datatable_rows

_NUM_TAG_RE = re.compile(r"<Num(?:Blue|Red)_\d+>")
_SELF_CLOSING_TAG_RE = re.compile(r"<[^>]+/>")
_GENERIC_TAG_RE = re.compile(r"<[^>]+>")
_EFFECTVALUE_TOKEN_RE = re.compile(r"\{EffectValue(\d+)\}")
_UICOMMON_TAG_RE = re.compile(
    r"<\s*uiCommon\s+id=\|\s*(?P<key>[^|]+)\s*\|/\s*>",
    re.IGNORECASE,
)

def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_text(entry: Any) -> str:
    if entry is None:
        return ""

    if isinstance(entry, str):
        return entry.strip()

    if isinstance(entry, dict):
        text_data = entry.get("TextData")
        if isinstance(text_data, dict):
            s = text_data.get("LocalizedString") or text_data.get("SourceString") or ""
            return str(s).strip()

        s = entry.get("LocalizedString") or entry.get("SourceString") or ""
        return str(s).strip()

    return ""


class EnglishText:
    def __init__(self) -> None:
        # file_path -> { key -> row_dict }
        self._cache = {}

    def _get_table(self, file_path: str):
        if file_path in self._cache:
            return self._cache[file_path]

        raw = _load_json(file_path)
        rows = extract_datatable_rows(raw, source=os.path.basename(file_path)) or {}

        self._cache[file_path] = rows
        return rows

    def get_raw(self, file_path: str, key: str) -> str:
        rows = self._get_table(file_path)
        row = rows.get(key)
        if row is None:
            return ""
        return _extract_text(row)

    def get(self, file_path: str, key: str) -> str:
        rows = self._get_table(file_path)
        row = rows.get(key)
        if row is None:
            return ""
        return clean_english_text(_extract_text(row), row)

    def get_first(self, file_path: str, keys: list) -> str:
        for k in keys:
            v = self.get(file_path, k)
            if v:
                return v
        return ""
    
    def get_first_casefold(self, file_path: str, keys: list) -> str:
        # Exact pass first (fast path)
        v = self.get_first(file_path, keys)
        if v:
            return v

        table = self._get_table(file_path)
        want_folded = {str(k).casefold() for k in keys if k}

        for key, row in table.items():
            if isinstance(key, str) and key.casefold() in want_folded:
                return clean_english_text(_extract_text(row), row)

        return ""

    def get_pal_name(self, pal_id: str) -> str:
        pal_id = str(pal_id).strip()
        if not pal_id:
            return ""

        # First try the normal exact keys
        v = self.get_first(constants.EN_PAL_NAME_FILE, [
            f"PAL_NAME_{pal_id}",
            f"PAL_{pal_id}",
        ])
        if v:
            return v

        # Case-insensitive fallback for known casing mismatches (e.g., WindChimes vs Windchimes)
        table = self._get_table(constants.EN_PAL_NAME_FILE)

        want_keys = [
            f"PAL_NAME_{pal_id}",
            f"PAL_{pal_id}",
        ]
        want_folded = {k.casefold() for k in want_keys}

        for key, row in table.items():
            if isinstance(key, str) and key.casefold() in want_folded:
                return clean_english_text(_extract_text(row), row)

        return ""

    def get_item_name(self, item_id: str) -> str:
        item_id = str(item_id).strip()
        return self.get_first(constants.EN_ITEM_NAME_FILE, [
            f"ITEM_NAME_{item_id}",
            f"ITEM_{item_id}",
        ])

    def get_passive_name(self, passive_id: str) -> str:
        return self.get(constants.EN_SKILL_NAME_FILE, f"PASSIVE_{passive_id}")

    def get_active_skill_name(self, skill_id: str) -> str:
        skill_id = str(skill_id or "").strip()
        if not skill_id:
            return ""

        return self.get_first_casefold(constants.EN_SKILL_NAME_FILE, [
            f"ACTION_SKILL_{skill_id}",
            f"COOP_{skill_id}",
            f"ACTIVE_{skill_id}",
        ])

    def get_skill_desc(self, key: str) -> str:
        return self.get(constants.EN_SKILL_DESC_FILE, key)


    def audit_keys(
        self,
        *,
        name: str,
        file_path: str,
        expected_keys: Iterable[str],
        include_empty: bool = True,
    ) -> List[str]:
        """
        Audit a localization file for missing (or empty) keys.

        Returns a list of missing keys.
        Writes a debug file listing missing/empty entries.
        """

        table = self._get_table(file_path)

        missing: List[str] = []
        empty: List[str] = []

        for key in expected_keys:
            if key not in table:
                missing.append(key)
            elif include_empty and not table[key]:
                empty.append(key)

        if not missing and not empty:
            return []

        os.makedirs(constants.DEBUG_DIRECTORY, exist_ok=True)

        output_path = os.path.join(
            constants.DEBUG_DIRECTORY,
            f"english_audit_{name}.txt"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"English localization audit: {name}\n")
            f.write(f"Source file: {file_path}\n\n")

            if missing:
                f.write("Missing keys:\n")
                for key in sorted(missing):
                    f.write(f"- {key}\n")
                f.write("\n")

            if empty:
                f.write("Keys with empty text:\n")
                for key in sorted(empty):
                    f.write(f"- {key}\n")

        return missing

def _format_effect_value_token(v: Any) -> str:
    """
    For inserting into {EffectValue#} placeholders (WITHOUT adding %).
    20.0 -> "20"
    12.5 -> "12.5"
    -10.0 -> "-10"
    """
    try:
        n = float(v)
    except (TypeError, ValueError):
        return ""

    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))

    return str(n).rstrip("0").rstrip(".")

def substitute_effectvalue_placeholders(text: str, row: Optional[Dict[str, Any]]) -> str:
    """
    Replace {EffectValue1}, {EffectValue2}, ... with row['EffectValue#'].
    If row is None, leaves placeholders unchanged.
    """
    if not text or not row:
        return str(text or "")

    def repl(m: re.Match) -> str:
        idx = m.group(1)
        key = f"EffectValue{idx}"
        return _format_effect_value_token(row.get(key))

    return _EFFECTVALUE_TOKEN_RE.sub(repl, str(text))

def strip_palworld_markup(text: str) -> str:
    """
    Remove Palworld/Unreal inline markup like:
    - <NumBlue_13> ... </> and <NumRed_13> ... </>
    - other <...> tags and <.../> tags

    Also converts <uiCommon id=|COMMON_ELEMENT_NAME_X|/> into readable element names.
    """
    s = str(text or "")

    # normalize line endings
    s = s.replace("\r", "")

    # Convert element uiCommon tokens BEFORE we strip self-closing tags.
    def _uicommon_repl(m: re.Match) -> str:
        key = (m.group("key") or "").strip()

        if key.startswith("COMMON_ELEMENT_NAME_"):
            raw = key[len("COMMON_ELEMENT_NAME_"):].strip()
            return ELEMENT_NAME_MAP.get(raw, raw)

        # Any other uiCommon token is "junk" for now
        return ""

    s = _UICOMMON_TAG_RE.sub(_uicommon_repl, s)

    # remove number color tags + their close tag
    s = _NUM_TAG_RE.sub("", s)
    s = s.replace("</>", "")

    # remove any remaining XML-ish tags
    s = _SELF_CLOSING_TAG_RE.sub("", s)
    s = _GENERIC_TAG_RE.sub("", s)

    return s.strip()

def clean_english_text(text: str, row: Optional[Dict[str, Any]] = None) -> str:
    """
    One-stop cleaner for localized strings:
    1) replaces {EffectValue#} placeholders using row values (if row provided)
    2) strips Palworld markup tags like <NumBlue_13> and </>

    Use this on any text pulled from the English DT tables.
    """
    s = substitute_effectvalue_placeholders(text, row)
    s = strip_palworld_markup(s)
    return s
