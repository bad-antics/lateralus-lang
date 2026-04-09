"""
Tests for the LATERALUS LSP server.
"""
from lateralus_lang.lsp_server import (
    DocumentManager,
    LateralusLSP,
    TextDocument,
    collect_diagnostics,
    get_completions,
    get_definition,
    get_document_symbols,
    get_hover,
    get_references,
    get_signature_help,
)


class TestTextDocument:
    def test_create(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "let x = 42\nprintln(x)")
        assert len(doc.lines) == 2
        assert doc.get_line(0) == "let x = 42"
        assert doc.get_line(1) == "println(x)"

    def test_get_word_at(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "let x = 42")
        assert doc.get_word_at(0, 0) == "let"
        assert doc.get_word_at(0, 4) == "x"

    def test_update(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "let x = 1")
        doc.update("let x = 2\nlet y = 3", 2)
        assert doc.version == 2
        assert len(doc.lines) == 2

    def test_get_line_out_of_range(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "hello")
        assert doc.get_line(999) == ""

    def test_get_word_at_edge(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "")
        assert doc.get_word_at(0, 0) == ""


class TestDocumentManager:
    def test_open_and_get(self):
        dm = DocumentManager()
        dm.open("file:///a.ltl", "lateralus", 1, "hello")
        doc = dm.get("file:///a.ltl")
        assert doc is not None
        assert doc.text == "hello"

    def test_close(self):
        dm = DocumentManager()
        dm.open("file:///a.ltl", "lateralus", 1, "hello")
        dm.close("file:///a.ltl")
        assert dm.get("file:///a.ltl") is None

    def test_update(self):
        dm = DocumentManager()
        dm.open("file:///a.ltl", "lateralus", 1, "old")
        dm.update("file:///a.ltl", "new", 2)
        doc = dm.get("file:///a.ltl")
        assert doc.text == "new"
        assert doc.version == 2


class TestDiagnostics:
    def test_var_warning(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "var x = 42")
        diagnostics = collect_diagnostics(doc)
        assert len(diagnostics) >= 1
        assert "let" in diagnostics[0]["message"]

    def test_semicolon_info(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "let x = 42;")
        diagnostics = collect_diagnostics(doc)
        semi_diags = [d for d in diagnostics if "Semicolon" in d["message"] or "emicolon" in d["message"]]
        assert len(semi_diags) >= 1

    def test_clean_code(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "let x = 42\nprintln(x)")
        diagnostics = collect_diagnostics(doc)
        # Should have no errors (warnings possible but no actual errors)
        errors = [d for d in diagnostics if d.get("severity") == 1]
        assert len(errors) == 0


class TestCompletions:
    def test_keyword_completion(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "f")
        items = get_completions(doc, 0, 1)
        labels = [i["label"] for i in items]
        assert "fn" in labels or any("fn" in l for l in labels)

    def test_builtin_completion(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "pri")
        items = get_completions(doc, 0, 3)
        labels = [i["label"] for i in items]
        assert "println" in labels

    def test_type_completion_after_colon(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "let x: i")
        items = get_completions(doc, 0, 8)
        labels = [i["label"] for i in items]
        assert "int" in labels

    def test_all_completions(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "")
        items = get_completions(doc, 0, 0)
        assert len(items) > 0


class TestHover:
    def test_keyword_hover(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "fn hello() {}")
        hover = get_hover(doc, 0, 0)
        assert hover is not None
        assert "function" in hover["contents"]["value"].lower()

    def test_builtin_hover(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "println(42)")
        hover = get_hover(doc, 0, 3)
        assert hover is not None
        assert "print" in hover["contents"]["value"].lower()

    def test_unknown_hover(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "xyz123")
        hover = get_hover(doc, 0, 3)
        assert hover is None


