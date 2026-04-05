# LATERALUS Style Guide

This document defines mandatory style rules for **all** code, documentation,
and assets in the LATERALUS project. All contributors must follow these rules.

---

## 1. NO BOX-DRAWING CHARACTERS — PERMANENT POLICY

Unicode box-drawing characters are **permanently banned** from this project.
This applies to every file type — source code, comments, string literals,
output text, documentation, READMEs, configuration, and data files.

### Banned characters

```
Single-line:   ─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼
Double-line:   ═ ║ ╔ ╗ ╚ ╝ ╠ ╣ ╦ ╩ ╬
Heavy-line:    ━ ┃ ┏ ┓ ┗ ┛ ┣ ┫ ┳ ┻ ╋
```

**All 34 characters above are rejected.** No exceptions.

### Required ASCII alternatives

| Purpose            | Character | Example                        |
|--------------------|-----------|--------------------------------|
| Horizontal rule    | `-`       | `--------------------`         |
| Thick rule / break | `=`       | `====================`         |
| Vertical separator | `\|`      | `\| content \|`               |
| Corner / junction  | `+`       | `+----+`                       |
| Section header     | `=`       | `# ==== Section ====`          |
| Comment separator  | `=` / `-` | `// ====================`      |

### Examples

**Correct — ASCII box:**
```
+==============================+
|  LateralusOS v0.3.0         |
+==============================+
```

**Correct — ASCII table:**
```
+--------+-------+---------+
| Name   | Type  | Status  |
+--------+-------+---------+
| sched  | task  | active  |
+--------+-------+---------+
```

**Correct — comment separator:**
```python
# ===========================================================================
# Module: compiler.py
# ===========================================================================
```

**Wrong — box-drawing (REJECTED):**
```
╔══════════════════════════════╗
║  LateralusOS v0.3.0         ║
╚══════════════════════════════╝
```

### Verification

Before committing, verify no box-drawing characters remain:

```bash
grep -rn '[═║╔╗╚╝╠╣╦╩╬┌┐└┘─│├┤┬┴┼━┃┏┓┗┛┣┫┳┻╋]' \
  --include="*.py" --include="*.ltl" --include="*.c" \
  --include="*.h" --include="*.md" --include="*.sh" \
  --include="*.asm" --include="*.json"
```

This should return **zero** results. PRs that introduce box-drawing
characters will not be merged.

---

## 2. Python Code Style

- Python 3.10+ required
- Type hints on all public functions
- Docstrings on all classes and public methods
- 100-character line limit
- Use `dataclass` for data structures
- Use `enum.Enum` for enumerations

## 3. LATERALUS Code Style

- Use `let` (not `var`) for variable declarations
- Use pipeline operators (`|>`) for data transformations
- `snake_case` for functions and variables
- `PascalCase` for struct names
- `UPPER_CASE` for constants
- Format with: `lateralus fmt src/`
- Lint with: `lateralus lint src/ --strict`

## 4. C Code (LateralusOS)

- C99 freestanding — no libc
- `snake_case` for functions and variables
- `UPPER_CASE` for macros and constants
- Indent with 4 spaces (no tabs)
- Keep functions under 80 lines where possible
- ASCII-only in all strings and comments (see Rule 1)

## 5. Commit Messages

Use conventional commits:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation
- `test:` — Test changes
- `refactor:` — Code restructuring
- `perf:` — Performance improvement
- `style:` — Formatting / style changes (no logic change)

---

*Spiral outward. Keep it clean. Keep it ASCII.*
