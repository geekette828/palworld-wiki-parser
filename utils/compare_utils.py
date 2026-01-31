# utils/compare_utils.py
import re
import difflib
from typing import Dict, List, Optional, Tuple


_TEMPLATE_NAME_RE_CACHE: Dict[str, re.Pattern] = {}

_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_NUMERIC_WHOLE_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

def is_blank(v: Optional[str]) -> bool:
    return v is None or str(v).strip() == ""


def normalize_title(s: str) -> str:
    s = str(s or "").strip()
    return " ".join(s.split())


def normalize_skip_keys(keys: List[str]) -> set[str]:
    out: set[str] = set()
    for k in (keys or []):
        s = str(k or "").strip()
        if not s:
            continue
        out.add(s.casefold())
    return out

def _normalize_numeric_string(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""

    # Only touch values that are purely numeric
    if not _NUMERIC_WHOLE_RE.match(s):
        return s

    # Convert "80.0" -> "80", "0.0" -> "0"
    if "." in s:
        left, right = s.split(".", 1)
        if right.strip("0") == "":
            return left

        # Also trim trailing zeros: "1.5000" -> "1.5"
        right = right.rstrip("0")
        return left + "." + right

    return s

def get_template_name_re(template_name: str) -> re.Pattern:
    key = template_name.strip().casefold()
    if key in _TEMPLATE_NAME_RE_CACHE:
        return _TEMPLATE_NAME_RE_CACHE[key]

    # Exact template match:
    #   {{Pal|...}}
    #   {{Pal}}
    #   {{Pal
    #    |...}}
    #
    # Does NOT match:
    #   {{Pal Navigation}}
    #   {{Paldeck}}
    pat = re.compile(
        r"\{\{\s*" + re.escape(template_name.strip()) + r"\s*(?=\||\}\})",
        re.IGNORECASE,
    )

    _TEMPLATE_NAME_RE_CACHE[key] = pat
    return pat

def find_template_blocks(text: str, template_name: str) -> List[Tuple[str, int, int]]:
    out: List[Tuple[str, int, int]] = []
    if is_blank(text):
        return out

    name_re = get_template_name_re(template_name)
    for m in name_re.finditer(text):
        start = m.start()
        i = start
        depth = 0

        while i < len(text) - 1:
            two = text[i : i + 2]
            if two == "{{":
                depth += 1
                i += 2
                continue
            if two == "}}":
                depth -= 1
                i += 2
                if depth == 0:
                    end = i
                    out.append((text[start:end], start, end))
                    break
                continue
            i += 1

    return out


def extract_first_template_block(text: str, template_name: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    blocks = find_template_blocks(text, template_name)
    if not blocks:
        return None, None, None
    b, s, e = blocks[0]
    return b, s, e


def replace_span(text: str, start: int, end: int, replacement: str) -> str:
    return text[:start] + replacement + text[end:]


def normalize_for_diff(s: str) -> str:
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    s = s.strip() + "\n"
    return s


def unified_diff(*, title: str, old: str, new: str, label: str) -> str:
    old_lines = normalize_for_diff(old).splitlines(keepends=True)
    new_lines = normalize_for_diff(new).splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"{title} ({label}) - wiki",
        tofile=f"{title} ({label}) - data",
        lineterm="",
    )
    return "\n".join(diff).strip()


def strip_wikilinks(s: str) -> str:
    def repl(m: re.Match) -> str:
        target = (m.group(1) or "").strip()
        label = (m.group(2) or "").strip()
        return label if label else target

    return _WIKILINK_RE.sub(repl, s or "")


def strip_trailing_wiki_comment(s: str) -> str:
    return re.sub(r"\s*<!--.*?-->\s*$", "", s or "", flags=re.DOTALL).strip()

def template_has_meaningful_data(
    template_text: str,
    *,
    ignore_keys: Optional[set[str]] = None,
) -> bool:
    """
    True if a template contains any non-blank param value.

    - Counts any |key = value where value is not blank after trimming and stripping trailing <!-- ... -->.
    - `ignore_keys` lets you ignore params like 'product' or maintenance fields.
    """
    if is_blank(template_text):
        return False

    ignore = {k.casefold() for k in (ignore_keys or set()) if str(k).strip()}

    params = parse_template_params(template_text, allow_multiline_keys=set())

    for k, v in params.items():
        if not k:
            continue
        if k.casefold() in ignore:
            continue
        if not is_blank(strip_trailing_wiki_comment(v)):
            return True

    return False

def normalize_param_value_for_compare(v: str) -> str:
    v = (v or "").replace("\r\n", "\n").replace("\r", "\n")
    v = strip_wikilinks(v)
    v = re.sub(r"(?<=\d),(?=\d)", "", v)
    v = re.sub(r"\s+", " ", v).strip()

    v = _normalize_numeric_string(v)
    return v

def normalize_qty_list_assume_one(v: str) -> str:
    s = (v or "").strip()
    if not s:
        return ""

    parts = [p.strip() for p in s.split(";")]
    out: List[str] = []
    for p in parts:
        if not p:
            continue
        if "*" not in p:
            out.append(p + "*1")
        else:
            out.append(p)
    return "; ".join(out)


def parse_template_params(
    template_text: str,
    *,
    allow_multiline_keys: Optional[set[str]] = None,
) -> Dict[str, str]:
    params: Dict[str, str] = {}
    if is_blank(template_text):
        return params

    allow_multiline_keys = allow_multiline_keys or set()
    allow_multiline_norm = {str(k).strip().casefold() for k in allow_multiline_keys if str(k).strip()}

    text = template_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    current_key: Optional[str] = None
    current_key_norm: str = ""
    current_val_lines: List[str] = []

    # Param line: "| key = value"
    param_re = re.compile(r"^\s*\|\s*(?P<key>[^=\n|]+?)\s*=\s*(?P<val>.*)$")

    def flush() -> None:
        nonlocal current_key, current_key_norm, current_val_lines
        if not current_key:
            return

        raw_val = "\n".join(current_val_lines).strip()

        # If the template closes on the same line as the last param, strip it.
        raw_val = re.sub(r"\s*\}\}\s*$", "", raw_val).rstrip()

        if current_key_norm not in allow_multiline_norm:
            first_line = raw_val.split("\n", 1)[0].strip()
            params[current_key] = strip_trailing_wiki_comment(first_line)
        else:
            params[current_key] = raw_val.strip()

        current_key = None
        current_key_norm = ""
        current_val_lines = []

    for line in lines:
        # End of template
        if re.match(r"^\s*\}\}\s*$", line):
            flush()
            break

        m = param_re.match(line)
        if m:
            # New param starts — flush previous param first
            flush()

            key_raw = (m.group("key") or "").strip()
            val_raw = (m.group("val") or "")

            if not key_raw:
                continue

            current_key = key_raw
            current_key_norm = key_raw.casefold()
            current_val_lines = [val_raw]
            continue

        # Continuation line (only relevant for multiline keys)
        if current_key and current_key_norm in allow_multiline_norm:
            current_val_lines.append(line)

    # Flush if template ended without a clean "}}"
    flush()
    return params

def extract_param_value_single_line(template_text: str, param_name: str) -> str:
    if is_blank(template_text):
        return ""

    text = template_text.replace("\r\n", "\n").replace("\r", "\n")

    pat = re.compile(
        r"^[ \t]*\|\s*" + re.escape(param_name) + r"\s*=\s*([^\n]*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    m = pat.search(text)
    if not m:
        return ""

    val = (m.group(1) or "").strip()
    val = re.sub(r"\s*\}\}\s*$", "", val).strip()
    val = re.sub(r"\s*<!--.*?-->\s*$", "", val).strip()
    return val


def compare_param_dicts(
    expected: Dict[str, str],
    found: Dict[str, str],
    *,
    prefix: str = "",
    skip_keys: Optional[set[str]] = None,
    qty_assume_one_suffixes: Optional[set[str]] = None,
) -> List[str]:
    mismatches: List[str] = []
    keys = set(expected.keys()) | set(found.keys())

    skip_keys = skip_keys or set()
    qty_assume_one_suffixes = qty_assume_one_suffixes or set()

    for key in sorted(keys, key=lambda x: x.casefold()):
        label = f"{prefix}{key}" if prefix else key

        if label.casefold() in skip_keys or key.casefold() in skip_keys:
            continue

        exp_raw = (expected.get(key, "") or "")
        got_raw = (found.get(key, "") or "")

        key_norm = key.casefold()
        label_norm = label.casefold()

        should_qty_assume_one = False
        for suf in qty_assume_one_suffixes:
            s = (suf or "").casefold()
            if not s:
                continue
            if key_norm.endswith(s) or label_norm.endswith(s):
                should_qty_assume_one = True
                break

        if should_qty_assume_one:
            exp = normalize_param_value_for_compare(normalize_qty_list_assume_one(exp_raw))
            got = normalize_param_value_for_compare(normalize_qty_list_assume_one(got_raw))
        else:
            exp = normalize_param_value_for_compare(exp_raw)
            got = normalize_param_value_for_compare(got_raw)

        if exp == "" and got == "":
            continue

        if exp != got:
            mismatches.append(f"- {label} Expected {repr(exp)} - Found {repr(got)}")

    return mismatches


def patch_template_params_in_place(
    *,
    template_text: str,
    expected_params: Dict[str, str],
    skip_keys: set[str],
    allow_multiline_keys: Optional[set[str]] = None,
    add_missing_params: bool = False,
) -> Tuple[str, List[str]]:
    """
    Patch a template block in-place.

    - If a param exists, update only its value region (preserving indentation and trailing inline comments).
    - If add_missing_params=True, insert params that are missing from the template.
      This supports templates like "{{Crafting Recipe}}" that have no params at all.
    """
    if is_blank(template_text) or not expected_params:
        return template_text, []

    allow_multiline = {str(k).strip().casefold() for k in (allow_multiline_keys or set()) if str(k).strip()}
    text = template_text.replace("\r\n", "\n").replace("\r", "\n")

    # Match a whole param block:
    #   | key = value
    #   (value may span multiple lines until next |other= or }} )
    pattern = re.compile(
        r"(?ims)^(?P<indent>[ \t]*)\|\s*(?P<key>[^=\n|]+?)\s*=\s*(?P<val>.*?)(?=^\s*\|\s*[^=\n|]+?\s*=|^\s*\}\}\s*$)"
    )

    matches = list(pattern.finditer(text))

    by_key: Dict[str, re.Match] = {}
    indent_guess = ""

    for m in matches:
        k_raw = (m.group("key") or "").strip()
        if not k_raw:
            continue
        by_key[k_raw.casefold()] = m
        if not indent_guess:
            indent_guess = m.group("indent") or ""

    replacements: List[Tuple[int, int, str]] = []
    mismatch_lines: List[str] = []
    insert_lines: List[str] = []

    # Determine a stable insertion order: prefer the order of expected_params
    # (dict order is stable in py3.7+), which comes from your model mapping.
    for exp_key_raw, exp_val_raw in expected_params.items():
        exp_key = (exp_key_raw or "").strip()
        if not exp_key:
            continue

        exp_key_norm = exp_key.casefold()
        if exp_key_norm in skip_keys:
            continue

        exp_val_block = str(exp_val_raw or "")
        is_multiline = exp_key_norm in allow_multiline

        m = by_key.get(exp_key_norm)

        if m is None:
            if not add_missing_params:
                continue

            # Insert missing param
            if not is_multiline:
                exp_first_line = (
                    exp_val_block.replace("\r\n", "\n").replace("\r", "\n").split("\n", 1)[0].strip()
                )
                insert_lines.append(f"{indent_guess}|{exp_key} = {exp_first_line}".rstrip())
            else:
                exp_norm = exp_val_block.replace("\r\n", "\n").replace("\r", "\n").rstrip()
                insert_lines.append(f"{indent_guess}|{exp_key} = {exp_norm}".rstrip())
            continue

        indent = m.group("indent") or ""
        wiki_key_spelling = (m.group("key") or "").strip()
        wiki_val_block = (m.group("val") or "")

        got_cmp = normalize_param_value_for_compare(wiki_val_block)
        exp_cmp = normalize_param_value_for_compare(exp_val_block)

        if got_cmp == exp_cmp:
            continue

        mismatch_lines.append(f"- {wiki_key_spelling} Expected {repr(exp_cmp)} - Found {repr(got_cmp)}")

        if not is_multiline:
            # Preserve any trailing inline comment on the first line of the existing value
            wiki_first_line = wiki_val_block.split("\n", 1)[0]

            trailing_comment = ""
            cm = re.search(r"(<!--.*?-->\s*)$", wiki_first_line, flags=re.DOTALL)
            if cm:
                trailing_comment = cm.group(1) or ""

            exp_first_line = (
                exp_val_block.replace("\r\n", "\n").replace("\r", "\n").split("\n", 1)[0].strip()
            )

            new_first_line = exp_first_line
            if trailing_comment:
                new_first_line = (new_first_line + " " + trailing_comment.strip()).rstrip()

            # Preserve any additional lines captured in the existing value block (e.g. section headers like <!-- Basics -->)
            wiki_lines = wiki_val_block.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            wiki_rest = ""
            if len(wiki_lines) > 1:
                wiki_rest = "\n".join(wiki_lines[1:]).rstrip("\n")

            new_block = f"{indent}|{wiki_key_spelling} = {new_first_line}"
            if wiki_rest:
                new_block = new_block + "\n" + wiki_rest
        else:
            exp_norm = exp_val_block.replace("\r\n", "\n").replace("\r", "\n").rstrip()
            new_block = f"{indent}|{wiki_key_spelling} = {exp_norm}"

        original_block = text[m.start() : m.end()]
        suffix = "\n" if original_block.endswith("\n") else ""
        replacements.append((m.start(), m.end(), new_block + suffix))

    # Apply replacements (reverse order so indices stay valid)
    if replacements:
        replacements.sort(key=lambda t: t[0], reverse=True)
        for s, e, rep in replacements:
            text = text[:s] + rep + text[e:]

    # Insert missing params just before the final "}}"
    if add_missing_params and insert_lines:
        close_idx = text.rfind("}}")
        if close_idx != -1:
            before = text[:close_idx]
            after = text[close_idx:]

            # If template is one-liner like "{{Crafting Recipe}}", expand it
            if "\n" not in before:
                before = before.rstrip() + "\n"

            # Ensure before ends with newline
            if not before.endswith("\n"):
                before = before + "\n"

            # Insert and ensure there's exactly one newline before closing
            insertion = "\n".join(insert_lines).rstrip() + "\n"
            # Avoid double blank lines if the template already has content
            if before.endswith("\n\n"):
                before = before.rstrip("\n") + "\n"

            text = before + insertion + after.lstrip()

    return text, mismatch_lines
