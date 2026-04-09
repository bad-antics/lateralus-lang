"""
LATERALUS Language Server Protocol (LSP) v1.5.0
Provides IDE integration: diagnostics, completions, hover, go-to-definition.

Diagnostics are powered by the full compiler pipeline (lexer → parser →
semantic analysis → type checker) so real parse errors, type errors, and
semantic warnings are surfaced inline — not just text-level heuristics.

Uses stdin/stdout JSON-RPC protocol.  Works with VS Code, Neovim, Helix,
Zed, and any LSP-compliant editor.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

# --- Compiler integration (real diagnostics) --------------------------
try:
    from .compiler import Compiler, Target
    from .errors import Severity as LTLSeverity
    _HAS_COMPILER = True
except Exception:          # pragma: no cover – graceful degradation
    _HAS_COMPILER = False

log = logging.getLogger("lateralus-lsp")


# --- JSON-RPC Protocol ------------------------------------------------

@dataclass
class RPCMessage:
    """A JSON-RPC 2.0 message."""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: Optional[str] = None
    params: Optional[dict] = None
    result: Optional[Any] = None
    error: Optional[dict] = None


def read_message() -> Optional[dict]:
    """Read a JSON-RPC message from stdin."""
    headers = {}
    while True:
        line = sys.stdin.buffer.readline().decode("utf-8")
        if not line or line == "\r\n":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

    content_length = int(headers.get("Content-Length", 0))
    if content_length == 0:
        return None

    content = sys.stdin.buffer.read(content_length).decode("utf-8")
    return json.loads(content)


def send_message(msg: dict):
    """Send a JSON-RPC message to stdout."""
    content = json.dumps(msg)
    header = f"Content-Length: {len(content)}\r\n\r\n"
    sys.stdout.buffer.write(header.encode("utf-8"))
    sys.stdout.buffer.write(content.encode("utf-8"))
    sys.stdout.buffer.flush()


def send_response(request_id: int, result: Any):
    """Send a response to a request."""
    send_message({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    })


def send_notification(method: str, params: dict):
    """Send a notification (no response expected)."""
    send_message({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    })


# --- Document Manager -------------------------------------------------

@dataclass
class TextDocument:
    """An open text document."""
    uri: str
    language_id: str
    version: int
    text: str
    lines: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.lines = self.text.split("\n")

    def update(self, text: str, version: int):
        self.text = text
        self.version = version
        self.lines = text.split("\n")

    def get_line(self, line: int) -> str:
        if 0 <= line < len(self.lines):
            return self.lines[line]
        return ""

    def get_word_at(self, line: int, character: int) -> str:
        """Get the word at a given position."""
        text = self.get_line(line)
        if not text or character >= len(text):
            return ""

        # Find word boundaries
        start = character
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
            start -= 1

        end = character
        while end < len(text) and (text[end].isalnum() or text[end] == "_"):
            end += 1

        return text[start:end]


class DocumentManager:
    """Manages open documents."""

    def __init__(self):
        self.documents: dict[str, TextDocument] = {}

    def open(self, uri: str, language_id: str, version: int, text: str):
        self.documents[uri] = TextDocument(uri, language_id, version, text)

    def update(self, uri: str, text: str, version: int):
        if uri in self.documents:
            self.documents[uri].update(text, version)

    def close(self, uri: str):
        self.documents.pop(uri, None)

    def get(self, uri: str) -> Optional[TextDocument]:
        return self.documents.get(uri)


# --- LATERALUS Language Intelligence ----------------------------------

# Keywords for completion
LATERALUS_KEYWORDS = [
    "fn", "let", "const", "if", "else", "for", "while", "return",
    "match", "struct", "enum", "interface", "impl", "import", "from", "as", "in",
    "throw", "try", "catch", "emit", "probe", "measure", "pass",
    "break", "continue", "and", "or", "not", "true", "false", "none",
    "type", "trait", "where", "pub", "async", "await", "yield",
]

# Built-in functions
LATERALUS_BUILTINS = {
    "println": {"detail": "fn println(value: any)", "doc": "Print a value followed by newline"},
    "print": {"detail": "fn print(value: any)", "doc": "Print a value without newline"},
    "len": {"detail": "fn len(collection: any) -> int", "doc": "Return length of collection"},
    "str": {"detail": "fn str(value: any) -> str", "doc": "Convert to string"},
    "int": {"detail": "fn int(value: any) -> int", "doc": "Convert to integer"},
    "float": {"detail": "fn float(value: any) -> float", "doc": "Convert to float"},
    "type": {"detail": "fn type(value: any) -> str", "doc": "Return type name"},
    "range": {"detail": "fn range(start: int, end: int, step?: int) -> list", "doc": "Generate integer range"},
    "map": {"detail": "fn map(fn: callable, list: list) -> list", "doc": "Apply function to each element"},
    "filter": {"detail": "fn filter(fn: callable, list: list) -> list", "doc": "Keep elements matching predicate"},
    "reduce": {"detail": "fn reduce(fn: callable, list: list, init: any) -> any", "doc": "Reduce list to single value"},
    "sort": {"detail": "fn sort(list: list) -> list", "doc": "Return sorted copy of list"},
    "reverse": {"detail": "fn reverse(list: list) -> list", "doc": "Return reversed copy of list"},
    "zip": {"detail": "fn zip(a: list, b: list) -> list", "doc": "Zip two lists together"},
    "enumerate": {"detail": "fn enumerate(list: list) -> list", "doc": "Enumerate with index-value pairs"},
    "sum": {"detail": "fn sum(list: list) -> number", "doc": "Sum all elements"},
    "min": {"detail": "fn min(a: any, b: any) -> any", "doc": "Return minimum value"},
    "max": {"detail": "fn max(a: any, b: any) -> any", "doc": "Return maximum value"},
    "abs": {"detail": "fn abs(n: number) -> number", "doc": "Absolute value"},
    "sqrt": {"detail": "fn sqrt(n: number) -> float", "doc": "Square root"},
    "keys": {"detail": "fn keys(map: map) -> list", "doc": "Get map keys"},
    "values": {"detail": "fn values(map: map) -> list", "doc": "Get map values"},
    "split": {"detail": "fn split(s: str, sep: str) -> list", "doc": "Split string by separator"},
    "join": {"detail": "fn join(list: list, sep: str) -> str", "doc": "Join list with separator"},
    "contains": {"detail": "fn contains(collection: any, item: any) -> bool", "doc": "Check if item is in collection"},
    "assert_eq": {"detail": "fn assert_eq(a: any, b: any)", "doc": "Assert two values are equal"},
    "hash_sha256": {"detail": "fn hash_sha256(data: str) -> str", "doc": "SHA-256 hash"},
    "hash_blake2b": {"detail": "fn hash_blake2b(data: str) -> str", "doc": "BLAKE2b hash"},
    "random_token": {"detail": "fn random_token(length?: int) -> str", "doc": "Generate random hex token"},
    "base64_encode": {"detail": "fn base64_encode(data: str) -> str", "doc": "Base64 encode"},
    "base64_decode": {"detail": "fn base64_decode(data: str) -> str", "doc": "Base64 decode"},
}

# Type annotations
LATERALUS_TYPES = [
    "int", "float", "str", "bool", "list", "map", "any", "none", "void",
    "Result", "Option", "Iterator", "Comparable", "Hashable",
]

# Snippet completions
LATERALUS_SNIPPETS = {
    "fn": {
        "label": "fn (function)",
        "insertText": "fn ${1:name}(${2:params}) {\n    ${0}\n}",
        "doc": "Define a new function",
    },
    "for": {
        "label": "for (loop)",
        "insertText": "for ${1:item} in ${2:collection} {\n    ${0}\n}",
        "doc": "For-in loop",
    },
    "if": {
        "label": "if (conditional)",
        "insertText": "if ${1:condition} {\n    ${0}\n}",
        "doc": "If statement",
    },
    "match": {
        "label": "match (pattern matching)",
        "insertText": "match ${1:expr} {\n    ${2:pattern} => { ${0} },\n}",
        "doc": "Pattern matching",
    },
    "struct": {
        "label": "struct (data type)",
        "insertText": "struct ${1:Name} {\n    ${2:field}: ${3:type},\n}",
        "doc": "Define a struct",
    },
    "pipe": {
        "label": "|> (pipeline)",
        "insertText": "|> ${1:transform}(${0})",
        "doc": "Pipeline operator",
    },
    "try": {
        "label": "try-catch",
        "insertText": "try {\n    ${1}\n} catch ${2:e} {\n    ${0}\n}",
        "doc": "Try-catch error handling",
    },
    "test": {
        "label": "@test fn",
        "insertText": "@test\nfn test_${1:name}() {\n    ${0}\n}",
        "doc": "Test function",
    },
    "enum": {
        "label": "enum (algebraic type)",
        "insertText": "enum ${1:Name} {\n    ${2:Variant}(${3:type}),\n}",
        "doc": "Define an algebraic data type",
    },
    "result": {
        "label": "Result match",
        "insertText": "match ${1:expr} {\n    Result::Ok(val) => { ${2} },\n    Result::Err(e) => { ${0} },\n}",
        "doc": "Match on Result type",
    },
    "option": {
        "label": "Option match",
        "insertText": "match ${1:expr} {\n    Option::Some(val) => { ${2} },\n    Option::None => { ${0} },\n}",
        "doc": "Match on Option type",
    },
    "impl": {
        "label": "impl (implementation)",
        "insertText": "impl ${1:Type} {\n    fn ${2:method}(self${3}) {\n        ${0}\n    }\n}",
        "doc": "Implement methods on a type",
    },
}


def collect_diagnostics(doc: TextDocument) -> list[dict]:
    """Analyze document using the full LATERALUS compiler pipeline.

    Pipeline: Lex → Parse → Semantic analysis → type errors.
    Falls back to lightweight text heuristics when the compiler
    is unavailable (e.g. circular-import edge cases).
    """
    diagnostics: list[dict] = []

    # -- Compiler-powered diagnostics --------------------------------------
    if _HAS_COMPILER:
        try:
            cc = Compiler()
            result = cc.compile_source(doc.text, filename=doc.uri,
                                       target=Target.CHECK)

            # Map compiler severity → LSP severity int
            _sev_map = {
                LTLSeverity.FATAL:   1,   # LSP Error
                LTLSeverity.ERROR:   1,   # LSP Error
                LTLSeverity.WARNING: 2,   # LSP Warning
                LTLSeverity.INFO:    3,   # LSP Information
                LTLSeverity.HINT:    4,   # LSP Hint
            }

            for ctx in result.errors + result.warnings:
                line = max(0, ctx.line - 1)            # LSP is 0-based
                col  = max(0, ctx.col)
                end_col = col + max(1, len(ctx.source_line.strip())) \
                    if ctx.source_line else col + 1
                sev = _sev_map.get(ctx.severity, 1)

                diag: dict = {
                    "range": {
                        "start": {"line": line, "character": col},
                        "end":   {"line": line, "character": end_col},
                    },
                    "severity": sev,
                    "source": "lateralus",
                    "code": ctx.code,
                    "message": ctx.message,
                }
                if ctx.suggestion:
                    diag["message"] += f"\n💡 {ctx.suggestion}"
                diagnostics.append(diag)

        except Exception as exc:
            log.debug("Compiler diagnostic pass failed: %s", exc)
            # Fall through to lightweight checks below

    # -- Lightweight / supplementary heuristics ----------------------------
    for i, line in enumerate(doc.lines):
        stripped = line.strip()

        # 'var' keyword is deprecated
        if stripped.startswith("var "):
            diagnostics.append({
                "range": {
                    "start": {"line": i, "character": 0},
                    "end": {"line": i, "character": 3},
                },
                "severity": 2,  # Warning
                "source": "lateralus",
                "message": "Use 'let' instead of 'var' for variable declarations",
            })

        # Trailing semicolons
        if stripped.endswith(";") and not stripped.startswith("//"):
            diagnostics.append({
                "range": {
                    "start": {"line": i, "character": len(line) - 1},
                    "end": {"line": i, "character": len(line)},
                },
                "severity": 3,  # Information
                "source": "lateralus",
                "message": "Semicolons are optional in LATERALUS",
            })

    return diagnostics


def get_completions(doc: TextDocument, line: int, character: int) -> list[dict]:
    """Get completion items at position."""
    items = []
    prefix = doc.get_word_at(line, character).lower()

    # Keyword completions
    for kw in LATERALUS_KEYWORDS:
        if kw.startswith(prefix) or not prefix:
            items.append({
                "label": kw,
                "kind": 14,  # Keyword
                "detail": f"keyword: {kw}",
            })

    # Built-in function completions
    for name, info in LATERALUS_BUILTINS.items():
        if name.startswith(prefix) or not prefix:
            items.append({
                "label": name,
                "kind": 3,  # Function
                "detail": info["detail"],
                "documentation": info["doc"],
            })

    # Snippet completions
    for trigger, snippet in LATERALUS_SNIPPETS.items():
        if trigger.startswith(prefix) or not prefix:
            items.append({
                "label": snippet["label"],
                "kind": 15,  # Snippet
                "insertText": snippet["insertText"],
                "insertTextFormat": 2,  # Snippet format
                "documentation": snippet["doc"],
            })

    # Type completions (if after colon)
    line_text = doc.get_line(line)
    before_cursor = line_text[:character]
    if re.search(r":\s*\w*$", before_cursor):
        for t in LATERALUS_TYPES:
            if t.startswith(prefix) or not prefix:
                items.append({
                    "label": t,
                    "kind": 7,  # Class (used for types)
                    "detail": f"type: {t}",
                })

    return items


def get_hover(doc: TextDocument, line: int, character: int) -> Optional[dict]:
    """Get hover information at position."""
    word = doc.get_word_at(line, character)
    if not word:
        return None

    # Check builtins
    if word in LATERALUS_BUILTINS:
        info = LATERALUS_BUILTINS[word]
        return {
            "contents": {
                "kind": "markdown",
                "value": f"```lateralus\n{info['detail']}\n```\n\n{info['doc']}",
            },
        }

    # Check keywords
    keyword_docs = {
        "fn": "Define a function.\n```lateralus\nfn name(params) -> return_type { body }\n```",
        "let": "Declare a mutable variable.\n```lateralus\nlet x = value\n```",
        "const": "Declare an immutable constant.\n```lateralus\nconst PI = 3.14159\n```",
        "struct": "Define a data structure.\n```lateralus\nstruct Point { x: float, y: float }\n```",
        "enum": "Define an algebraic data type.\n```lateralus\nenum Option {\n    Some(value: any),\n    None,\n}\n```",
        "trait": "Define a trait interface.\n```lateralus\ntrait Printable {\n    fn to_str(self) -> str\n}\n```",
        "impl": "Implement methods on a type.\n```lateralus\nimpl Point {\n    fn distance(self) -> float { ... }\n}\n```",
        "match": "Pattern matching expression.\n```lateralus\nmatch value { pattern => result }\n```",
        "emit": "Emit an event.\n```lateralus\nemit event_name(data)\n```",
        "probe": "Observe a reactive value.\n```lateralus\nprobe variable_name\n```",
        "measure": "Profile a code block.\n```lateralus\nmeasure \"label\" { code }\n```",
        "async": "Declare an asynchronous function.\n```lateralus\nasync fn fetch(url: str) -> str { ... }\n```",
        "await": "Await an asynchronous expression.\n```lateralus\nlet result = await fetch(url)\n```",
        "spawn": "Launch a concurrent task.\n```lateralus\nlet handle = spawn compute(data)\n```",
        "yield": "Yield a value from a generator.\n```lateralus\nyield value\n```",
    }

    if word in keyword_docs:
        return {
            "contents": {
                "kind": "markdown",
                "value": keyword_docs[word],
            },
        }

    return None


# --- Document Symbols -------------------------------------------------

# LSP SymbolKind constants
_SK_FUNCTION   = 12
_SK_VARIABLE   = 13
_SK_CLASS      = 5    # used for struct
_SK_INTERFACE  = 11   # used for trait
_SK_ENUM       = 10
_SK_MODULE     = 2
_SK_CONSTANT   = 14
_SK_METHOD     = 6

# Regex patterns for symbol extraction
_RE_FN       = re.compile(r"^(\s*)(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\(")
_RE_STRUCT   = re.compile(r"^(\s*)(?:pub\s+)?struct\s+(\w+)")
_RE_ENUM     = re.compile(r"^(\s*)(?:pub\s+)?enum\s+(\w+)")
_RE_TRAIT    = re.compile(r"^(\s*)(?:pub\s+)?trait\s+(\w+)")
_RE_IMPL     = re.compile(r"^(\s*)impl\s+(\w+)")
_RE_LET      = re.compile(r"^(\s*)let\s+(?:mut\s+)?(\w+)")
_RE_CONST    = re.compile(r"^(\s*)const\s+(\w+)")
_RE_TYPE     = re.compile(r"^(\s*)(?:pub\s+)?type\s+(\w+)")
_RE_IMPORT   = re.compile(r"^(\s*)import\s+(\w+)")
_RE_FROM_IMP = re.compile(r"^(\s*)from\s+\S+\s+import\s+(.+)")


def get_document_symbols(doc: TextDocument) -> list[dict]:
    """Extract document symbols for outline / breadcrumbs."""
    symbols: list[dict] = []
    current_container: Optional[dict] = None  # for methods inside impl/struct

    for i, line in enumerate(doc.lines):
        stripped = line.strip()

        # Functions (top-level and methods)
        m = _RE_FN.match(line)
        if m:
            indent, name = m.group(1), m.group(2)
            kind = _SK_METHOD if len(indent) > 0 and current_container else _SK_FUNCTION
            sym = _make_symbol(name, kind, i, 0, i, len(line))
            if current_container and len(indent) > 0:
                current_container.setdefault("children", []).append(sym)
            else:
                symbols.append(sym)
            continue

        # Structs
        m = _RE_STRUCT.match(line)
        if m:
            sym = _make_symbol(m.group(2), _SK_CLASS, i, 0, i, len(line))
            symbols.append(sym)
            current_container = sym
            continue

        # Enums
        m = _RE_ENUM.match(line)
        if m:
            sym = _make_symbol(m.group(2), _SK_ENUM, i, 0, i, len(line))
            symbols.append(sym)
            current_container = sym
            continue

        # Traits
        m = _RE_TRAIT.match(line)
        if m:
            sym = _make_symbol(m.group(2), _SK_INTERFACE, i, 0, i, len(line))
            symbols.append(sym)
            current_container = sym
            continue

        # Impl blocks
        m = _RE_IMPL.match(line)
        if m:
            sym = _make_symbol(f"impl {m.group(2)}", _SK_CLASS, i, 0, i, len(line))
            symbols.append(sym)
            current_container = sym
            continue

        # Let bindings (top-level only)
        m = _RE_LET.match(line)
        if m and not m.group(1):  # no indent = top-level
            symbols.append(_make_symbol(m.group(2), _SK_VARIABLE, i, 0, i, len(line)))
            continue

        # Constants
        m = _RE_CONST.match(line)
        if m:
            symbols.append(_make_symbol(m.group(2), _SK_CONSTANT, i, 0, i, len(line)))
            continue

        # Type aliases
        m = _RE_TYPE.match(line)
        if m:
            symbols.append(_make_symbol(m.group(2), _SK_CLASS, i, 0, i, len(line)))
            continue

        # Imports
        m = _RE_IMPORT.match(line)
        if m:
            symbols.append(_make_symbol(m.group(2), _SK_MODULE, i, 0, i, len(line)))
            continue

        # End of container block
        if stripped == "}" and current_container:
            current_container = None

    return symbols


def _make_symbol(name: str, kind: int, start_line: int, start_char: int,
                 end_line: int, end_char: int) -> dict:
    return {
        "name": name,
        "kind": kind,
        "range": {
            "start": {"line": start_line, "character": start_char},
            "end": {"line": end_line, "character": end_char},
        },
        "selectionRange": {
            "start": {"line": start_line, "character": start_char},
            "end": {"line": start_line, "character": start_char + len(name)},
        },
    }


# --- Go-to-Definition -------------------------------------------------

def get_definition(doc: TextDocument, line: int, character: int) -> Optional[dict]:
    """Find the definition of the symbol at the given position."""
    word = doc.get_word_at(line, character)
    if not word:
        return None

    # Search for definitions in the current document
    # Priority: fn > struct > enum > trait > type > let > const
    patterns = [
        (re.compile(rf"(?:pub\s+)?(?:async\s+)?fn\s+{re.escape(word)}\s*\("), word),
        (re.compile(rf"(?:pub\s+)?struct\s+{re.escape(word)}\b"), word),
        (re.compile(rf"(?:pub\s+)?enum\s+{re.escape(word)}\b"), word),
        (re.compile(rf"(?:pub\s+)?trait\s+{re.escape(word)}\b"), word),
        (re.compile(rf"(?:pub\s+)?type\s+{re.escape(word)}\b"), word),
        (re.compile(rf"let\s+(?:mut\s+)?{re.escape(word)}\b"), word),
        (re.compile(rf"const\s+{re.escape(word)}\b"), word),
    ]

    for i, text in enumerate(doc.lines):
        for pat, _name in patterns:
            m = pat.search(text)
            if m:
                col = m.start()
                # Don't return self-reference
                if i == line:
                    continue
                return {
                    "uri": doc.uri,
                    "range": {
                        "start": {"line": i, "character": col},
                        "end": {"line": i, "character": col + len(word)},
                    },
                }

    return None


# --- Find References --------------------------------------------------

def get_references(doc: TextDocument, line: int, character: int,
                   include_decl: bool = True) -> list[dict]:
    """Find all references to the symbol at the given position."""
    word = doc.get_word_at(line, character)
    if not word:
        return []

    refs = []
    pattern = re.compile(rf"\b{re.escape(word)}\b")

    for i, text in enumerate(doc.lines):
        for m in pattern.finditer(text):
            if not include_decl and i == line and m.start() <= character < m.end():
                continue
            refs.append({
                "uri": doc.uri,
                "range": {
                    "start": {"line": i, "character": m.start()},
                    "end": {"line": i, "character": m.end()},
                },
            })

    return refs


# --- Signature Help ---------------------------------------------------

def get_signature_help(doc: TextDocument, line: int, character: int) -> Optional[dict]:
    """Provide signature help when inside function call parens."""
    line_text = doc.get_line(line)
    before = line_text[:character]

    # Find the function name before the opening paren
    # Walk backwards to find the matching '('
    paren_depth = 0
    comma_count = 0
    fn_end = -1

    for idx in range(len(before) - 1, -1, -1):
        ch = before[idx]
        if ch == ')':
            paren_depth += 1
        elif ch == '(':
            if paren_depth > 0:
                paren_depth -= 1
            else:
                fn_end = idx
                break
        elif ch == ',' and paren_depth == 0:
            comma_count += 1

    if fn_end < 0:
        return None

    # Extract function name
    fn_name_end = fn_end
    fn_name_start = fn_name_end - 1
    while fn_name_start >= 0 and (before[fn_name_start].isalnum() or before[fn_name_start] == '_'):
        fn_name_start -= 1
    fn_name_start += 1
    fn_name = before[fn_name_start:fn_name_end]

    if not fn_name:
        return None

    # Look up in builtins
    if fn_name in LATERALUS_BUILTINS:
        info = LATERALUS_BUILTINS[fn_name]
        return {
            "signatures": [{
                "label": info["detail"],
                "documentation": info["doc"],
                "activeParameter": comma_count,
            }],
            "activeSignature": 0,
            "activeParameter": comma_count,
        }

    # Look up user-defined functions in the document
    fn_pat = re.compile(rf"(?:pub\s+)?(?:async\s+)?fn\s+{re.escape(fn_name)}\s*\(([^)]*)\)")
    for text in doc.lines:
        m = fn_pat.search(text)
        if m:
            params_str = m.group(1)
            sig_label = f"fn {fn_name}({params_str})"
            # Check for return type
            rest = text[m.end():]
            ret_match = re.match(r"\s*->\s*(\S+)", rest)
            if ret_match:
                sig_label += f" -> {ret_match.group(1)}"
            return {
                "signatures": [{
                    "label": sig_label,
                    "activeParameter": comma_count,
                }],
                "activeSignature": 0,
                "activeParameter": comma_count,
            }

    return None


# --- LSP Server --------------------------------------------------------

class LateralusLSP:
    """The LATERALUS Language Server."""

    def __init__(self):
        self.documents = DocumentManager()
        self.initialized = False
        self.shutdown_requested = False

    def handle_message(self, msg: dict) -> Optional[dict]:
        """Handle an incoming JSON-RPC message."""
        method = msg.get("method", "")
        params = msg.get("params", {})
        msg_id = msg.get("id")

        # Requests (expect response)
        if method == "initialize":
            return self.handle_initialize(msg_id, params)
        elif method == "shutdown":
            self.shutdown_requested = True
            return {"jsonrpc": "2.0", "id": msg_id, "result": None}
        elif method == "textDocument/completion":
            return self.handle_completion(msg_id, params)
        elif method == "textDocument/hover":
            return self.handle_hover(msg_id, params)
        elif method == "textDocument/documentSymbol":
            return self.handle_document_symbols(msg_id, params)
        elif method == "textDocument/definition":
            return self.handle_definition(msg_id, params)
        elif method == "textDocument/references":
            return self.handle_references(msg_id, params)
        elif method == "textDocument/signatureHelp":
            return self.handle_signature_help(msg_id, params)
        elif method == "textDocument/formatting":
            return self.handle_formatting(msg_id, params)
        elif method == "textDocument/codeAction":
            return self.handle_code_action(msg_id, params)
        elif method == "textDocument/rename":
            return self.handle_rename(msg_id, params)
        elif method == "textDocument/prepareRename":
            return self.handle_prepare_rename(msg_id, params)

        # Notifications (no response)
        elif method == "initialized":
            self.initialized = True
        elif method == "exit":
            sys.exit(0 if self.shutdown_requested else 1)
        elif method == "textDocument/didOpen":
            self.handle_did_open(params)
        elif method == "textDocument/didChange":
            self.handle_did_change(params)
        elif method == "textDocument/didClose":
            self.handle_did_close(params)

        return None

    def handle_initialize(self, msg_id: int, params: dict) -> dict:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "capabilities": {
                    "textDocumentSync": {
                        "openClose": True,
                        "change": 1,  # Full sync
                    },
                    "completionProvider": {
                        "triggerCharacters": [".", "|", "@", ":"],
                        "resolveProvider": False,
                    },
                    "hoverProvider": True,
                    "documentSymbolProvider": True,
                    "definitionProvider": True,
                    "referencesProvider": True,
                    "signatureHelpProvider": {
                        "triggerCharacters": ["(", ","],
                    },
                    "documentFormattingProvider": True,
                    "codeActionProvider": {
                        "codeActionKinds": [
                            "quickfix",
                            "refactor",
                        ],
                    },
                    "renameProvider": {
                        "prepareProvider": True,
                    },
                    "diagnosticProvider": {
                        "interFileDependencies": False,
                        "workspaceDiagnostics": False,
                    },
                },
                "serverInfo": {
                    "name": "lateralus-lsp",
                    "version": "2.4.0",
                },
            },
        }

    def handle_completion(self, msg_id: int, params: dict) -> dict:
        """Handle completion request."""
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        doc = self.documents.get(uri)

        items = []
        if doc:
            items = get_completions(doc, pos["line"], pos["character"])

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"isIncomplete": False, "items": items},
        }

    def handle_hover(self, msg_id: int, params: dict) -> dict:
        """Handle hover request."""
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        doc = self.documents.get(uri)

        hover = None
        if doc:
            hover = get_hover(doc, pos["line"], pos["character"])

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": hover,
        }

    def handle_document_symbols(self, msg_id: int, params: dict) -> dict:
        """Handle textDocument/documentSymbol request."""
        uri = params["textDocument"]["uri"]
        doc = self.documents.get(uri)
        symbols = get_document_symbols(doc) if doc else []
        return {"jsonrpc": "2.0", "id": msg_id, "result": symbols}

    def handle_definition(self, msg_id: int, params: dict) -> dict:
        """Handle textDocument/definition request."""
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        doc = self.documents.get(uri)
        result = get_definition(doc, pos["line"], pos["character"]) if doc else None
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def handle_references(self, msg_id: int, params: dict) -> dict:
        """Handle textDocument/references request."""
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        ctx = params.get("context", {})
        doc = self.documents.get(uri)
        refs = get_references(doc, pos["line"], pos["character"],
                              include_decl=ctx.get("includeDeclaration", True)) if doc else []
        return {"jsonrpc": "2.0", "id": msg_id, "result": refs}

    def handle_signature_help(self, msg_id: int, params: dict) -> dict:
        """Handle textDocument/signatureHelp request."""
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        doc = self.documents.get(uri)
        result = get_signature_help(doc, pos["line"], pos["character"]) if doc else None
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def handle_formatting(self, msg_id: int, params: dict) -> dict:
        """Handle textDocument/formatting request."""
        uri = params["textDocument"]["uri"]
        doc = self.documents.get(uri)
        if not doc:
            return {"jsonrpc": "2.0", "id": msg_id, "result": []}
        try:
            from .formatter import FormatConfig, LateralusFormatter
            config = FormatConfig()
            opts = params.get("options", {})
            if "tabSize" in opts:
                config.indent_size = opts["tabSize"]
            formatted = LateralusFormatter(config).format(doc.text)
            if formatted == doc.text:
                return {"jsonrpc": "2.0", "id": msg_id, "result": []}
            # Return a single TextEdit covering the whole document
            last_line = len(doc.lines) - 1
            last_char = len(doc.lines[-1]) if doc.lines else 0
            edits = [{
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": last_line, "character": last_char},
                },
                "newText": formatted,
            }]
            return {"jsonrpc": "2.0", "id": msg_id, "result": edits}
        except Exception:
            return {"jsonrpc": "2.0", "id": msg_id, "result": []}

    def handle_code_action(self, msg_id: int, params: dict) -> dict:
        """Handle textDocument/codeAction request — provide quick fixes."""
        uri = params["textDocument"]["uri"]
        range_ = params["range"]
        context = params.get("context", {})
        doc = self.documents.get(uri)
        actions = []

        if not doc:
            return {"jsonrpc": "2.0", "id": msg_id, "result": actions}

        diagnostics = context.get("diagnostics", [])

        for diag in diagnostics:
            msg = diag.get("message", "")
            start = diag.get("range", {}).get("start", {})
            line_num = start.get("line", 0)

            if line_num >= len(doc.lines):
                continue
            line_text = doc.lines[line_num]

            # Quick fix: use 'let' instead of 'var'
            if "Use 'let' instead of 'var'" in msg:
                new_text = line_text.replace("var ", "let ", 1)
                actions.append({
                    "title": "Replace 'var' with 'let'",
                    "kind": "quickfix",
                    "diagnostics": [diag],
                    "edit": {
                        "changes": {
                            uri: [{
                                "range": {
                                    "start": {"line": line_num, "character": 0},
                                    "end": {"line": line_num,
                                            "character": len(line_text)},
                                },
                                "newText": new_text,
                            }],
                        },
                    },
                })

            # Quick fix: remove unnecessary semicolon
            elif "Unnecessary semicolon" in msg:
                new_text = line_text.rstrip().rstrip(";")
                actions.append({
                    "title": "Remove semicolon",
                    "kind": "quickfix",
                    "diagnostics": [diag],
                    "edit": {
                        "changes": {
                            uri: [{
                                "range": {
                                    "start": {"line": line_num, "character": 0},
                                    "end": {"line": line_num,
                                            "character": len(line_text)},
                                },
                                "newText": new_text,
                            }],
                        },
                    },
                })

            # Quick fix: prefix unused variable with underscore
            elif "is defined but never used" in msg:
                import re as _re
                m = _re.search(r"Variable '(\w+)'", msg)
                if m:
                    var_name = m.group(1)
                    new_text = line_text.replace(var_name, f"_{var_name}", 1)
                    actions.append({
                        "title": f"Rename to '_{var_name}'",
                        "kind": "quickfix",
                        "diagnostics": [diag],
                        "edit": {
                            "changes": {
                                uri: [{
                                    "range": {
                                        "start": {"line": line_num, "character": 0},
                                        "end": {"line": line_num,
                                                "character": len(line_text)},
                                    },
                                    "newText": new_text,
                                }],
                            },
                        },
                    })

            # Quick fix: remove duplicate import
            elif "already imported" in msg:
                actions.append({
                    "title": "Remove duplicate import",
                    "kind": "quickfix",
                    "diagnostics": [diag],
                    "edit": {
                        "changes": {
                            uri: [{
                                "range": {
                                    "start": {"line": line_num, "character": 0},
                                    "end": {"line": line_num + 1, "character": 0},
                                },
                                "newText": "",
                            }],
                        },
                    },
                })

        return {"jsonrpc": "2.0", "id": msg_id, "result": actions}

    def handle_rename(self, msg_id: int, params: dict) -> dict:
        """Handle textDocument/rename request."""
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        new_name = params["newName"]
        doc = self.documents.get(uri)

        if not doc:
            return {"jsonrpc": "2.0", "id": msg_id, "result": None}

        # Find the word at position
        line_num = pos["line"]
        col = pos["character"]
        if line_num >= len(doc.lines):
            return {"jsonrpc": "2.0", "id": msg_id, "result": None}

        line_text = doc.lines[line_num]
        import re as _re

        # Find word boundaries around cursor
        old_name = None
        for m in _re.finditer(r"\b([a-zA-Z_]\w*)\b", line_text):
            if m.start() <= col <= m.end():
                old_name = m.group(1)
                break

        if not old_name:
            return {"jsonrpc": "2.0", "id": msg_id, "result": None}

        # Find all occurrences in the document
        edits = []
        for i, ln in enumerate(doc.lines):
            for m in _re.finditer(r"\b" + _re.escape(old_name) + r"\b", ln):
                edits.append({
                    "range": {
                        "start": {"line": i, "character": m.start()},
                        "end": {"line": i, "character": m.end()},
                    },
                    "newText": new_name,
                })

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "changes": {uri: edits},
            },
        }

    def handle_prepare_rename(self, msg_id: int, params: dict) -> dict:
        """Handle textDocument/prepareRename — validate rename is possible."""
        uri = params["textDocument"]["uri"]
        pos = params["position"]
        doc = self.documents.get(uri)

        if not doc:
            return {"jsonrpc": "2.0", "id": msg_id, "result": None}

        line_num = pos["line"]
        col = pos["character"]
        if line_num >= len(doc.lines):
            return {"jsonrpc": "2.0", "id": msg_id, "result": None}

        line_text = doc.lines[line_num]
        import re as _re

        for m in _re.finditer(r"\b([a-zA-Z_]\w*)\b", line_text):
            if m.start() <= col <= m.end():
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "range": {
                            "start": {"line": line_num, "character": m.start()},
                            "end": {"line": line_num, "character": m.end()},
                        },
                        "placeholder": m.group(1),
                    },
                }

        return {"jsonrpc": "2.0", "id": msg_id, "result": None}

    def handle_did_open(self, params: dict):
        """Handle textDocument/didOpen notification."""
        td = params["textDocument"]
        self.documents.open(td["uri"], td.get("languageId", "lateralus"),
                           td.get("version", 0), td["text"])

        # Publish diagnostics
        doc = self.documents.get(td["uri"])
        if doc:
            diagnostics = collect_diagnostics(doc)
            send_notification("textDocument/publishDiagnostics", {
                "uri": td["uri"],
                "diagnostics": diagnostics,
            })

    def handle_did_change(self, params: dict):
        """Handle textDocument/didChange notification."""
        uri = params["textDocument"]["uri"]
        version = params["textDocument"].get("version", 0)

        for change in params.get("contentChanges", []):
            self.documents.update(uri, change["text"], version)

        # Re-publish diagnostics
        doc = self.documents.get(uri)
        if doc:
            diagnostics = collect_diagnostics(doc)
            send_notification("textDocument/publishDiagnostics", {
                "uri": uri,
                "diagnostics": diagnostics,
            })

    def handle_did_close(self, params: dict):
        """Handle textDocument/didClose notification."""
        uri = params["textDocument"]["uri"]
        self.documents.close(uri)
        # Clear diagnostics
        send_notification("textDocument/publishDiagnostics", {
            "uri": uri,
            "diagnostics": [],
        })

    def run(self):
        """Main server loop."""
        while True:
            msg = read_message()
            if msg is None:
                continue

            response = self.handle_message(msg)
            if response:
                send_message(response)


def main():
    """Start the LATERALUS LSP server."""
    server = LateralusLSP()
    server.run()


if __name__ == "__main__":
    main()
