# Mastering Unix Glob in Lateralus: Wildcard Matching, Path Filtering, and Linear Backtracking

File system traversals, build pipelines, and command-line interfaces require flexible file and path matching. While full regular expressions (Regex) are expressive, they carry substantial runtime overhead, complex escaping rules, and vulnerability to Regular Expression Denial of Service (ReDoS) catastrophic backtracking.

**Unix Globbing** offers an ergonomic, deterministic alternative using standard wildcards (`*`, `?`) designed specifically for file trees and token matching.

In this tutorial, we implement a linear-time, non-recursive, two-pointer backtracking Glob pattern matcher natively in Lateralus.

---

## 1. Syntax & Wildcard Semantics

The core Unix globbing semantics include:
- **`*` (Asterisk)**: Matches zero or more arbitrary characters.
- **`?` (Question Mark)**: Matches exactly one character.
- **Literals**: Match the identical character at the corresponding position.

Examples:
- `*.ltl` matches any file ending with `.ltl`.
- `file?.txt` matches `file1.txt`, `fileA.txt`, but rejects `file12.txt`.
- `src/*` matches any file under the `src/` directory.

---

## 2. Linear Two-Pointer Greedy Backtracking Engine

Rather than constructing an NFA or using deep recursion (which risks stack overflow on deep paths), our implementation maintains four pointer indices:
- `p_idx`: Current pattern position
- `t_idx`: Current text position
- `star_idx`: Position of the most recent `*` wildcard encountered
- `match_idx`: Text offset anchored to the `*` wildcard

```lateralus
fn glob_match(pattern: string, text: string) -> bool {
    let p_len = len(pattern);
    let t_len = len(text);
    let mut p_idx = 0;
    let mut t_idx = 0;
    let mut star_idx = -1;
    let mut match_idx = 0;

    while t_idx < t_len {
        let mut p_char = "";
        if p_idx < p_len {
            p_char = slice(pattern, p_idx, p_idx + 1);
        }
        let t_char = slice(text, t_idx, t_idx + 1);

        if p_idx < p_len && (p_char == "?" || p_char == t_char) {
            p_idx = p_idx + 1;
            t_idx = t_idx + 1;
        } else if p_idx < p_len && p_char == "*" {
            star_idx = p_idx;
            match_idx = t_idx;
            p_idx = p_idx + 1;
        } else if star_idx != -1 {
            p_idx = star_idx + 1;
            match_idx = match_idx + 1;
            t_idx = match_idx;
        } else {
            return false;
        }
    }

    while p_idx < p_len && slice(pattern, p_idx, p_idx + 1) == "*" {
        p_idx = p_idx + 1;
    }

    return p_idx == p_len;
}
```

---

## 3. Real-World Build Tool Filtering

In build automation, globs select compilation inputs while ignoring distribution artifacts.

See `examples/glob_tutorial.ltl` for a runnable demonstration filtering `.ltl` sources and directory partitions.

---

## 4. End-to-End Verification with Golden Vectors

We assert compliance across edge cases:
- Exact string equivalence and mismatches.
- Single-character `?` cardinality bounds.
- Multi-wildcard combinations (`*.*`, `?*?`).
- Empty string matches (`""` vs `""`, `*` vs `""`).

Run the compiler checks and test suites:
```bash
python -m lateralus_lang check examples/glob_tutorial.ltl
python -m lateralus_lang check tests/stdlib_glob_tutorial.ltl
pytest tests/test_compiler.py
```
