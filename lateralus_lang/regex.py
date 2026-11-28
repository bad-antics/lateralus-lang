"""
LATERALUS Standard Library — regex
Python implementation of stdlib/regex.ltl
Regular expression matching and text extraction.
"""
from __future__ import annotations
import re as _re

def regex_match(pattern: str, text: str) -> dict:
    m = _re.search(pattern, text)
    if not m:
        return {"matched": False, "groups": [], "start": -1, "end": -1, "named_groups": {}}
    return {
        "matched": True,
        "groups": list(m.groups()),
        "start": m.start(),
        "end": m.end(),
        "named_groups": m.groupdict(),
    }

def regex_match_all(pattern: str, text: str) -> list[dict]:
    matches = []
    for m in _re.finditer(pattern, text):
        matches.append({
            "matched": True,
            "groups": list(m.groups()),
            "start": m.start(),
            "end": m.end(),
            "named_groups": m.groupdict(),
        })
    return matches

def regex_replace(pattern: str, text: str, replacement: str) -> str:
    return _re.sub(pattern, replacement, text, count=1)

def regex_replace_all(pattern: str, text: str, replacement: str) -> str:
    return _re.sub(pattern, replacement, text)

def regex_split(pattern: str, text: str) -> list[str]:
    return _re.split(pattern, text)

def match(pattern: str, text: str) -> dict:
    return regex_match(pattern, text)

def match_all(pattern: str, text: str) -> list[dict]:
    return regex_match_all(pattern, text)

def is_match(pattern: str, text: str) -> bool:
    return bool(_re.search(pattern, text))

def find_first(pattern: str, text: str) -> str:
    m = _re.search(pattern, text)
    return text[m.start():m.end()] if m else ""

def find_all(pattern: str, text: str) -> list[str]:
    return [text[m.start():m.end()] for m in _re.finditer(pattern, text)]

def replace(pattern: str, text: str, replacement: str) -> str:
    return regex_replace(pattern, text, replacement)

def replace_all(pattern: str, text: str, replacement: str) -> str:
    return regex_replace_all(pattern, text, replacement)

def split(pattern: str, text: str) -> list[str]:
    return regex_split(pattern, text)

def groups(pattern: str, text: str) -> list[str]:
    m = _re.search(pattern, text)
    return list(m.groups()) if m else []

def named_groups(pattern: str, text: str) -> dict[str, str]:
    m = _re.search(pattern, text)
    return m.groupdict() if m else {}

def is_email(text: str) -> bool:
    return bool(_re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", text))

def is_url(text: str) -> bool:
    return bool(_re.match(r"^https?://[\w.-]+(:[0-9]+)?(/[\w./-]*)?$", text))

def is_ipv4(text: str) -> bool:
    return bool(_re.match(r"^(\d{1,3}\.){3}\d{1,3}$", text))

def is_hex(text: str) -> bool:
    return bool(_re.match(r"^(0x)?[0-9a-fA-F]+$", text))

def is_integer(text: str) -> bool:
    return bool(_re.match(r"^-?[0-9]+$", text))

def is_float(text: str) -> bool:
    return bool(_re.match(r"^-?[0-9]+\.?[0-9]*([eE][+-]?[0-9]+)?$", text))

def is_identifier(text: str) -> bool:
    return bool(_re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", text))

def escape(text: str) -> str:
    return _re.escape(text)