class TestLSPServer:
    def test_initialize(self):
        server = LateralusLSP()
        response = server.handle_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })
        assert response is not None
        assert response["result"]["capabilities"]["completionProvider"]
        assert response["result"]["serverInfo"]["name"] == "lateralus-lsp"

    def test_shutdown(self):
        server = LateralusLSP()
        response = server.handle_message({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "shutdown",
            "params": {},
        })
        assert response["result"] is None
        assert server.shutdown_requested

    def test_did_open(self):
        server = LateralusLSP()
        server.handle_message({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test.ltl",
                    "languageId": "lateralus",
                    "version": 1,
                    "text": "let x = 42",
                },
            },
        })
        doc = server.documents.get("file:///test.ltl")
        assert doc is not None

    def test_completion_request(self):
        server = LateralusLSP()
        # Open a document first
        server.handle_message({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test.ltl",
                    "languageId": "lateralus",
                    "version": 1,
                    "text": "fn",
                },
            },
        })
        # Request completions
        response = server.handle_message({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "textDocument/completion",
            "params": {
                "textDocument": {"uri": "file:///test.ltl"},
                "position": {"line": 0, "character": 2},
            },
        })
        assert response is not None
        assert "items" in response["result"]

    def test_hover_request(self):
        server = LateralusLSP()
        server.handle_message({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test.ltl",
                    "languageId": "lateralus",
                    "version": 1,
                    "text": "println(42)",
                },
            },
        })
        response = server.handle_message({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": "file:///test.ltl"},
                "position": {"line": 0, "character": 3},
            },
        })
        assert response is not None


# --- Document Symbols -------------------------------------------------

class TestDocumentSymbols:
    """Tests for textDocument/documentSymbol (outline / breadcrumbs)."""

    def _doc(self, source: str) -> TextDocument:
        return TextDocument("file:///test.ltl", "lateralus", 1, source)

    def test_function_symbol(self):
        syms = get_document_symbols(self._doc("fn greet(name: str) {\n    println(name)\n}"))
        names = [s["name"] for s in syms]
        assert "greet" in names
        assert syms[0]["kind"] == 12  # Function

    def test_struct_symbol(self):
        syms = get_document_symbols(self._doc("struct Point {\n    x: float\n    y: float\n}"))
        assert syms[0]["name"] == "Point"
        assert syms[0]["kind"] == 5  # Class (struct)

    def test_enum_symbol(self):
        syms = get_document_symbols(self._doc("enum Color {\n    Red,\n    Green,\n}"))
        assert syms[0]["name"] == "Color"
        assert syms[0]["kind"] == 10  # Enum

    def test_trait_symbol(self):
        syms = get_document_symbols(self._doc("trait Printable {\n    fn to_str(self) -> str\n}"))
        assert syms[0]["name"] == "Printable"
        assert syms[0]["kind"] == 11  # Interface

    def test_const_symbol(self):
        syms = get_document_symbols(self._doc("const PI = 3.14159"))
        assert syms[0]["name"] == "PI"
        assert syms[0]["kind"] == 14  # Constant

    def test_let_top_level(self):
        syms = get_document_symbols(self._doc("let counter = 0"))
        assert syms[0]["name"] == "counter"
        assert syms[0]["kind"] == 13  # Variable

    def test_impl_block(self):
        src = "impl Point {\n    fn distance(self) -> float {\n        return 0.0\n    }\n}"
        syms = get_document_symbols(self._doc(src))
        names = [s["name"] for s in syms]
        assert "impl Point" in names

    def test_pub_fn_symbol(self):
        syms = get_document_symbols(self._doc("pub fn hello() {\n}"))
        assert syms[0]["name"] == "hello"

    def test_async_fn_symbol(self):
        syms = get_document_symbols(self._doc("async fn fetch(url: str) {\n}"))
        assert syms[0]["name"] == "fetch"

    def test_pub_struct_symbol(self):
        syms = get_document_symbols(self._doc("pub struct Config {\n    debug: bool\n}"))
        assert syms[0]["name"] == "Config"

    def test_multiple_symbols(self):
        src = "fn a() {}\nfn b() {}\nstruct C {}\nenum D {}\nconst E = 1"
        syms = get_document_symbols(self._doc(src))
        names = [s["name"] for s in syms]
        assert names == ["a", "b", "C", "D", "E"]

    def test_import_symbol(self):
        syms = get_document_symbols(self._doc("import math"))
        assert syms[0]["name"] == "math"
        assert syms[0]["kind"] == 2  # Module

    def test_type_alias_symbol(self):
        syms = get_document_symbols(self._doc("type Callback = fn"))
        assert syms[0]["name"] == "Callback"

    def test_nested_let_not_shown(self):
        src = "fn foo() {\n    let x = 42\n}"
        syms = get_document_symbols(self._doc(src))
        names = [s["name"] for s in syms]
        assert "x" not in names

    def test_empty_document(self):
        syms = get_document_symbols(self._doc(""))
        assert syms == []


