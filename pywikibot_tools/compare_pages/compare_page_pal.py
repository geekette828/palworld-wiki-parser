import os
import sys
import re
import json
import pywikibot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config import constants  # type: ignore
from pywikibot import pagegenerators
from typing import List, Optional, Tuple, Dict
from utils.console_utils import force_utf8_stdout  # type: ignore
from utils.english_text_utils import EnglishText  # type: ignore

from builders.pal_infobox import (  # type: ignore
    load_rows as pal_infobox_load_rows,
    build_waza_master_index,
    build_pal_infobox_model_by_id,
    build_pal_order as build_pal_order_infobox,
)
from exports.export_pal_infoboxes import render_pal_infobox  # type: ignore

from builders.pal_drops import (  # type: ignore
    load_json as pal_drops_load_json,
    index_drop_rows_by_character_id,
    build_pal_drops_model_by_id,
    build_pal_order as build_pal_order_drops,
)
from exports.export_pal_drops import render_pal_drops  # type: ignore

from builders.pal_breeding import (  # type: ignore
    build_pal_breeding_model_by_id,
    build_pal_order as build_pal_order_breeding,
)
from exports.export_pal_breeding import render_pal_breeding  # type: ignore

from utils.compare_utils import (  # type: ignore
    is_blank,
    normalize_title,
    normalize_skip_keys,
    extract_first_template_block,
    replace_span,
    parse_template_params,
    compare_param_dicts,
    patch_template_params_in_place,
)

force_utf8_stdout()

compare_output_file = os.path.join(constants.OUTPUT_DIRECTORY, "Pywikibot", "Compare_Pal_Pages.txt")

DRY_RUN = True

CHECK_INFOBOX = True
CHECK_DROPS = True
CHECK_BREEDING = True

TEST_RUN = False
TEST_PAGES = [
    "Blazamut", "Fuddler", "Lifmunk", "Fuack", "Foxcicle", "Frostallion", "Lovander", "Tanzee", "Vaelet",
    "Lamball", "Chikipi", "Jolthog", "Mammorest", "Gobfin", "Dazemu", "Bushi Noct", "Azurmane",
]

SKIP_INFOBOX_PARAMS = [
    "pal_gear",
    "partner_skill_icon",
]

SKIP_BREEDING_PARAMS = [
    "uniqueCombos",
]


def _write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _normalize_alias_param(params: Dict[str, str], primary: str, alias: str) -> Dict[str, str]:
    primary_k = primary.strip()
    alias_k = alias.strip()

    v_primary = (params.get(primary_k) or "").strip()
    v_alias = (params.get(alias_k) or "").strip()

    if v_primary == "" and v_alias != "":
        params[primary_k] = v_alias
    elif v_alias == "" and v_primary != "":
        params[alias_k] = v_primary

    return params


def _build_pal_name_to_id_map(en: EnglishText) -> Dict[str, str]:
    """
    Build a (normalized title -> base pal id) map from the EN pal name table.

    Keys in EN file include:
      PAL_NAME_<id>
      PAL_<id>
    """
    out: Dict[str, str] = {}

    try:
        table = en._get_table(constants.EN_PAL_NAME_FILE)  # type: ignore[attr-defined]
    except Exception:
        return out

    def _extract_text(entry: object) -> str:
        if entry is None:
            return ""
        if isinstance(entry, str):
            return entry.strip()
        if isinstance(entry, dict):
            td = entry.get("TextData")
            if isinstance(td, dict):
                s = td.get("LocalizedString") or td.get("SourceString") or ""
                return str(s).strip()
            s = entry.get("LocalizedString") or entry.get("SourceString") or ""
            return str(s).strip()
        return ""

    for key, row in (table or {}).items():
        if not isinstance(key, str):
            continue

        k = key.strip()
        pal_id = ""
        if k.startswith("PAL_NAME_"):
            pal_id = k[len("PAL_NAME_") :].strip()
        elif k.startswith("PAL_"):
            pal_id = k[len("PAL_") :].strip()
        else:
            continue

        if not pal_id:
            continue

        name = _extract_text(row)
        if not name:
            continue

        norm = normalize_title(name).casefold()
        if norm and norm not in out:
            out[norm] = pal_id

    return out


def _resolve_pal_id_from_title(title: str, pal_name_to_id: Dict[str, str]) -> str:
    norm = normalize_title(title).casefold()
    return pal_name_to_id.get(norm, "")


def _page_generator(site: pywikibot.Site):
    template_page = pywikibot.Page(site, "Template:Pal")

    for p in template_page.embeddedin(namespaces=[0]):
        try:
            if p.isRedirectPage():
                continue
        except Exception:
            pass

        yield p


