# stdlib/semver.py
import re

# Strict SemVer 2.0.0 regex pattern ensuring exactly 3 core numeric components
SEMVER_REGEX = re.compile(
    r'^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)'
    r'(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
    r'(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
)

def is_valid(version_str: str) -> bool:
    """
    Validates whether a given string is a valid Semantic Version (SemVer 2.0.0).
    Rejects strings with a fourth numeric core component (e.g., 1.2.3.4).
    """
    if not isinstance(version_str, str):
        return False
    
    # Quick check: if there are 4 or more dot-separated numeric parts at the start,
    # reject immediately to avoid incorrect matching or edge cases.
    parts = version_str.split('+')[0].split('-')[0].split('.')
    if len(parts) > 3 and all(p.isdigit() for p in parts[:4]):
        return False

    return bool(SEMVER_REGEX.match(version_str))