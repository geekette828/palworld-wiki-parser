import sys


def force_utf8_stdout() -> None:
    """
    Force UTF-8 encoding for stdout/stderr on Windows consoles.

    This prevents UnicodeEncodeError when printing emoji or other
    non-cp1252 characters, especially when output is captured
    or piped through subprocess.
    """
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
