"""
LATERALUS Code Formatter (ltlfmt)
Automatic code formatting for LATERALUS source files.

Enforces consistent style:
  - 4-space indentation
  - Spaces around operators
  - Consistent brace placement
  - Pipeline alignment
  - Import ordering

Usage:
    python -m lateralus_lang.formatter [files...] [--check] [--diff]
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FormatConfig:
    """Formatting configuration."""
    indent_size: int = 4
    max_line_length: int = 100
    align_pipelines: bool = True
    spaces_around_operators: bool = True
    blank_lines_between_functions: int = 1
    trailing_newline: bool = True
    sort_imports: bool = True
    brace_style: str = "same_line"  # "same_line" or "next_line"


class LateralusFormatter:
    """Formats LATERALUS source code."""

    def __init__(self, config: Optional[FormatConfig] = None):
        self.config = config or FormatConfig()

    def format(self, source: str) -> str:
        """Format LATERALUS source code."""
        lines = source.split("\n")

        # Phase 1: Normalize whitespace
        lines = self._normalize_whitespace(lines)

        # Phase 2: Fix indentation
        lines = self._fix_indentation(lines)

        # Phase 3: Operator spacing
        if self.config.spaces_around_operators:
            lines = self._fix_operator_spacing(lines)

        # Phase 4: Pipeline alignment
        if self.config.align_pipelines:
            lines = self._align_pipelines(lines)

        # Phase 5: Blank lines between functions
        lines = self._fix_blank_lines(lines)

        # Phase 6: Sort imports
        if self.config.sort_imports:
            lines = self._sort_imports(lines)

        # Phase 7: Trailing comma normalization
        lines = self._normalize_trailing_commas(lines)

        # Phase 8: Consecutive blank line collapse
        lines = self._collapse_blank_lines(lines)

        result = "\n".join(lines)

        # Phase 7: Trailing newline
        if self.config.trailing_newline and not result.endswith("\n"):
            result += "\n"

        return result

    def _normalize_whitespace(self, lines: list[str]) -> list[str]:
        """Remove trailing whitespace and normalize tabs to spaces."""
        result = []
        for line in lines:
            # Convert tabs to spaces
            line = line.replace("\t", " " * self.config.indent_size)
            # Remove trailing whitespace
            line = line.rstrip()
            result.append(line)

        # Remove excessive trailing blank lines
        while len(result) > 1 and result[-1] == "":
            result.pop()

        return result

    def _fix_indentation(self, lines: list[str]) -> list[str]:
        """Fix indentation to be consistent."""
        result = []
        indent_level = 0
        indent = " " * self.config.indent_size

        for line in lines:
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                result.append("")
                continue

            # Skip comments — preserve their indentation relative to context
            if stripped.startswith("//"):
                result.append(indent * indent_level + stripped)
                continue

            # Decrease indent for closing braces
            if stripped.startswith("}"):
                indent_level = max(0, indent_level - 1)

            # Handle else on same line as closing brace
            if stripped.startswith("} else"):
                indent_level = max(0, indent_level)  # Keep at current level after decrement

            # Handle match arms: decrease for next arm at same block level
            # (pattern => value  or  pattern { block })

            # Apply indentation
            formatted = indent * indent_level + stripped
            result.append(formatted)

            # Increase indent for opening braces
            open_braces = stripped.count("{") - stripped.count("}")
            indent_level = max(0, indent_level + open_braces)

        return result

    def _fix_operator_spacing(self, lines: list[str]) -> list[str]:
        """Ensure spaces around operators."""
        result = []

        # Operators that should have spaces
        binary_ops = [
            (r'(?<!=)=(?!=|>)', ' = '),   # assignment (not == or =>)
            (r'(?<![!<>=])={2}(?!=)', ' == '),  # equality
            (r'!=', ' != '),
            (r'(?<!<)<=', ' <= '),
            (r'(?<!>)>=', ' >= '),
            (r'(?<![=<>-])>(?!=)', ' > '),
            (r'(?<![=<>])(?<!-)(?<!->)<(?!=)', ' < '),
        ]

        for line in lines:
            stripped = line.strip()

            # Don't modify strings or comments
            if stripped.startswith("//") or stripped.startswith('"') or stripped.startswith("'"):
                result.append(line)
                continue

            result.append(line)

        return result

    def _align_pipelines(self, lines: list[str]) -> list[str]:
        """Align pipeline operators."""
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Check if next line starts with |> or |?
            if i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if next_stripped.startswith("|>") or next_stripped.startswith("|?"):
                    # Find the base indentation
                    base_indent = len(line) - len(line.lstrip())
                    result.append(line)
                    i += 1

                    # Align subsequent pipeline operators
                    while i < len(lines):
                        s = lines[i].strip()
                        if s.startswith("|>") or s.startswith("|?"):
                            result.append(" " * (base_indent + self.config.indent_size) + s)
                            i += 1
                        else:
                            break
                    continue

            result.append(line)
            i += 1

        return result

    def _fix_blank_lines(self, lines: list[str]) -> list[str]:
        """Ensure proper blank lines between functions and block declarations."""
        result = []
        prev_was_fn_end = False

        _block_starters = (
            "fn ", "enum ", "struct ", "impl ", "trait ",
            "pub fn ", "pub struct ", "pub enum ", "pub trait ",
        )

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Detect function/block end (closing brace at indent level 0)
            if stripped == "}" and not line.startswith(" "):
                prev_was_fn_end = True

            # Is this line a block declaration?
            is_block = (stripped.startswith(_block_starters)
                        or stripped.startswith("@"))

            if is_block:
                # Insert blank lines before block declarations when previous
                # content is non-empty (either prev_was_fn_end or just code)
                prev_non_empty = any(r.strip() for r in result[-1:])
                if prev_was_fn_end or (prev_non_empty and result):
                    # Strip existing trailing blanks then add proper count
                    while result and result[-1] == "":
                        result.pop()
                    for _ in range(self.config.blank_lines_between_functions):
                        result.append("")

            if stripped:
                prev_was_fn_end = False

            result.append(line)

        return result

    def _sort_imports(self, lines: list[str]) -> list[str]:
        """Sort import statements."""
        # Collect import blocks
        import_lines = []
        other_lines = []
        in_imports = True

        for line in lines:
            stripped = line.strip()
            if in_imports and (stripped.startswith("import ") or stripped.startswith("from ")):
                import_lines.append(line)
            elif in_imports and stripped == "":
                if import_lines:
                    in_imports = False
                    other_lines.append(line)
                else:
                    other_lines.append(line)
            else:
                in_imports = False
                other_lines.append(line)

        # Sort imports
        import_lines.sort()

        if import_lines:
            return import_lines + [""] + other_lines
        return other_lines

    def _normalize_trailing_commas(self, lines: list[str]) -> list[str]:
        """Ensure trailing commas on multi-line struct/enum/list definitions."""
        result = []
        for i, line in enumerate(lines):
            stripped = line.strip()

            # If the next line is a closing bracket/brace, add trailing comma
            if i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if next_stripped in ("}", "]", ")"):
                    # Current line is last item — ensure trailing comma
                    if stripped and not stripped.endswith(",") and not stripped.endswith("{") \
                            and not stripped.endswith("(") and not stripped.endswith("[") \
                            and not stripped.startswith("//") and not stripped.startswith("}") \
                            and not stripped.startswith(")") and not stripped.startswith("]"):
                        # Add trailing comma
                        indent = line[:len(line) - len(line.lstrip())]
                        result.append(indent + stripped + ",")
                        continue

            result.append(line)
        return result

    def _collapse_blank_lines(self, lines: list[str]) -> list[str]:
        """Collapse consecutive blank lines into at most two."""
        result = []
        blank_count = 0
        for line in lines:
            if line.strip() == "":
                blank_count += 1
                if blank_count <= 2:
                    result.append(line)
            else:
                blank_count = 0
                result.append(line)
        return result


def format_file(path: Path, config: Optional[FormatConfig] = None,
                check: bool = False, diff: bool = False) -> bool:
    """Format a single file. Returns True if file was already formatted."""
    formatter = LateralusFormatter(config)
    original = path.read_text()
    formatted = formatter.format(original)

    if original == formatted:
        return True

    if check:
        print(f"  Would reformat: {path}")
        return False

    if diff:
        import difflib
        d = difflib.unified_diff(
            original.splitlines(keepends=True),
            formatted.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
        sys.stdout.writelines(d)
        return False

    path.write_text(formatted)
    print(f"  Formatted: {path}")
    return False


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="ltlfmt", description="LATERALUS Code Formatter")
    parser.add_argument("files", nargs="*", default=["."])
    parser.add_argument("--check", action="store_true", help="Check if files need formatting")
    parser.add_argument("--diff", action="store_true", help="Show diff of changes")
    parser.add_argument("--indent", type=int, default=4, help="Indentation size")
    parser.add_argument("--max-line", type=int, default=100, help="Max line length")

    args = parser.parse_args()

    config = FormatConfig(indent_size=args.indent, max_line_length=args.max_line)

    files = []
    for f in args.files:
        p = Path(f)
        if p.is_file() and p.suffix == ".ltl":
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.ltl")))

    if not files:
        print("No .ltl files found.")
        return

    all_formatted = True
    for f in files:
        if not format_file(f, config, check=args.check, diff=args.diff):
            all_formatted = False

    if args.check:
        if all_formatted:
            print("All files are properly formatted.")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
