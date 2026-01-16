
def normalize_name(value: str, name_map: dict) -> str:
    if not value:
        return ""
    value = str(value).strip()
    return name_map.get(value, value)
