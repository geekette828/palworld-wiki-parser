"""
Reads export settings (archive directory, mappings file, output version)
from pal_data_export.conf, then runs PalUE4Exporter.exe once per content
prefix, writing each export into a version-tagged output directory.
"""

import configparser
import os
import subprocess
import sys


# location of the exporter executable, relative to this script's folder.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DOTNET_DIR = os.path.join(_SCRIPT_DIR, "bin")
_EXE_PATH = os.path.join(_DOTNET_DIR, "PalUE4Exporter.exe")

CONFIG_FILE = "pal_data_export.conf"

# prefixes of content to export, in order.
PREFIXES = [
    "Pal/Content/Pal/Blueprint",
    "Pal/Content/Pal/DataTable",
    "Pal/Content/Pal/DataAsset",
    "Pal/Content/L10N/",
    "Pal/Content/Pal/Texture",
]


def load_config(path: str = CONFIG_FILE) -> configparser.SectionProxy:
    """Load pal_data_export.conf and return its [export] section.

    Raises:
        FileNotFoundError: If the config file can't be found/read.
    """
    config = configparser.ConfigParser()
    if not config.read(path):
        raise FileNotFoundError(f"Could not read config file: {path}")
    return config["export"]


def export(
    archive_dir: str,
    mappings_file: str,
    output_dir: str,
    prefix: str,
    debug: bool = False,
) -> int:
    """Run PalUE4Exporter.exe to export all files that have a specific content prefix

    Args:
        archive_dir: Path to the game archive/pak directory.
        mappings_file: Path to the UE mappings (.usmap) file.
        output_dir: Directory to write exported assets to.
        prefix: Content path prefix to export  (e.g. "Pal/Content/Pal/Blueprint").
        debug: If True, pass --debug to the exporter for verbose output.

    Returns:
        The exporter's exit code (always 0 here, since a non-zero code
        causes a RuntimeError to be raised instead).

    Raises:
        RuntimeError: If the exporter process exits with a non-zero code.
    """
    cmd = [
        _EXE_PATH,
        "--archive", archive_dir,
        "--mappings", mappings_file,
        "--output", output_dir,
        "--prefix", prefix,
    ]
    if debug:
        cmd.append("--debug")

    print(f"Exporting prefix: {prefix}")
    result = subprocess.run(cmd, check=False)

    if result.returncode != 0:
        raise RuntimeError(
            f"PalUE4Exporter failed with exit code {result.returncode} "
            f"(prefix={prefix!r})"
        )

    return result.returncode


def main():
    export_config = load_config()
    archive_dir = export_config["archive_dir"]
    mappings_file = export_config["mappings_file"]
    version = export_config["version"]

    output_dir = f"_input/{version}"
    print(f"Exporter binary: {_EXE_PATH}")
    print(f"Output directory: {output_dir}")

    for prefix in PREFIXES:
        export(
            archive_dir=archive_dir,
            mappings_file=mappings_file,
            output_dir=output_dir,
            prefix=prefix,
            debug=True,
        )
        print(f"Done: {prefix}")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)