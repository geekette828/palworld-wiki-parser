# Launcher for the vendored Pywikibot (Windows / PowerShell).
# Resolves paths relative to this script so the repo works from any location.
$pwbDir = Join-Path $PSScriptRoot 'pwb'
$env:PYWIKIBOT_DIR = $pwbDir
& python (Join-Path $pwbDir 'pwb.py') @args
