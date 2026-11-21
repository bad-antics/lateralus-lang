"""tests/test_ltlcfg.py — .ltlcfg parser tests"""

from lateralus_lang.ltlcfg import LtlCfgParser


def parse(s):
    return LtlCfgParser().parse_string(s)


class TestMultilineString:
    """Issue #237: triple-quoted multiline values were silently dropped."""

    def test_multiline_value_preserved(self):
        cfg = parse('[app]\nbanner: str = """first\nsecond"""\nport: int = 8080\n')
        assert cfg["app"] == {"banner": "first\nsecond", "port": 8080}

    def test_single_line_triple_quote(self):
        cfg = parse('x = """hello"""\n')
        assert cfg["__root__"]["x"] == "hello"

    def test_normal_fields_unaffected(self):
        cfg = parse('[s]\na: int = 1\nb = "txt" # comment\n')
        assert cfg["s"]["a"] == 1
        assert cfg["s"]["b"] == "txt"