# --- Go-to-Definition -------------------------------------------------

class TestDefinition:
    """Tests for textDocument/definition."""

    def _doc(self, source: str) -> TextDocument:
        return TextDocument("file:///test.ltl", "lateralus", 1, source)

    def test_find_function(self):
        doc = self._doc("fn greet(name: str) {\n    println(name)\n}\ngreet(\"hi\")")
        defn = get_definition(doc, 3, 2)  # 'greet' on the call line
        assert defn is not None
        assert defn["range"]["start"]["line"] == 0

    def test_find_let_binding(self):
        doc = self._doc("let x = 42\nprintln(x)")
        defn = get_definition(doc, 1, 9)  # 'x' on the println line
        assert defn is not None
        assert defn["range"]["start"]["line"] == 0

    def test_find_struct(self):
        doc = self._doc("struct Point {\n    x: float\n}\nlet p = Point(1.0)")
        defn = get_definition(doc, 3, 10)  # 'Point' on let line
        assert defn is not None
        assert defn["range"]["start"]["line"] == 0

    def test_find_const(self):
        doc = self._doc("const PI = 3.14\nlet r = PI")
        defn = get_definition(doc, 1, 9)
        assert defn is not None
        assert defn["range"]["start"]["line"] == 0

    def test_no_definition_for_builtin(self):
        doc = self._doc("println(42)")
        defn = get_definition(doc, 0, 3)
        assert defn is None  # println is a builtin, not in document

    def test_self_reference_skipped(self):
        doc = self._doc("fn foo() {}")
        defn = get_definition(doc, 0, 4)  # 'foo' on its own decl line
        assert defn is None  # Should skip self-reference

    def test_enum_definition(self):
        doc = self._doc("enum Color {\n    Red,\n}\nlet c = Color()")
        defn = get_definition(doc, 3, 9)
        assert defn is not None
        assert defn["range"]["start"]["line"] == 0


# --- Find References --------------------------------------------------

class TestReferences:
    """Tests for textDocument/references."""

    def _doc(self, source: str) -> TextDocument:
        return TextDocument("file:///test.ltl", "lateralus", 1, source)

    def test_basic_references(self):
        doc = self._doc("let x = 42\nprintln(x)\nlet y = x + 1")
        refs = get_references(doc, 0, 4)  # 'x'
        assert len(refs) == 3  # decl + 2 uses

    def test_no_references(self):
        doc = self._doc("let x = 42")
        refs = get_references(doc, 0, 4, include_decl=False)
        assert len(refs) == 0  # Only decl, excluded

    def test_function_references(self):
        doc = self._doc("fn greet() {}\ngreet()\ngreet()")
        refs = get_references(doc, 0, 3)
        assert len(refs) == 3  # decl + 2 calls

    def test_word_boundary(self):
        doc = self._doc("let foo = 1\nlet foobar = 2\nprintln(foo)")
        refs = get_references(doc, 0, 4)  # 'foo'
        # Should NOT match 'foobar'
        assert len(refs) == 2


# --- Signature Help ---------------------------------------------------

