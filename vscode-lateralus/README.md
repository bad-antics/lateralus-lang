# Lateralus Language — VS Code Extension

Syntax highlighting, bracket matching, code snippets, and file-icon support
for the **Lateralus** programming language (`.ltl`) and **Lateralus Assembly**
(`.ltasm`).

---

## Features

### Lateralus (`.ltl`)
| Feature | Details |
|---|---|
| **Syntax highlighting** | Keywords, types, operators, literals, comments |
| **String interpolation** | `{expr}` inside `"..."` strings highlighted correctly |
| **Raw strings** | `r"..."` treated as plain string content |
| **Decorators** | `@doc`, `@deprecated`, etc. |
| **Type declarations** | `struct`, `enum`, `interface`, `impl`, `type` aliases |
| **Function signatures** | `fn` / `async fn` names highlighted |
| **Module system** | `module`, `import`, `from … import` |
| **Comments** | `//` line, `/* */` block, `#` hash |
| **Bracket matching** | `{}`, `[]`, `()` |
| **Code snippets** | `fn`, `afn`, `let`, `letm`, `if`, `ife`, `match`, `while`, `for`, `try`, `struct`, `enum`, `impl`, and more |

### Lateralus Assembly (`.ltasm`)
| Feature | Details |
|---|---|
| **Opcode highlighting** | All ~80+ LTasm opcodes (`PUSH_IMM`, `CALL`, `FADD`, …) |
| **Register highlighting** | `r0`–`r15`, `sp`, `pc`, `flags` |
| **Directives** | `.section`, `.global`, `.data`, `.text`, `.align`, … |
| **Labels** | Definition (`name:`) and reference (`.name`) |
| **Semicolon comments** | `;` line comments |
| **String literals** | `"…"` with escape sequences |
| **Numeric literals** | Decimal, `0x` hex, `0b` binary |
| **Code snippets** | `entry`, `prints`, `sub`, `call`, `jt`, `movimm`, `try`, `spawn` |

---

## Language Quick Reference

```lateralus
module examples.hello

import io

@doc("Entry point")
pub fn main() {
    let name: str = "Lateralus"
    let nums = [1, 2, 3] |> map(fn(x) x * x)
    io.println("Hello from {name}!")
}

pub struct Point { x: float  y: float }

impl Point {
    pub fn new(x: float, y: float) -> Point {
        return Point { x: x, y: y }
    }
}

async fn fetch(url: str) -> str {
    return await http.get(url)
}
```

```lateralus-asm
; Hello World in Lateralus Assembly
.section code
.global _start

_start:
    PUSH_STR   "Hello, World!"
    PRINTLN
    PUSH_IMM   0
    HALT
```

---

## Snippets

### `.ltl` trigger list
`fn` · `afn` · `let` · `letm` · `const` · `if` · `ife` · `ifee` · `match` ·
`while` · `for` · `loop` · `try` · `trye` · `struct` · `enum` · `impl` ·
`implfor` · `interface` · `type` · `pln` · `ret` · `spawn` · `await`

### `.ltasm` trigger list
`.section` · `.global` · `entry` · `prints` · `sub` · `call` · `jt` ·
`movimm` · `try` · `spawn`

---

## Installation

### From source (developer mode)

```bash
# Copy to VS Code extensions directory
cp -r vscode-lateralus ~/.vscode/extensions/lateralus-lang.lateralus-1.3.0

# Reload VS Code window
# Ctrl+Shift+P → "Developer: Reload Window"
```

### Via VSIX package

```bash
npm install -g @vscode/vsce
cd vscode-lateralus
vsce package
code --install-extension lateralus-lang-1.3.0.vsix
```

---

## License

MIT