def _compare_and_patch_page(
    *,
    title: str,
    page_text: str,
    pal_id: str,
    en: EnglishText,
    infobox_ctx: dict,
    drops_ctx: dict,
    breeding_ctx: dict,
) -> Tuple[str, List[str], List[str]]:
    diffs: List[str] = []
    warnings: List[str] = []

    new_text = page_text

    if CHECK_INFOBOX:
        wiki_block, s, e = extract_first_template_block(new_text, "Pal")
        if wiki_block is None or s is None or e is None:
            warnings.append("No {{Pal}} template found on page.")
        else:
            expected_model = build_pal_infobox_model_by_id(
                pal_id,
                rows=infobox_ctx["param_rows"],
                waza_by_pal_id=infobox_ctx["waza_by_pal_id"],
                en=en,
                pal_activate_rows=infobox_ctx["pal_activate_rows"],
                partner_skill_name_rows=infobox_ctx["partner_skill_name_rows"],
            )

            expected_block = render_pal_infobox(expected_model, include_header=False)

            exp_t, _, _ = extract_first_template_block(expected_block, "Pal")
            if exp_t is None:
                warnings.append("No canonical {{Pal}} template could be generated from data.")
            else:
                wiki_params = parse_template_params(wiki_block, allow_multiline_keys=set())
                expected_params = parse_template_params(exp_t, allow_multiline_keys=set())

                skip_infobox = normalize_skip_keys(SKIP_INFOBOX_PARAMS)

                param_mismatches = compare_param_dicts(
                    expected_params,
                    wiki_params,
                    skip_keys=skip_infobox,
                )

                if param_mismatches:
                    diffs.extend(param_mismatches)

                    patched_block, _patch_mismatches = patch_template_params_in_place(
                        template_text=wiki_block,
                        expected_params=expected_params,
                        skip_keys=skip_infobox,
                        allow_multiline_keys=set(),
                        add_missing_params=False,
                    )

                    new_text = replace_span(new_text, s, e, patched_block)

    if CHECK_DROPS:
        wiki_block, s, e = extract_first_template_block(new_text, "Item Drop")
        if wiki_block is None or s is None or e is None:
            warnings.append("No {{Item Drop}} template found on page.")
        else:
            drops_model = build_pal_drops_model_by_id(
                pal_id,
                drops_by_character_id=drops_ctx["drops_by_character_id"],
                en=en,
            )
            expected_block = render_pal_drops(drops_model)

            exp_t, _, _ = extract_first_template_block(expected_block, "Item Drop")
            if exp_t is None:
                warnings.append("No canonical {{Item Drop}} template could be generated from data.")
            else:
                wiki_params = parse_template_params(wiki_block, allow_multiline_keys=set())
                expected_params = parse_template_params(exp_t, allow_multiline_keys=set())

                wiki_params = _normalize_alias_param(wiki_params, "palName", "target_name")
                expected_params = _normalize_alias_param(expected_params, "palName", "target_name")

                skip_keys = normalize_skip_keys(["target_name"])

                param_mismatches = compare_param_dicts(
                    expected_params,
                    wiki_params,
                    skip_keys=skip_keys,
                )

                if param_mismatches:
                    diffs.extend([
                        f"- drops.{m[2:]}" if m.startswith("- ") else f"- drops.{m}"
                        for m in param_mismatches
                    ])

                    patched_block, _patch_mismatches = patch_template_params_in_place(
                        template_text=wiki_block,
                        expected_params=expected_params,
                        skip_keys=skip_keys,
                        allow_multiline_keys=set(),
                        add_missing_params=False,
                    )

                    new_text = replace_span(new_text, s, e, patched_block)

    if CHECK_BREEDING:
        wiki_block, s, e = extract_first_template_block(new_text, "Breeding")
        if wiki_block is None or s is None or e is None:
            warnings.append("No {{Breeding}} template found on page.")
        else:
            breeding_model = build_pal_breeding_model_by_id(
                pal_id,
                rows=breeding_ctx["param_rows"],
                en=en,
            )
            expected_block = render_pal_breeding(breeding_model, include_header=False)

            exp_t, _, _ = extract_first_template_block(expected_block, "Breeding")
            if exp_t is None:
                warnings.append("No canonical {{Breeding}} template could be generated from data.")
            else:
                wiki_params = parse_template_params(wiki_block, allow_multiline_keys=set())
                expected_params = parse_template_params(exp_t, allow_multiline_keys=set())

                skip_breeding = normalize_skip_keys(SKIP_BREEDING_PARAMS)

                param_mismatches = compare_param_dicts(
                    expected_params,
                    wiki_params,
                    skip_keys=skip_breeding,
                )

                if param_mismatches:
                    diffs.extend([
                        f"- breeding.{m[2:]}" if m.startswith("- ") else f"- breeding.{m}"
                        for m in param_mismatches
                    ])

                    patched_block, _patch_mismatches = patch_template_params_in_place(
                        template_text=wiki_block,
                        expected_params=expected_params,
                        skip_keys=skip_breeding,
                        allow_multiline_keys=set(),
                        add_missing_params=False,
                    )

                    new_text = replace_span(new_text, s, e, patched_block)

    return new_text, diffs, warnings


