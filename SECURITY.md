# Security Policy

## Supported Versions

| Version | Supported          |
|:--------|:-------------------|
| 3.0.x   | ✅ Active support  |
| 2.x.x   | ⚠️ Critical fixes only |
| < 2.0   | ❌ End of life     |

## Reporting a Vulnerability

If you discover a security vulnerability in Lateralus, **please do not open a public issue**.

Instead, report it responsibly via one of the following:

1. **GitHub Security Advisories** — [Report a vulnerability](https://github.com/bad-antics/lateralus-lang/security/advisories/new) (preferred)
2. **Email** — Send details to the maintainers listed in `pyproject.toml`

### What to include

- Description of the vulnerability
- Steps to reproduce
- Affected version(s)
- Impact assessment (if known)
- Suggested fix (if any)

### Response timeline

| Stage | Timeframe |
|:------|:----------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 1 week |
| Fix development | Within 2 weeks (critical), 4 weeks (moderate) |
| Public disclosure | After fix is released |

### Scope

The following components are in scope:

- **Compiler** (`lateralus_lang/`) — Lexer, parser, code generation, VM
- **Standard library** (`stdlib/`) — All built-in modules
- **CLI tools** (`bin/`, `scripts/`) — Command-line interface
- **LSP server** — Language Server Protocol implementation
- **DAP server** — Debug Adapter Protocol implementation
- **Build tooling** — Makefile, pyproject.toml, packaging

### Out of scope

- Third-party packages or community-contributed code
- The VS Code extension (report to [lateralus-grammar](https://github.com/bad-antics/lateralus-grammar) repo)
- Example code in `examples/` (educational, not production)

## Security Best Practices for Lateralus Code

When writing Lateralus applications:

```lateralus
// Use try/recover for untrusted input
let parsed = try {
    input |> parse_json
} recover err {
    log_error("Invalid input: {err}")
    return Error("Malformed data")
}

// Validate before pipeline processing
let results = user_data
    |> validate(schema)
    |> sanitize
    |> process
```

## Acknowledgments

We thank all security researchers who responsibly disclose vulnerabilities. Contributors who report valid security issues will be credited in release notes (unless anonymity is requested).
