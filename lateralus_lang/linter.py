"""
LATERALUS Linter (ltllint)
Static analysis and code quality checks for LATERALUS source files.

Checks:
  - Unused variables
  - Undefined references
  - Style violations
  - Potential bugs
  - Complexity warnings

Usage:
    python -m lateralus_lang.linter [files...] [--strict] [--fix]
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class LintIssue:
    """A single lint issue."""
    rule: str
    message: str
    severity: Severity
    file: str
    line: int
    column: int = 0
    suggestion: Optional[str] = None

    def __str__(self):
        sev = self.severity.value.upper()
        loc = f"{self.file}:{self.line}"
        if self.column > 0:
            loc += f":{self.column}"
        s = f"  {sev:7} {loc:30} [{self.rule}] {self.message}"
        if self.suggestion:
            s += f"\n           suggestion: {self.suggestion}"
        return s


@dataclass
class LintResult:
    """Result of linting a file or project."""
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0


# ─── Lint Rules ────────────────────────────────────────────────────────

LATERALUS_BUILTINS = {
    "println", "print", "len", "str", "int", "float", "type", "range",
    "map", "filter", "reduce", "sort", "reverse", "zip", "enumerate",
    "sum", "min", "max", "abs", "sqrt", "keys", "values", "split",
    "join", "contains", "append", "pop", "slice", "upper", "lower",
    "trim", "replace", "starts_with", "ends_with", "repr", "char_at",
    "dict_get", "assert_eq", "hash_sha256", "hash_blake2b",
    "random_token", "base64_encode", "base64_decode", "hex_encode",
    "hex_decode", "hmac_sign", "hmac_verify", "input", "round",
    "floor", "ceil", "log", "sin", "cos", "tan", "repeat",
}

LATERALUS_KEYWORDS = {
    "fn", "let", "const", "if", "else", "for", "while", "return",
    "match", "struct", "interface", "import", "from", "as", "in",
    "throw", "try", "catch", "emit", "probe", "measure", "pass",
    "break", "continue", "and", "or", "not", "true", "false", "none",
    # v1.3+ keywords
    "async", "await", "yield", "spawn", "foreign",
    # v1.5+ keywords
    "enum", "trait", "impl", "pub", "type", "where", "self",
}


class LateralusLinter:
    """Static analysis for LATERALUS source code."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.issues: list[LintIssue] = []
        self.defined_vars: dict[str, int] = {}  # name -> line
        self.used_vars: set[str] = set()
        self.defined_functions: dict[str, int] = {}
        self.used_functions: set[str] = set()
        self.imports: dict[str, int] = {}  # module -> first line
        self.fn_brace_depth: int = 0      # track function brace nesting
        self.in_function: bool = False
        self.after_return: bool = False    # did we see a return at current depth?
        self.fn_return_depth: int = 0      # brace depth where return was seen

    def lint(self, source: str, filename: str = "<stdin>") -> LintResult:
        """Lint LATERALUS source code."""
        self.issues = []
        self.defined_vars = {}
        self.used_vars = set()
        self.defined_functions = {}
        self.used_functions = set()
        self.imports = {}
        self.fn_brace_depth = 0
        self.in_function = False
        self.after_return = False
        self.fn_return_depth = 0

        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            self._check_line(line, i, filename, lines)

        # Post-analysis checks
        self._check_unused_vars(filename)
        self._check_unused_functions(filename)
        self._check_unused_imports(filename, source)

        return LintResult(issues=self.issues)

    def _check_line(self, line: str, lineno: int, filename: str, all_lines: list[str]):
        """Check a single line for issues."""
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            return

        # Check TODO/FIXME even in comment-only lines
        self._check_todo_fixme(stripped, lineno, filename)

        # Skip pure comment lines for other checks
        if stripped.startswith("//"):
            return

        # Check shadowed variables BEFORE collecting new definitions
        self._check_shadowed_variable(stripped, lineno, filename)

        # Collect definitions
        self._collect_definitions(stripped, lineno)
        self._collect_usages(stripped)

        # Rule checks
        self._check_line_length(line, lineno, filename)
        self._check_trailing_whitespace(line, lineno, filename)
        self._check_semicolons(stripped, lineno, filename)
        self._check_var_keyword(stripped, lineno, filename)
        self._check_comparison_none(stripped, lineno, filename)
        self._check_empty_block(stripped, lineno, filename, all_lines)
        self._check_nested_pipelines(stripped, lineno, filename)
        self._check_magic_numbers(stripped, lineno, filename)
        self._check_naming_conventions(stripped, lineno, filename)
        self._check_duplicate_import(stripped, lineno, filename)
        self._check_unreachable_code(stripped, lineno, filename)
        self._check_constant_condition(stripped, lineno, filename)
        self._check_deep_nesting(line, lineno, filename)
        self._check_string_concat_in_loop(stripped, lineno, filename, all_lines)
        self._check_mutable_default(stripped, lineno, filename)

        if self.strict:
            self._check_missing_type_annotations(stripped, lineno, filename)
            self._check_function_length(stripped, lineno, filename, all_lines)

    def _collect_definitions(self, line: str, lineno: int):
        """Track variable and function definitions."""
        # let/const declarations
        m = re.match(r"(?:let|const)\s+(\w+)", line)
        if m:
            self.defined_vars[m.group(1)] = lineno

        # Function declarations
        m = re.match(r"fn\s+(\w+)", line)
        if m:
            name = m.group(1)
            if name != "main":
                self.defined_functions[name] = lineno

        # for-in loop variable
        m = re.match(r"for\s+(\w+)\s+in", line)
        if m:
            self.defined_vars[m.group(1)] = lineno

    def _collect_usages(self, line: str):
        """Track variable and function usages."""
        # Simple identifier extraction
        identifiers = set(re.findall(r"\b([a-zA-Z_]\w*)\b", line))
        identifiers -= LATERALUS_KEYWORDS
        identifiers -= LATERALUS_BUILTINS

        # Remove definition names from usages on the same line
        if line.startswith("let ") or line.startswith("const "):
            m = re.match(r"(?:let|const)\s+(\w+)", line)
            if m:
                identifiers.discard(m.group(1))
        if line.startswith("fn "):
            m = re.match(r"fn\s+(\w+)", line)
            if m:
                identifiers.discard(m.group(1))

        self.used_vars.update(identifiers)
        self.used_functions.update(identifiers)

    def _check_unused_vars(self, filename: str):
        """Report unused variables."""
        for name, line in self.defined_vars.items():
            if name.startswith("_"):
                continue  # Skip underscore-prefixed (intentionally unused)
            if name not in self.used_vars:
                self.issues.append(LintIssue(
                    rule="unused-variable",
                    message=f"Variable '{name}' is defined but never used",
                    severity=Severity.WARNING,
                    file=filename,
                    line=line,
                    suggestion=f"Prefix with underscore: _{name}",
                ))

    def _check_unused_functions(self, filename: str):
        """Report unused functions."""
        for name, line in self.defined_functions.items():
            if name.startswith("_"):
                continue
            if name.startswith("test_"):
                continue  # Test functions are used by the test runner
            if name not in self.used_functions:
                self.issues.append(LintIssue(
                    rule="unused-function",
                    message=f"Function '{name}' is defined but never called",
                    severity=Severity.INFO if not self.strict else Severity.WARNING,
                    file=filename,
                    line=line,
                ))

    def _check_line_length(self, line: str, lineno: int, filename: str):
        if len(line) > 120:
            self.issues.append(LintIssue(
                rule="line-length",
                message=f"Line is {len(line)} characters (max 120)",
                severity=Severity.WARNING,
                file=filename,
                line=lineno,
            ))

    def _check_trailing_whitespace(self, line: str, lineno: int, filename: str):
        if line != line.rstrip():
            self.issues.append(LintIssue(
                rule="trailing-whitespace",
                message="Trailing whitespace",
                severity=Severity.HINT,
                file=filename,
                line=lineno,
            ))

    def _check_semicolons(self, line: str, lineno: int, filename: str):
        if line.endswith(";") and not line.startswith("//"):
            self.issues.append(LintIssue(
                rule="unnecessary-semicolon",
                message="Unnecessary semicolon",
                severity=Severity.INFO,
                file=filename,
                line=lineno,
                suggestion="Remove the semicolon",
            ))

    def _check_var_keyword(self, line: str, lineno: int, filename: str):
        if line.startswith("var "):
            self.issues.append(LintIssue(
                rule="use-let",
                message="Use 'let' instead of 'var'",
                severity=Severity.ERROR,
                file=filename,
                line=lineno,
                suggestion="Replace 'var' with 'let'",
            ))

    def _check_comparison_none(self, line: str, lineno: int, filename: str):
        if "== none" in line or "!= none" in line:
            self.issues.append(LintIssue(
                rule="none-comparison",
                message="Prefer pattern matching over none comparison",
                severity=Severity.INFO if not self.strict else Severity.WARNING,
                file=filename,
                line=lineno,
                suggestion="Use 'match value { none => ..., _ => ... }'",
            ))

    def _check_empty_block(self, line: str, lineno: int, filename: str, all_lines: list[str]):
        if line.endswith("{}") or line.endswith("{ }"):
            self.issues.append(LintIssue(
                rule="empty-block",
                message="Empty block — use 'pass' if intentional",
                severity=Severity.WARNING,
                file=filename,
                line=lineno,
                suggestion="Add 'pass' inside empty blocks",
            ))

    def _check_nested_pipelines(self, line: str, lineno: int, filename: str):
        pipe_count = line.count("|>") + line.count("|?")
        if pipe_count > 5:
            self.issues.append(LintIssue(
                rule="pipeline-length",
                message=f"Pipeline has {pipe_count} stages — consider breaking up",
                severity=Severity.WARNING,
                file=filename,
                line=lineno,
                suggestion="Extract intermediate steps into named variables",
            ))

    def _check_magic_numbers(self, line: str, lineno: int, filename: str):
        if line.startswith("let ") or line.startswith("const ") or line.startswith("//"):
            return
        # Find standalone numbers that aren't 0, 1, 2, or in known contexts
        numbers = re.findall(r"\b(\d{3,})\b", line)
        for num in numbers:
            if int(num) not in {100, 1000}:  # Allow common round numbers
                self.issues.append(LintIssue(
                    rule="magic-number",
                    message=f"Magic number {num} — consider using a named constant",
                    severity=Severity.HINT,
                    file=filename,
                    line=lineno,
                    suggestion=f"const MEANINGFUL_NAME = {num}",
                ))

    def _check_naming_conventions(self, line: str, lineno: int, filename: str):
        # Function names should be snake_case
        m = re.match(r"fn\s+([a-zA-Z_]\w*)", line)
        if m:
            name = m.group(1)
            if name != name.lower() and not name.startswith("_"):
                self.issues.append(LintIssue(
                    rule="naming-convention",
                    message=f"Function '{name}' should be snake_case",
                    severity=Severity.WARNING,
                    file=filename,
                    line=lineno,
                ))

        # Struct names should be PascalCase
        m = re.match(r"struct\s+([a-zA-Z_]\w*)", line)
        if m:
            name = m.group(1)
            if not name[0].isupper():
                self.issues.append(LintIssue(
                    rule="naming-convention",
                    message=f"Struct '{name}' should be PascalCase",
                    severity=Severity.WARNING,
                    file=filename,
                    line=lineno,
                ))

        # Constants should be UPPER_CASE
        m = re.match(r"const\s+([a-zA-Z_]\w*)", line)
        if m:
            name = m.group(1)
            if name != name.upper() and not name.startswith("_"):
                self.issues.append(LintIssue(
                    rule="naming-convention",
                    message=f"Constant '{name}' should be UPPER_CASE",
                    severity=Severity.INFO,
                    file=filename,
                    line=lineno,
                ))

    def _check_duplicate_import(self, line: str, lineno: int, filename: str):
        """Detect duplicate import statements."""
        m = re.match(r"(?:from\s+\S+\s+)?import\s+(\S+)", line)
        if m:
            module = m.group(1)
            if module in self.imports:
                self.issues.append(LintIssue(
                    rule="duplicate-import",
                    message=f"Module '{module}' already imported on line {self.imports[module]}",
                    severity=Severity.WARNING,
                    file=filename,
                    line=lineno,
                    suggestion=f"Remove duplicate import of '{module}'",
                ))
            else:
                self.imports[module] = lineno

    def _check_unreachable_code(self, line: str, lineno: int, filename: str):
        """Detect unreachable code after return/break/continue statements."""
        # Track function boundaries
        if re.match(r"fn\s+\w+", line):
            self.in_function = True
            self.fn_brace_depth = 0
            self.after_return = False

        if self.in_function:
            opens = line.count("{")
            closes = line.count("}")
            self.fn_brace_depth += opens - closes

            # If we previously saw a return at this depth, this line is unreachable
            if self.after_return and self.fn_brace_depth >= self.fn_return_depth:
                # Allow closing braces and else/catch clauses
                if line not in ("}", "") and not re.match(r"\}\s*else|catch|finally", line):
                    self.issues.append(LintIssue(
                        rule="unreachable-code",
                        message="Unreachable code after return/break/continue",
                        severity=Severity.WARNING,
                        file=filename,
                        line=lineno,
                        suggestion="Remove dead code or restructure control flow",
                    ))

            # Detect return/break/continue at current depth
            if re.match(r"return\b|break\b|continue\b", line):
                self.after_return = True
                self.fn_return_depth = self.fn_brace_depth
            elif closes > 0:
                # Closing a brace resets unreachable tracking for the outer scope
                if self.fn_brace_depth < self.fn_return_depth:
                    self.after_return = False

            if self.fn_brace_depth <= 0:
                self.in_function = False
                self.after_return = False

    def _check_shadowed_variable(self, line: str, lineno: int, filename: str):
        """Warn when a variable shadows an outer-scope variable."""
        m = re.match(r"(?:let|const)\s+(?:mut\s+)?(\w+)", line)
        if m:
            name = m.group(1)
            if name in self.defined_vars and name != "_":
                prev_line = self.defined_vars[name]
                # Only warn if defined more than a few lines ago (not just reassignment)
                if lineno - prev_line > 3:
                    self.issues.append(LintIssue(
                        rule="shadowed-variable",
                        message=f"Variable '{name}' shadows definition on line {prev_line}",
                        severity=Severity.INFO,
                        file=filename,
                        line=lineno,
                    ))

    def _check_todo_fixme(self, line: str, lineno: int, filename: str):
        """Flag TODO/FIXME/HACK/XXX comments as hints."""
        # Only check comments
        comment_idx = line.find("//")
        if comment_idx >= 0:
            comment = line[comment_idx:]
            for tag in ("TODO", "FIXME", "HACK", "XXX"):
                if tag in comment:
                    self.issues.append(LintIssue(
                        rule="todo-comment",
                        message=f"{tag} comment found",
                        severity=Severity.HINT,
                        file=filename,
                        line=lineno,
                    ))
                    break  # only one issue per line

    def _check_missing_type_annotations(self, line: str, lineno: int, filename: str):
        """Strict mode: check for missing type annotations."""
        m = re.match(r"fn\s+\w+\(([^)]*)\)", line)
        if m:
            params = m.group(1)
            if params and ":" not in params:
                self.issues.append(LintIssue(
                    rule="missing-type-annotation",
                    message="Function parameters should have type annotations",
                    severity=Severity.WARNING,
                    file=filename,
                    line=lineno,
                ))
            if "->" not in line:
                self.issues.append(LintIssue(
                    rule="missing-return-type",
                    message="Function should have a return type annotation",
                    severity=Severity.INFO,
                    file=filename,
                    line=lineno,
                ))

    def _check_function_length(self, line: str, lineno: int, filename: str, all_lines: list[str]):
        """Strict mode: warn about long functions."""
        if not re.match(r"fn\s+\w+", line):
            return

        # Count lines until matching closing brace
        brace_count = 0
        fn_lines = 0
        for j in range(lineno - 1, len(all_lines)):
            l = all_lines[j]
            brace_count += l.count("{") - l.count("}")
            fn_lines += 1
            if brace_count <= 0 and fn_lines > 1:
                break

        if fn_lines > 50:
            self.issues.append(LintIssue(
                rule="function-length",
                message=f"Function is {fn_lines} lines long (max 50)",
                severity=Severity.WARNING,
                file=filename,
                line=lineno,
                suggestion="Consider splitting into smaller functions",
            ))

    # ── v2.3 rules ──────────────────────────────────────────────────────

    def _check_constant_condition(self, line: str, lineno: int, filename: str):
        """Detect constant boolean conditions in if/while statements."""
        # Match if true / if false / while true / while false
        m = re.match(r"(if|while|guard)\s+(true|false)\b", line)
        if m:
            keyword, value = m.group(1), m.group(2)
            # while true is an intentional infinite loop pattern — only hint
            if keyword == "while" and value == "true":
                return  # common idiom, skip
            self.issues.append(LintIssue(
                rule="constant-condition",
                message=f"Condition is always {value}",
                severity=Severity.WARNING,
                file=filename,
                line=lineno,
                suggestion="Remove the dead branch or simplify the condition",
            ))

    def _check_unused_imports(self, filename: str, source: str):
        """Report imported modules that are never referenced in the code."""
        for module, line in self.imports.items():
            # Simple heuristic: check if module name appears outside import lines
            uses = 0
            for src_line in source.split("\n"):
                stripped = src_line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    continue
                if module in stripped:
                    uses += 1
            if uses == 0:
                self.issues.append(LintIssue(
                    rule="unused-import",
                    message=f"Module '{module}' is imported but never used",
                    severity=Severity.WARNING,
                    file=filename,
                    line=line,
                    suggestion=f"Remove unused import: import {module}",
                ))

    def _check_deep_nesting(self, line: str, lineno: int, filename: str):
        """Warn about deeply nested code (more than 4 levels)."""
        if not line.strip():
            return
        # Count leading spaces to determine nesting depth
        indent = len(line) - len(line.lstrip())
        depth = indent // 4  # assuming 4-space indentation
        if depth >= 5 and not line.strip().startswith("//"):
            self.issues.append(LintIssue(
                rule="deep-nesting",
                message=f"Code is nested {depth} levels deep — consider refactoring",
                severity=Severity.INFO if depth < 7 else Severity.WARNING,
                file=filename,
                line=lineno,
                suggestion="Extract nested logic into helper functions",
            ))

    def _check_string_concat_in_loop(self, line: str, lineno: int, filename: str,
                                      all_lines: list[str]):
        """Detect string concatenation inside loops (performance issue)."""
        # Check if we're inside a loop
        in_loop = False
        indent = len(line) - len(line.lstrip()) if line.strip() else 0
        for j in range(lineno - 2, max(0, lineno - 20), -1):
            prev = all_lines[j].strip()
            prev_indent = len(all_lines[j]) - len(all_lines[j].lstrip()) if prev else 0
            if prev_indent < indent and re.match(r"(for|while)\b", prev):
                in_loop = True
                break

        if in_loop and "+=" in line:
            # Check if the variable being appended to is likely a string
            m = re.match(r"(\w+)\s*\+=\s*\"", line)
            if m:
                self.issues.append(LintIssue(
                    rule="string-concat-in-loop",
                    message="String concatenation in a loop — consider using a list and join()",
                    severity=Severity.INFO,
                    file=filename,
                    line=lineno,
                    suggestion="Collect parts in a list, then use join()",
                ))

    def _check_mutable_default(self, line: str, lineno: int, filename: str):
        """Detect function parameters with mutable default values."""
        m = re.match(r"fn\s+\w+\(.*?(\w+)\s*=\s*(\[\]|\{\})\s*[,)]", line)
        if m:
            param, default = m.group(1), m.group(2)
            self.issues.append(LintIssue(
                rule="mutable-default",
                message=f"Parameter '{param}' has a mutable default value {default}",
                severity=Severity.WARNING,
                file=filename,
                line=lineno,
                suggestion=f"Use 'none' as default and create {default} inside the function",
            ))


def lint_file(path: Path, strict: bool = False) -> LintResult:
    """Lint a single file."""
    linter = LateralusLinter(strict=strict)
    source = path.read_text()
    return linter.lint(source, str(path))


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="ltllint", description="LATERALUS Linter")
    parser.add_argument("files", nargs="*", default=["."])
    parser.add_argument("--strict", action="store_true", help="Enable strict checks")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--errors-only", action="store_true", help="Only show errors")

    args = parser.parse_args()

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

    total_issues = 0
    total_errors = 0

    for f in files:
        result = lint_file(f, strict=args.strict)

        for issue in result.issues:
            if args.errors_only and issue.severity != Severity.ERROR:
                continue
            print(str(issue))
            total_issues += 1

        total_errors += result.error_count

    print(f"\n  {total_issues} issues ({total_errors} errors) in {len(files)} files")

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