def _build_infobox_context(en: EnglishText) -> dict:
    param_rows = pal_infobox_load_rows(
        os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json"),
        source="DT_PalMonsterParameter",
    )
    waza_rows = pal_infobox_load_rows(
        os.path.join(constants.INPUT_DIRECTORY, "Waza", "DT_WazaMasterLevel.json"),
        source="DT_WazaMasterLevel",
    )

    pal_activate_rows = pal_infobox_load_rows(
        constants.EN_PAL_ACTIVATE_FILE,
        source="DT_PalFirstActivatedInfoText",
    )
    partner_skill_name_rows = pal_infobox_load_rows(
        constants.EN_SKILL_NAME_FILE,
        source="DT_SkillNameText_Common",
    )

    waza_by_pal_id = build_waza_master_index(waza_rows)

    return {
        "param_rows": param_rows,
        "waza_by_pal_id": waza_by_pal_id,
        "pal_activate_rows": pal_activate_rows,
        "partner_skill_name_rows": partner_skill_name_rows,
        "pal_order": build_pal_order_infobox(param_rows),
    }


def _build_drops_context() -> dict:
    param_data = pal_drops_load_json(
        os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json")
    )
    drop_data = pal_drops_load_json(
        os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalDropItem.json")
    )

    from utils.json_datatable_utils import extract_datatable_rows  # type: ignore

    param_rows = extract_datatable_rows(param_data, source="DT_PalMonsterParameter")
    drop_rows = extract_datatable_rows(drop_data, source="DT_PalDropItem")

    drops_by_character_id = index_drop_rows_by_character_id(drop_rows)

    return {
        "param_rows": param_rows,
        "drops_by_character_id": drops_by_character_id,
        "pal_order": build_pal_order_drops(param_rows),
    }


def _build_breeding_context(en: EnglishText) -> dict:
    with open(os.path.join(constants.INPUT_DIRECTORY, "Character", "DT_PalMonsterParameter.json"), "r", encoding="utf-8") as f:
        param_data = json.load(f)

    from utils.json_datatable_utils import extract_datatable_rows  # type: ignore
    param_rows = extract_datatable_rows(param_data, source="DT_PalMonsterParameter")

    return {
        "param_rows": param_rows,
        "pal_order": build_pal_order_breeding(param_rows),
    }


def main() -> None:
    site = pywikibot.Site()
    site.login()

    en = EnglishText()
    pal_name_to_id = _build_pal_name_to_id_map(en)

    infobox_ctx = _build_infobox_context(en)
    drops_ctx = _build_drops_context()
    breeding_ctx = _build_breeding_context(en)

    diffs_out: List[str] = []
    warnings_out: List[str] = []
    changed_pages: List[str] = []

    pages = list(pagegenerators.PreloadingGenerator(_page_generator(site), groupsize=50))

    if TEST_RUN and TEST_PAGES:
        wanted = {normalize_title(t).casefold() for t in TEST_PAGES if t.strip()}
        pages = [p for p in pages if normalize_title(p.title()).casefold() in wanted]

    total = len(pages)
    print(f"🔍 Found {total} pages embedding Template:Pal")

    for idx, page in enumerate(pages, start=1):
        title = page.title()
        try:
            text = page.get()
        except Exception as e:
            warnings_out.append(f"## {title}\nFailed to read page: {e}\n")
            continue

        pal_id = _resolve_pal_id_from_title(title, pal_name_to_id)
        if not pal_id:
            warnings_out.append(f"## {title}\nCould not resolve pal_id from page title. Skipping.\n")
            continue

        new_text, diffs, warns = _compare_and_patch_page(
            title=title,
            page_text=text,
            pal_id=pal_id,
            en=en,
            infobox_ctx=infobox_ctx,
            drops_ctx=drops_ctx,
            breeding_ctx=breeding_ctx,
        )

        if warns:
            warnings_out.append(f"## {title}\n" + "\n".join([f"- {w}" for w in warns]) + "\n")

        if diffs:
            diffs_out.append(f"- {title}")
            for d in diffs:
                diffs_out.append(f"  {d}")
            diffs_out.append("")
            changed_pages.append(title)

        if not DRY_RUN and diffs:
            if new_text.strip() == text.strip():
                continue

            page.text = new_text
            page.save(summary="Update pal templates from data", minor=False)
            print(f"📝 Updated: {title} ({idx}/{total})")
        else:
            if idx % 25 == 0 or idx == total:
                print(f"🔄 Scanned {idx}/{total}")

    if DRY_RUN:
        parts: List[str] = []

        parts.append("# Pal Page Compare Output\n")
        parts.append(f"DRY_RUN: {DRY_RUN}\n")
        parts.append(f"CHECK_INFOBOX: {CHECK_INFOBOX}\n")
        parts.append(f"CHECK_DROPS: {CHECK_DROPS}\n")
        parts.append(f"CHECK_BREEDING: {CHECK_BREEDING}\n")
        parts.append("")

        parts.append("# Parameter Mismatches\n")
        if diffs_out:
            parts.extend(diffs_out)
        else:
            parts.append("(none)")
        parts.append("")

        parts.append("# Warnings\n")
        if warnings_out:
            parts.extend(warnings_out)
        else:
            parts.append("(none)")
        parts.append("")

        _write_text(compare_output_file, "\n".join(parts).rstrip() + "\n")
        print(f"✅ Wrote diff report: {compare_output_file}")


if __name__ == "__main__":
    main()
