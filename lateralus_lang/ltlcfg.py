"""
lateralus_lang/ltlcfg.py
LATERALUS Configuration Language (.ltlcfg)

A typed, schematized configuration language that compiles to Python dicts.
Inspired by TOML but with LATERALUS-style types, inline validation, and
computed fields.

File format example:
---
[server]
host: str = "localhost"
port: int = 8080
debug: bool = false
workers: int = 4  # must be > 0

[database]
url: str = "sqlite:///db.ltldb"
pool_size: int = 5
timeout: float = 30.0

[logging]
level: str = "INFO"  # one of: DEBUG, INFO, WARN, ERROR
output: list[str] = ["stdout", "/var/log/app.log"]

[features]
enable_reactive: bool = true
max_pipeline_depth: int = 256
---

Supports:
  - Sections ([section_name])
  - Typed fields (name: type = value)
  - Comments (# ...)
  - Multiline strings (triple-quoted: \"\"\"...\"\"\")
  - Lists ([a, b, c])
  - Nested config (dot-notation: server.host)
  - Environment variable substitution (${ENV_VAR})
  - Include directives (!include other.ltlcfg)
  - Schema validation (TypeSchema)
  - Computed fields (derived: = base * 2)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Union

# ---------------------------------------------------------------------------
# Type system for config values
# ---------------------------------------------------------------------------

class ConfigType:
    """Primitive config types."""
    STR   = "str"
    INT   = "int"
    FLOAT = "float"
    BOOL  = "bool"
    LIST  = "list"
    DICT  = "dict"
    ANY   = "any"

    @staticmethod
    def coerce(value_str: str, type_name: str) -> Any:
        """Coerce a string value to the target type."""
        type_name = type_name.strip()

        if type_name == "str":
            return value_str.strip('"\'')

        if type_name == "int":
            try:
                return int(value_str.strip())
            except ValueError:
                raise ConfigError(f"Cannot coerce {value_str!r} to int")

        if type_name == "float":
            try:
                return float(value_str.strip())
            except ValueError:
                raise ConfigError(f"Cannot coerce {value_str!r} to float")

        if type_name == "bool":
            v = value_str.strip().lower()
            if v in ("true", "yes", "on", "1"):
                return True
            if v in ("false", "no", "off", "0"):
                return False
            raise ConfigError(f"Cannot coerce {value_str!r} to bool")

        if type_name.startswith("list"):
            return _parse_list_literal(value_str)

        return value_str


class ConfigError(Exception):
    """Raised when config parsing or validation fails."""
    pass


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

@dataclass
class FieldSchema:
    """Schema for a single config field."""
    name: str
    type_name: str
    default: Any = None
    required: bool = False
    validator: Optional[Callable[[Any], bool]] = None
    description: str = ""
    choices: Optional[list] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class SectionSchema:
    """Schema for a config section."""
    name: str
    fields: dict[str, FieldSchema] = field(default_factory=dict)
    description: str = ""
    allow_extra: bool = False

    def field(self, name: str, type_name: str, default: Any = None,
              required: bool = False, description: str = "",
              choices: Optional[list] = None,
              min_value: Optional[float] = None,
              max_value: Optional[float] = None) -> "SectionSchema":
        self.fields[name] = FieldSchema(
            name=name, type_name=type_name, default=default,
            required=required, description=description,
            choices=choices, min_value=min_value, max_value=max_value,
        )
        return self


class ConfigSchema:
    """
    Full schema for a .ltlcfg file.

    Usage:
        schema = ConfigSchema()
        schema.section("server").field("host", "str", default="localhost")
        schema.section("server").field("port", "int", default=8080, min_value=1, max_value=65535)
        config = load_config("server.ltlcfg", schema)
    """

    def __init__(self) -> None:
        self._sections: dict[str, SectionSchema] = {}

    def section(self, name: str, description: str = "", allow_extra: bool = False) -> SectionSchema:
        if name not in self._sections:
            self._sections[name] = SectionSchema(name, description=description, allow_extra=allow_extra)
        return self._sections[name]

    def validate(self, config: dict) -> list[str]:
        """Validate a parsed config dict against this schema. Returns list of errors."""
        errors: list[str] = []

        for section_name, section_schema in self._sections.items():
            section_data = config.get(section_name, {})

            for field_name, field_schema in section_schema.fields.items():
                if field_name not in section_data:
                    if field_schema.required:
                        errors.append(f"[{section_name}] Required field '{field_name}' is missing")
                    continue

                value = section_data[field_name]

                # Choices validation
                if field_schema.choices is not None and value not in field_schema.choices:
                    errors.append(
                        f"[{section_name}] '{field_name}' = {value!r} is not one of {field_schema.choices}"
                    )

                # Numeric range validation
                if field_schema.min_value is not None:
                    try:
                        if float(value) < field_schema.min_value:
                            errors.append(
                                f"[{section_name}] '{field_name}' = {value} is below minimum {field_schema.min_value}"
                            )
                    except (TypeError, ValueError):
                        pass

                if field_schema.max_value is not None:
                    try:
                        if float(value) > field_schema.max_value:
                            errors.append(
                                f"[{section_name}] '{field_name}' = {value} is above maximum {field_schema.max_value}"
                            )
                    except (TypeError, ValueError):
                        pass

                # Custom validator
                if field_schema.validator is not None:
                    try:
                        if not field_schema.validator(value):
                            errors.append(f"[{section_name}] '{field_name}' failed custom validation")
                    except Exception as e:
                        errors.append(f"[{section_name}] '{field_name}' validator raised: {e}")

        return errors

    def apply_defaults(self, config: dict) -> dict:
        """Fill in missing fields with their default values."""
        result: dict = dict(config)

        for section_name, section_schema in self._sections.items():
            if section_name not in result:
                result[section_name] = {}
            for field_name, field_schema in section_schema.fields.items():
                if field_name not in result[section_name] and field_schema.default is not None:
                    result[section_name][field_name] = field_schema.default

        return result


# ---------------------------------------------------------------------------
# Config parser
# ---------------------------------------------------------------------------

_LIST_RE = re.compile(r'^\[(.*)]\s*$', re.DOTALL)
_ENV_RE  = re.compile(r'\$\{([^}]+)\}')


def _parse_list_literal(s: str) -> list:
    """Parse a list literal like [1, 2, "three", true]."""
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
    else:
        inner = s

    if not inner:
        return []

    items: list = []
    for raw_item in _split_list_items(inner):
        item = raw_item.strip()
        if item.startswith('"') or item.startswith("'"):
            items.append(item.strip('"\''))
        elif item.lower() in ("true", "yes"):
            items.append(True)
        elif item.lower() in ("false", "no"):
            items.append(False)
        elif "." in item:
            try:
                items.append(float(item))
                continue
            except ValueError:
                pass
            items.append(item)
        else:
            try:
                items.append(int(item))
            except ValueError:
                items.append(item)
    return items


def _split_list_items(s: str) -> list[str]:
    """Split comma-separated items respecting nesting and quotes."""
    items: list[str] = []
    depth = 0
    in_str = False
    str_char = ""
    buf: list[str] = []

    for c in s:
        if in_str:
            buf.append(c)
            if c == str_char:
                in_str = False
        elif c in ('"', "'"):
            in_str = True
            str_char = c
            buf.append(c)
        elif c in "[{(":
            depth += 1
            buf.append(c)
        elif c in "]})":
            depth -= 1
            buf.append(c)
        elif c == "," and depth == 0:
            items.append("".join(buf))
            buf.clear()
        else:
            buf.append(c)

    if buf:
        items.append("".join(buf))

    return items


def _substitute_env(value: str) -> str:
    """Replace ${ENV_VAR} with environment variable values."""
    def replacer(m: re.Match) -> str:
        env_name = m.group(1)
        default = ""
        if ":-" in env_name:
            env_name, default = env_name.split(":-", 1)
        return os.environ.get(env_name.strip(), default)
    return _ENV_RE.sub(replacer, value)


def _parse_value(raw: str, type_hint: Optional[str] = None) -> Any:
    """Parse a raw config value string into a Python value."""
    raw = raw.strip()

    # Environment variable substitution
    raw = _substitute_env(raw)

    # Triple-quoted strings
    if raw.startswith('"""') and raw.endswith('"""'):
        return raw[3:-3]

    # Single/double quoted strings
    if (raw.startswith('"') and raw.endswith('"')) or \
       (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]

    # Lists
    if raw.startswith("["):
        return _parse_list_literal(raw)

    # Booleans
    if raw.lower() in ("true", "yes", "on"):
        return True
    if raw.lower() in ("false", "no", "off"):
        return False

    # None
    if raw.lower() in ("null", "none", "~"):
        return None

    # Float
    if re.match(r'^-?\d+\.\d+$', raw):
        return float(raw)

    # Integer
    if re.match(r'^-?\d+$', raw):
        return int(raw)

    # Hex integer
    if re.match(r'^0x[0-9a-fA-F]+$', raw):
        return int(raw, 16)

    # Apply type coercion if hint given
    if type_hint:
        return ConfigType.coerce(raw, type_hint)

    return raw


class LtlCfgParser:
    """
    Parser for .ltlcfg files.

    Grammar:
        config     := section*
        section    := '[' NAME ']' NEWLINE field*
        field      := NAME ':' TYPE '=' value COMMENT? NEWLINE
                    | NAME '=' value COMMENT? NEWLINE
        value      := string | number | bool | list | null
        COMMENT    := '#' .*
        !include   := '!include' PATH
    """

    def __init__(self) -> None:
        self._config: dict[str, dict] = {}
        self._current_section: str = "__root__"
        self._computed: dict[str, str] = {}   # section.field -> expr

    def parse_string(self, content: str) -> dict:
        """Parse a .ltlcfg string into a nested dict."""
        lines = content.splitlines()
        i = 0

        while i < len(lines):
            raw_line = lines[i]
            i += 1

            # Strip inline comments (but not inside strings)
            line = _strip_comment(raw_line)

            # Skip blank lines
            if not line.strip():
                continue

            # Include directive
            if line.strip().startswith("!include "):
                include_path = line.strip()[9:].strip()
                included = self._load_include(include_path)
                # Merge included config
                for section, fields in included.items():
                    if section not in self._config:
                        self._config[section] = {}
                    self._config[section].update(fields)
                continue

            # Section header
            section_match = re.match(r'^\s*\[([^\]]+)\]\s*$', line)
            if section_match:
                self._current_section = section_match.group(1).strip()
                if self._current_section not in self._config:
                    self._config[self._current_section] = {}
                continue

            # Handle multiline triple-quoted strings
            if '"""' in line and line.count('"""') == 1:
                buf = [line]
                while i < len(lines) and '"""' not in lines[i]:
                    buf.append(lines[i])
                    i += 1
                if i < len(lines):
                    buf.append(lines[i])
                    i += 1
                line = "\n".join(buf)

            # Field assignment: name: type = value  or  name = value
            field_match = re.match(
                r'^\s*(\w+)\s*(?::\s*(\w+(?:\[[\w\s,]+\])?))?\s*=\s*(.*?)\s*$',
                line
            )
            if field_match:
                name = field_match.group(1)
                type_hint = field_match.group(2) or None
                raw_value = field_match.group(3)

                section = self._current_section
                if section not in self._config:
                    self._config[section] = {}

                self._config[section][name] = _parse_value(raw_value, type_hint)
                continue

        return dict(self._config)

    def _load_include(self, path: str) -> dict:
        """Load an included config file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return LtlCfgParser().parse_string(f.read())
        except FileNotFoundError:
            return {}


def _strip_comment(line: str) -> str:
    """Remove inline comment, being careful about strings."""
    in_str = False
    str_char = ""
    for i, c in enumerate(line):
        if in_str:
            if c == str_char:
                in_str = False
        elif c in ('"', "'"):
            in_str = True
            str_char = c
        elif c == "#":
            return line[:i]
    return line


# ---------------------------------------------------------------------------
# Config object (dot-access wrapper)
# ---------------------------------------------------------------------------

class Config:
    """
    A loaded .ltlcfg configuration with dot-access syntax.

    Usage:
        cfg = load_config("server.ltlcfg")
        print(cfg.server.host)       # dot access
        print(cfg["server"]["host"]) # dict access
        print(cfg.get("server.host", "localhost"))  # path access
    """

    def __init__(self, data: dict) -> None:
        self._data = data
        for section, fields in data.items():
            if isinstance(fields, dict):
                object.__setattr__(self, section, Config(fields))
            else:
                object.__setattr__(self, section, fields)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def get(self, path: str, default: Any = None) -> Any:
        """Get a value by dot-notation path, e.g. 'server.host'."""
        parts = path.split(".")
        node = self._data
        for part in parts:
            if isinstance(node, dict):
                node = node.get(part)
            elif hasattr(node, "_data"):
                node = node._data.get(part)
            else:
                return default
            if node is None:
                return default
        return node

    def to_dict(self) -> dict:
        return dict(self._data)

    def __repr__(self) -> str:
        sections = list(self._data.keys())
        return f"<Config sections={sections}>"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(path: Union[str, Path],
                schema: Optional[ConfigSchema] = None) -> Config:
    """
    Load a .ltlcfg file, optionally validating against a schema.

    Returns a Config object with dot-access syntax.
    Raises ConfigError if validation fails.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    content = path.read_text(encoding="utf-8")
    return parse_config(content, schema)


