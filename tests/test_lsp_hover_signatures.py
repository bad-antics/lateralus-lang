"""
Tests for the LATERALUS LSP stdlib hover-signature feature (issue #84).

Hovering a stdlib function name must show its signature plus the first
docstring line.  Signatures are parsed from ``stdlib/*.ltl`` at startup — no
extra data files.  These tests exercise:

  * a documented stdlib function (``base64.encode``),
  * a module-qualified reference (``base64.encode``),
  * a function whose docstring has multiple lines (only the first is shown),
  * a stdlib function without a docstring (signature only),
  * a multi-line signature (params spread across physical lines),
  * an unknown symbol (no hover),
  * the existing builtin / keyword hover paths still work,
  * the end-to-end ``textDocument/hover`` LSP request.
"""
from lateralus_lang.lsp_server import (
    STDLIB_SIGNATURES,
    LateralusLSP,
    TextDocument,
    get_hover,
)


def _hover_value(source: str, line: int, character: int):
    doc = TextDocument("file:///test.ltl", "lateralus", 1, source)
    hover = get_hover(doc, line, character)
    assert hover is not None, f"expected a hover for {source!r} at {line}:{character}"
    return hover["contents"]["value"]


class TestStdlibHoverSignatures:
    def test_documented_function_shows_signature_and_doc(self):
        # ``encode`` is defined in stdlib/base64.ltl with a ``///`` docstring.
        value = _hover_value("base64.encode(data)", 0, 8)
        assert "fn encode(data: str) -> str" in value
        assert "Encode a string to base64." in value

    def test_module_qualified_reference(self):
        # Hovering the ``base64`` qualifier of ``base64.encode`` resolves too.
        value = _hover_value("base64.encode(data)", 0, 3)
        assert "fn encode(data: str) -> str" in value
        assert "Encode a string to base64." in value

    def test_only_first_docstring_line_is_shown(self):
        # ``fnv1a_32`` has a two-line docstring; only the first should appear.
        value = _hover_value("hash.fnv1a_32(data)", 0, 6)
        assert "fn fnv1a_32(data: str) -> int" in value
        assert "FNV-1a 32-bit hash of a string." in value
        # The second docstring line must NOT leak into the hover.
        assert "Fast, good distribution" not in value

    def test_function_without_docstring_shows_signature_only(self):
        # ``aho_corasick.build`` has no ``///`` docstring.
        value = _hover_value("aho_corasick.build(patterns)", 0, 14)
        assert "fn build(patterns: list) -> dict" in value
        # No stray docstring text, but the signature code fence is present.
        assert "```lateralus" in value

    def test_multiline_signature_is_joined(self):
        # ``datetime.datetime`` is declared across two physical lines.
        value = _hover_value("datetime.datetime(2020, 1, 1)", 0, 10)
        assert "fn datetime(" in value
        assert "hour: int" in value
        assert "second: int) -> map" in value

    def test_unknown_symbol_has_no_hover(self):
        doc = TextDocument("file:///test.ltl", "lateralus", 1, "xyz123")
        assert get_hover(doc, 0, 3) is None

    def test_builtin_hover_still_works(self):
        value = _hover_value("println(42)", 0, 3)
        assert "print" in value.lower()

    def test_keyword_hover_still_works(self):
        value = _hover_value("fn hello() {}", 0, 0)
        assert "function" in value.lower()

    def test_index_is_populated_from_stdlib(self):
        # The index must be lazily built from the real stdlib sources.
        assert len(STDLIB_SIGNATURES) > 100
        assert STDLIB_SIGNATURES.lookup("encode") is not None
        assert STDLIB_SIGNATURES.lookup("encode", module="base64") is not None

    def test_bare_fn_definition_is_hoverable(self):
        # ``bubble_sort`` in stdlib/algorithms.ltl is declared with a bare
        # ``fn`` (no ``pub``/``export`` prefix).  It is still a public stdlib
        # function and must resolve on hover.
        value = _hover_value("bubble_sort(arr)", 0, 4)
        assert "fn bubble_sort(arr: list) -> list" in value

    def test_export_fn_definition_is_hoverable(self):
        # ``getMediaType`` in stdlib/mime.ltl uses the ``export fn`` form.
        value = _hover_value("mime.getMediaType(ext)", 0, 6)
        assert "fn getMediaType(extension: str) -> Optional[ContentType]" in value

    def test_dash_dash_doc_comment_is_used(self):
        # mime.ltl documents functions with ``--`` comment lines rather than
        # ``///``.  The first ``--`` line above the definition is the docstring.
        value = _hover_value("mime.isMimeType(b, t)", 0, 6)
        assert "fn isMimeType(" in value
        assert "Checks if the given bytes match a specific MIME type" in value


class TestStdlibHoverViaLSP:
    def test_hover_request_returns_signature(self):
        server = LateralusLSP()
        server.handle_message({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test.ltl",
                    "languageId": "lateralus",
                    "version": 1,
                    "text": "let x = base64.encode(\"hi\")",
                },
            },
        })
        response = server.handle_message({
            "jsonrpc": "2.0",
            "id": 7,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {"uri": "file:///test.ltl"},
                "position": {"line": 0, "character": 13},
            },
        })
        assert response is not None
        result = response["result"]
        assert result is not None
        value = result["contents"]["value"]
        assert "fn encode(data: str) -> str" in value
        assert "Encode a string to base64." in value