class TestSignatureHelp:
    """Tests for textDocument/signatureHelp."""

    def _doc(self, source: str) -> TextDocument:
        return TextDocument("file:///test.ltl", "lateralus", 1, source)

    def test_builtin_signature(self):
        doc = self._doc("println(")
        sig = get_signature_help(doc, 0, 8)
        assert sig is not None
        assert len(sig["signatures"]) == 1
        assert sig["activeParameter"] == 0

    def test_user_function_signature(self):
        doc = self._doc("fn add(a: int, b: int) -> int {\n    return a + b\n}\nadd(1, 2)")
        sig = get_signature_help(doc, 3, 5)  # inside add(1,
        assert sig is not None
        assert "add" in sig["signatures"][0]["label"]

    def test_active_parameter_advances(self):
        doc = self._doc("fn add(a: int, b: int) -> int { return a + b }\nadd(1, ")
        sig = get_signature_help(doc, 1, 7)  # after comma
        assert sig is not None
        assert sig["activeParameter"] == 1

    def test_no_signature_outside_parens(self):
        doc = self._doc("let x = 42")
        sig = get_signature_help(doc, 0, 10)
        assert sig is None

    def test_nested_call(self):
        doc = self._doc("println(len(")
        sig = get_signature_help(doc, 0, 12)
        assert sig is not None
        assert "len" in sig["signatures"][0]["label"]


# --- LSP Server Protocol (new capabilities) ---------------------------

class TestLSPServerV2:
    """Tests for the new LSP v2 message handlers."""

    def _server_with_doc(self, source: str) -> LateralusLSP:
        server = LateralusLSP()
        server.handle_message({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test.ltl",
                    "languageId": "lateralus",
                    "version": 1,
                    "text": source,
                },
            },
        })
        return server

    def test_initialize_has_new_capabilities(self):
        server = LateralusLSP()
        resp = server.handle_message({
            "jsonrpc": "2.0", "id": 1,
            "method": "initialize", "params": {},
        })
        caps = resp["result"]["capabilities"]
        assert caps["documentSymbolProvider"] is True
        assert caps["definitionProvider"] is True
        assert caps["referencesProvider"] is True
        assert "triggerCharacters" in caps["signatureHelpProvider"]
        assert caps["documentFormattingProvider"] is True

    def test_document_symbol_request(self):
        server = self._server_with_doc("fn greet() {}\nstruct Point {}")
        resp = server.handle_message({
            "jsonrpc": "2.0", "id": 10,
            "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": "file:///test.ltl"}},
        })
        names = [s["name"] for s in resp["result"]]
        assert "greet" in names
        assert "Point" in names

    def test_definition_request(self):
        server = self._server_with_doc("fn greet() {}\ngreet()")
        resp = server.handle_message({
            "jsonrpc": "2.0", "id": 11,
            "method": "textDocument/definition",
            "params": {
                "textDocument": {"uri": "file:///test.ltl"},
                "position": {"line": 1, "character": 2},
            },
        })
        assert resp["result"] is not None
        assert resp["result"]["range"]["start"]["line"] == 0

    def test_references_request(self):
        server = self._server_with_doc("let x = 42\nprintln(x)")
        resp = server.handle_message({
            "jsonrpc": "2.0", "id": 12,
            "method": "textDocument/references",
            "params": {
                "textDocument": {"uri": "file:///test.ltl"},
                "position": {"line": 0, "character": 4},
                "context": {"includeDeclaration": True},
            },
        })
        assert len(resp["result"]) == 2

    def test_signature_help_request(self):
        server = self._server_with_doc("println(")
        resp = server.handle_message({
            "jsonrpc": "2.0", "id": 13,
            "method": "textDocument/signatureHelp",
            "params": {
                "textDocument": {"uri": "file:///test.ltl"},
                "position": {"line": 0, "character": 8},
            },
        })
        assert resp["result"] is not None
        assert len(resp["result"]["signatures"]) >= 1

    def test_formatting_request(self):
        server = self._server_with_doc("let x = 42   \n")  # trailing whitespace
        resp = server.handle_message({
            "jsonrpc": "2.0", "id": 14,
            "method": "textDocument/formatting",
            "params": {
                "textDocument": {"uri": "file:///test.ltl"},
                "options": {"tabSize": 4, "insertSpaces": True},
            },
        })
        # Should return at least one edit to clean trailing whitespace
        assert len(resp["result"]) >= 1

    def test_formatting_no_change(self):
        server = self._server_with_doc("let x = 42\n")
        resp = server.handle_message({
            "jsonrpc": "2.0", "id": 15,
            "method": "textDocument/formatting",
            "params": {
                "textDocument": {"uri": "file:///test.ltl"},
                "options": {"tabSize": 4},
            },
        })
        # Already formatted: should return empty edits
        assert resp["result"] == []