def parse_config(content: str,
                 schema: Optional[ConfigSchema] = None) -> Config:
    """
    Parse a .ltlcfg string, optionally validating against a schema.

    Returns a Config object.
    """
    parser = LtlCfgParser()
    raw = parser.parse_string(content)

    if schema:
        raw = schema.apply_defaults(raw)
        errors = schema.validate(raw)
        if errors:
            msg = "\n".join(f"  - {e}" for e in errors)
            raise ConfigError(f"Config validation failed:\n{msg}")

    return Config(raw)


def dump_config(config: Union[Config, dict], include_types: bool = True) -> str:
    """Serialize a config dict/Config back to .ltlcfg format."""
    data = config.to_dict() if isinstance(config, Config) else config
    lines: list[str] = []

    for section, fields in data.items():
        if not isinstance(fields, dict):
            continue
        lines.append(f"[{section}]")
        for key, value in fields.items():
            if isinstance(value, bool):
                v = "true" if value else "false"
                t = ": bool" if include_types else ""
            elif isinstance(value, int):
                v = str(value)
                t = ": int" if include_types else ""
            elif isinstance(value, float):
                v = str(value)
                t = ": float" if include_types else ""
            elif isinstance(value, list):
                items = ", ".join(repr(i) if isinstance(i, str) else str(i) for i in value)
                v = f"[{items}]"
                t = ": list" if include_types else ""
            elif isinstance(value, str):
                v = f'"{value}"'
                t = ": str" if include_types else ""
            else:
                v = str(value)
                t = ""
            lines.append(f"{key}{t} = {v}")
        lines.append("")

    return "\n".join(lines)


def get_ltlcfg_builtins() -> dict:
    return {
        "Config":         Config,
        "ConfigSchema":   ConfigSchema,
        "ConfigError":    ConfigError,
        "load_config":    load_config,
        "parse_config":   parse_config,
        "dump_config":    dump_config,
    }
