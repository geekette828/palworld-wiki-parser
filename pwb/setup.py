#!/usr/bin/env python3
"""Dependency manifest for the vendored Pywikibot tree.

Pywikibot's :mod:`pywikibot.scripts.wrapper` calls ``check_modules()``, which
imports ``script_deps`` and ``dependencies`` from a ``setup.py`` sitting at the
root of the Pywikibot tree. Upstream ships that file as part of its packaging;
this project vendors only the runtime package, so the module is provided here
to keep the launcher working.

This is deliberately not an installable setup script -- the vendored copy is
used in place, never built or installed. It only declares what ``check_modules``
needs to verify.
"""
from __future__ import annotations


# Mandatory runtime requirements of the vendored Pywikibot.
# ``mwparserfromhell`` is the default markup parser; ``wikitextparser`` is
# accepted as an alternative by pywikibot.textlib, but only one is required.
dependencies = [
    'mwparserfromhell>=0.5.2',
    'packaging',
    'requests>=2.31.0',
]

# Per-script extra requirements, keyed by script filename. None of the scripts
# used by this project pull in dependencies beyond the mandatory set above.
script_deps: dict[str, list[str]] = {}
