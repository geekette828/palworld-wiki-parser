from typing import Dict, Any


def extract_datatable_rows(data: Any, *, source: str = "") -> Dict[str, dict]:
    """
    Normalize Unreal Engine DataTable / CompositeDataTable JSON exports.

    Supports:
    - { ..., "Rows": {...} }
    - [ { ..., "Rows": {...} } ]

    Returns:
        Dict[str, dict]: the Rows mapping

    Raises:
        ValueError: if Rows cannot be found
    """

    # List-wrapped DataTable (most common export quirk)
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict) and isinstance(entry.get("Rows"), dict):
                data = entry
                break
        else:
            raise ValueError(
                f"{source} JSON list did not contain a DataTable object with 'Rows'"
            )

    if not isinstance(data, dict):
        raise ValueError(
            f"{source} JSON must be an object or list containing a DataTable object"
        )

    rows = data.get("Rows")

    if not isinstance(rows, dict):
        keys = ", ".join(data.keys())
        raise ValueError(
            f"{source} JSON missing 'Rows'. Top-level keys: {keys}"
        )

    return rows
