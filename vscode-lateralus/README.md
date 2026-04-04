# Lateralus Language

[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/lateralus.lateralus-lang?label=VS%20Code%20Marketplace&color=blue&logo=visual-studio-code)](https://marketplace.visualstudio.com/items?itemName=lateralus.lateralus-lang)
[![Installs](https://img.shields.io/visual-studio-marketplace/i/lateralus.lateralus-lang?color=green)](https://marketplace.visualstudio.com/items?itemName=lateralus.lateralus-lang)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/github/stars/bad-antics/lateralus-lang?style=social)](https://github.com/bad-antics/lateralus-lang)

> **Pipeline-native programming with full LSP intelligence.**

Rich language support for the [Lateralus](https://github.com/bad-antics/lateralus-lang) programming language — a pipeline-native language with a VM, C backend, bare-metal OS support, and its own assembly format.

---

## ✨ Features

### Language Server Protocol (LSP)

The extension ships with a full LSP client that communicates with the Lateralus language server over JSON-RPC. Every standard LSP capability is wired up:

| Feature | Keybinding | Description |
|---|---|---|
| **Diagnostics** | — | Real-time errors, warnings, and hints as you type |
| **Completions** | `Ctrl+Space` | Context-aware completions with snippet support |
| **Hover** | hover cursor | Type info, documentation, and signatures on hover |
| **Go to Definition** | `F12` | Jump to the definition of any symbol |
| **Find References** | `Shift+F12` | Find all references to a symbol across your project |
| **Document Formatting** | `Shift+Alt+F` | Format entire files with the Lateralus formatter |
| **Range Formatting** | select + `Ctrl+K Ctrl+F` | Format just the selected region |
| **Code Actions** | `Ctrl+.` | Quick fixes, refactors, organize imports |
| **Signature Help** | `(` / `,` | Parameter hints while typing function arguments |
| **Document Symbols** | `Ctrl+Shift+O` | Navigate functions, structs, enums in the Outline view |
| **Workspace Symbols** | `Ctrl+T` | Search symbols across your entire workspace |
| **Rename Symbol** | `F2` | Safely rename symbols across all files |
| **Folding Ranges** | — | Collapse functions, blocks, imports, and comments |
| **Selection Range** | `Shift+Alt+→` | Smart expand/shrink selection |

### Syntax Highlighting

Full TextMate grammars for **7 file types** in the Lateralus ecosystem:

| Language | Extension(s) | Highlights |
|---|---|---|
| **Lateralus** | `.ltl` | Keywords, types, operators, string interpolation, decorators, pipes |
| **Lateralus Assembly** | `.ltasm` | 80+ opcodes, registers, directives, labels |
| **Lateralus Markup** | `.ltlm` / `.ltlml` | Embedded Lateralus + Assembly blocks |
| **Lateralus Config** | `.ltlcfg` | Key-value pairs, sections, comments |
| **Lateralus Notebook** | `.ltlnb` | Cell markers, embedded code |
| **Lateralus Bytecode** | `.ltbc` | Binary file icon support |
| **Lateralus Compiled** | `.ltlc` | Binary file icon support |

### Code Snippets

**50+ snippets** across all file types for rapid development:

<details>
<summary><strong>.ltl snippets</strong> (click to expand)</summary>

`fn` · `afn` · `let` · `letm` · `const` · `if` · `ife` · `ifee` · `match` ·
`while` · `for` · `loop` · `try` · `trye` · `struct` · `enum` · `impl` ·
`implfor` · `interface` · `type` · `pln` · `ret` · `spawn` · `await`
</details>

<details>
<summary><strong>.ltasm snippets</strong></summary>

`.section` · `.global` · `entry` · `prints` · `sub` · `call` · `jt` ·
`movimm` · `try` · `spawn`
</details>

### File Icons

Custom icons for every Lateralus file type — light and dark themes, 15 SVGs total.

### Status Bar

Live indicator showing the LSP server state (`running` / `error` / `stopped`). Click to restart.

---

## 📋 Supported File Types

| File Type | Extension | Language ID |
|---|---|---|
| Lateralus source | `.ltl` | `lateralus` |
| Lateralus Assembly | `.ltasm` | `lateralus-asm` |
| Lateralus Markup | `.ltlm`, `.ltlml` | `lateralus-markup` |
| Lateralus Config | `.ltlcfg` | `lateralus-cfg` |
| Lateralus Notebook | `.ltlnb` | `lateralus-notebook` |
| Lateralus Bytecode | `.ltbc` | `lateralus-bytecode` |
| Lateralus Compiled | `.ltlc` | `lateralus-compiled` |

---

## 🚀 Quick Start

### From the Marketplace

1. Open VS Code
2. `Ctrl+Shift+X` → Search **"Lateralus"**
3. Click **Install**
4. Open any `.ltl` file — the LSP starts automatically

### From VSIX

```bash
code --install-extension lateralus-lang-2.5.0.vsix
```

### From Source

```bash
git clone https://github.com/bad-antics/lateralus-lang.git
cd lateralus-lang/vscode-lateralus
npm install -g @vscode/vsce
vsce package
code --install-extension lateralus-lang-2.5.0.vsix
```

---

## ⚙️ Configuration

| Setting | Default | Description |
|---|---|---|
| `lateralus.enableLSP` | `true` | Enable/disable the language server |
| `lateralus.pythonPath` | `""` | Custom Python path for the LSP server |
| `lateralus.formatOnSave` | `false` | Auto-format on save |
| `lateralus.trace.server` | `"off"` | Trace LSP communication (`off` / `messages` / `verbose`) |

---

## 🗺️ Language Quick Reference

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

## 🧩 Commands

Open the Command Palette (`Ctrl+Shift+P`) and type **Lateralus**:

| Command | Description |
|---|---|
| `Lateralus: Restart Language Server` | Restart the LSP server |
| `Lateralus: Show Output Channel` | Open the Lateralus output log |
| `Lateralus: Format Document` | Format the current file |
| `Lateralus: Organize Imports` | Sort and clean up imports (`Shift+Alt+O`) |

---

## 🔗 Links

- **Repository**: [github.com/bad-antics/lateralus-lang](https://github.com/bad-antics/lateralus-lang)
- **Issues**: [github.com/bad-antics/lateralus-lang/issues](https://github.com/bad-antics/lateralus-lang/issues)
- **Marketplace**: [marketplace.visualstudio.com](https://marketplace.visualstudio.com/items?itemName=lateralus.lateralus-lang)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

## 📄 License

MIT — see [LICENSE.txt](LICENSE.txt)
