#!/usr/bin/env bash
# Launcher for the vendored Pywikibot (Linux / macOS).
# Resolves paths relative to this script so the repo works from any location.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYWIKIBOT_DIR="$here/pwb"

if command -v python3 >/dev/null 2>&1; then
    python_bin=python3
else
    python_bin=python
fi

exec "$python_bin" "$here/pwb/pwb.py" "$@"
