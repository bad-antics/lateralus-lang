# Changelog

All notable changes to the Lateralus Language extension will be documented in this file.

## [3.1.0] — 2026-04-21

### Changed
- **Version alignment** with Lateralus language core (3.1.0). Extension and
  language now share a single version number for clarity.
- Updated README VSIX install examples to reference `lateralus-lang-3.1.0.vsix`.

### Notes on marketplace state
A one-off build was published as 2.6.0 on 2026-04-04 without being committed
back to the repository. This 3.1.0 release supersedes it and re-syncs the
repository as the single source of truth for the extension.

## [2.5.1] — 2026-04-03

### Fixed
- Marketplace icon now uses PNG (was SVG, which marketplace does not render)
- README now shows full feature table with LSP providers on marketplace page
- All LSP providers registered for all 5 Lateralus language types

## [2.5.0] — 2025-07-09

### Added
- **Go to Definition** — `F12` to jump to symbol definitions
- **Find All References** — `Shift+F12` to find all usages of a symbol
- **Document Formatting** — `Shift+Alt+F` to format entire files
- **Range Formatting** — format selected regions
- **Code Actions** — quick fixes, refactors, and source actions via `Ctrl+.`
- **Signature Help** — parameter hints on `(` and `,` while typing function calls
- **Document Symbols** — outline view and `Ctrl+Shift+O` navigation
- **Workspace Symbols** — `Ctrl+T` to search symbols across the workspace
- **Rename Symbol** — `F2` for project-wide safe rename
- **Folding Ranges** — collapse functions, blocks, imports, and comments
- **Selection Range** — smart expand/shrink selection with `Shift+Alt+→`
- **Organize Imports** command with `Shift+Alt+O` keybinding
- **Format Document** command
- **didSave** document sync notification
- **window/showMessage** and **window/logMessage** handling from LSP server
- LSP error response handling with proper promise rejection
- `lateralus.formatOnSave` setting
- `lateralus.trace.server` setting (`off` / `messages` / `verbose`)
- Added `Formatters`, `Linters`, `Snippets` categories to marketplace listing
- Added `pipeline`, `language server`, `lsp` keywords
- Marketplace gallery banner (dark theme, #1e1e2e)
- `icon` field pointing to lateralus-logo.svg for marketplace listing
- `bugs` and `homepage` URLs in package.json
- All LSP providers now work across all 5 Lateralus language types (not just `.ltl`)

### Changed
- Version bumped to 2.5.0
- `isLateralusDocument()` now recognizes all 5 language IDs
- LSP request timeout increased from 5s to 10s
- Completion provider now triggers on `|` (pipe) in addition to `.` and `:`
- Hover provider now handles MarkupContent, MarkedString arrays, and range
- Completion provider now handles both array and object response formats
- `pendingRequests` map now stores `{resolve, reject}` for proper error handling
- Initialize capabilities now declare all new provider support

## [2.4.0] — 2025-04-03

### Added
- Lateralus Bytecode (`.ltbc`) file type
- Lateralus Compiled (`.ltlc`) file type
- File icons for bytecode and compiled types

## [2.3.0] — 2025-04-03

### Added
- LSP client with JSON-RPC over stdin/stdout
- Diagnostics (publishDiagnostics)
- Completion provider
- Hover provider
- Document synchronization (didOpen, didChange, didClose)
- Status bar indicator with restart support
- `lateralus.restartServer` command
- `lateralus.showOutput` command
- `lateralus.enableLSP` setting
- `lateralus.pythonPath` setting

## [2.2.0] — 2025-04-03

### Added
- Lateralus Notebook (`.ltlnb`) support with grammar and snippets
- Lateralus Config (`.ltlcfg`) support with grammar and snippets
- Lateralus Markup (`.ltlm` / `.ltlml`) support with embedded languages

## [2.0.0] — 2025-04-03

### Added
- Lateralus Assembly (`.ltasm`) syntax highlighting
- Assembly snippets (entry, prints, sub, call, etc.)
- Assembly language configuration (brackets, comments)
- All 15 file icons (light + dark for each language type)

## [1.0.0] — 2025-04-03

### Added
- Initial release
- Lateralus (`.ltl`) syntax highlighting
- TextMate grammar with keywords, types, operators, string interpolation
- Bracket matching and auto-closing pairs
- Code snippets for common patterns
- MIT License
