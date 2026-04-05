"""
tests/test_lexer.py  -  Lexer unit tests
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from lateralus_lang.lexer import lex, TK, LexError


def tokens(src):
    return [t for t in lex(src) if t.kind != TK.EOF]


def kinds(src):
    return [t.kind for t in tokens(src)]


class TestLiterals:
    def test_integer(self):
        ts = tokens("42")
        assert ts[0].kind  == TK.INT
        assert ts[0].value == 42

    def test_hex(self):
        ts = tokens("0xFF")
        assert ts[0].kind  == TK.INT
        assert ts[0].value == 255

    def test_binary(self):
        ts = tokens("0b1010")
        assert ts[0].kind  == TK.INT
        assert ts[0].value == 10

    def test_float(self):
        ts = tokens("3.14")
        assert ts[0].kind  == TK.FLOAT
        assert abs(ts[0].value - 3.14) < 1e-9

    def test_string(self):
        ts = tokens('"hello"')
        assert ts[0].kind  == TK.STRING
        assert ts[0].value == "hello"

    def test_bool_true(self):
        ts = tokens("true")
        assert ts[0].kind  == TK.BOOL
        assert ts[0].value is True

    def test_bool_false(self):
        ts = tokens("false")
        assert ts[0].kind  == TK.BOOL
        assert ts[0].value is False

    def test_nil(self):
        ts = tokens("nil")
        assert ts[0].kind  == TK.NIL
        assert ts[0].value is None

    def test_underscore_number(self):
        ts = tokens("1_000_000")
        assert ts[0].value == 1000000


class TestKeywords:
    def test_fn(self):
        assert kinds("fn")[0] == TK.KW_FN

    def test_let(self):
        assert kinds("let")[0] == TK.KW_LET

    def test_try_recover_ensure(self):
        k = kinds("try recover ensure")
        assert k == [TK.KW_TRY, TK.KW_RECOVER, TK.KW_ENSURE]

    def test_async_await(self):
        k = kinds("async await")
        assert k == [TK.KW_ASYNC, TK.KW_AWAIT]


class TestOperators:
    def test_pipeline(self):
        k = kinds("|>")
        assert k == [TK.PIPELINE]

    def test_arrow(self):
        assert kinds("->")[0] == TK.ARROW

    def test_fat_arrow(self):
        assert kinds("=>")[0] == TK.FAT_ARROW

    def test_starstar(self):
        assert kinds("**")[0] == TK.STARSTAR

    def test_cmp_ops(self):
        k = kinds("== != <= >=")
        assert k == [TK.EQ, TK.NEQ, TK.LTE, TK.GTE]

    def test_logical(self):
        assert kinds("&&")[0] == TK.AMPAMP
        assert kinds("||")[0] == TK.PIPEPIPE

    def test_dotdot(self):
        assert kinds("..")[0] == TK.DOTDOT

    def test_dotdotlt(self):
        assert kinds("..<")[0] == TK.DOTDOTLT


class TestComments:
    def test_line_comment_skipped(self):
        ts = tokens("42 // this is a comment")
        assert len(ts) == 1

    def test_hash_comment_skipped(self):
        ts = tokens("42 # hash comment")
        assert len(ts) == 1

    def test_block_comment_skipped(self):
        ts = tokens("42 /* block */ 43")
        assert [t.value for t in ts] == [42, 43]

    def test_unterminated_block_comment(self):
        with pytest.raises(LexError):
            lex("/* unterminated")


class TestErrors:
    def test_unexpected_char(self):
        # @ and ? are now valid tokens in v1.1; use backtick which is never valid
        with pytest.raises(LexError):
            lex("`")
