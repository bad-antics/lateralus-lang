---
title: "Monadic Parser Combinators: Composable Choice, Sequence & Predictive Grammars in Lateralus"
description: "A deep-dive tutorial on stdlib/parsec.ltl — building modular LL(1) token recognizers using choice (|), sequence (&), and Kleene star (*) combinators in Lateralus."
date: "2026-11-22"
author: "Lateralus Standard Library Team"
tags: ["parsec", "parsers", "combinators", "compilers", "standard-library"]
---

# Monadic Parser Combinators: Composable Choice, Sequence & Predictive Grammars in Lateralus

Hand-rolled recursive-descent parsers often tangle lexical state with grammar rules. **Parser combinators** (inspired by Haskell's Parsec) treat parsers as composable building blocks that consume a token cursor and return a structured result `(matched, next_pos, ast_value)`.

The **`stdlib/parsec.ltl`** module provides the core algebraic combinators—`token`, `choice` ($P_1 \parallel P_2$), `sequence` ($P_1 \cdot P_2$), and `many` ($P^*$)—for constructing predictive grammar recognizers.

---

## 1. Combinator Semantics

Let an input stream be an array of tokens $T[0 \dots n-1]$ and a cursor position $i \in [0, n]$:

1. **Terminal Matcher (`match_tok(T, i, expected)`)**:
   Succeeds with `(1, i + 1)` if $i < n \land T[i] = \text{expected}$; otherwise fails with `(0, i)`.
2. **Ordered Choice ($P_1 \parallel P_2$)**:
   Evaluates $P_1(T, i)$. If $P_1$ succeeds, returns its result; otherwise backtracks to cursor $i$ and evaluates $P_2(T, i)$.
3. **Sequence ($P_1 \cdot P_2$)**:
   Evaluates $(ok_1, i_1) = P_1(T, i)$. If $ok_1 = 1$, evaluates $(ok_2, i_2) = P_2(T, i_1)$; otherwise backtracks to $(0, i)$.

---

## 2. Runnable Lateralus Implementation

From `examples/parsec_tutorial.ltl`:

```ltl
pub fn parse_choice(tokens, n, pos, tok_a, tok_b) {
    if pos >= n { return -1 }
    if (tokens[pos] == tok_a) || (tokens[pos] == tok_b) {
        return pos + 1
    }
    return -1
}

pub fn parse_sequence2(tokens, n, pos, tok_first, tok_second) {
    if (pos + 1) >= n { return -1 }
    if (tokens[pos] == tok_first) && (tokens[pos + 1] == tok_second) {
        return pos + 2
    }
    return -1
}
```

---

## 3. Pinned Verification Vectors

| Grammar Rule | Token Stream | Start Pos | Result Cursor (`-1` = Fail) |
| :--- | :--- | :--- | :--- |
| `choice('LET', 'CONST')` | `['LET', 'IDENT', 'EQ', 'NUM']` | `0` | `1` (Consumed `'LET'`) |
| `sequence('EQ', 'NUM')` | `['LET', 'IDENT', 'EQ', 'NUM']` | `2` | `4` (Consumed `'EQ', 'NUM'`) |
| `many('DIGIT')` | `['DIGIT', 'DIGIT', 'DIGIT', 'EOF']` | `0` | `3` (Consumed 3 digits) |
| `sequence('LET', 'EQ')` | `['LET', 'IDENT', 'EQ', 'NUM']` | `0` | `-1` (Backtracked on mismatch) |
