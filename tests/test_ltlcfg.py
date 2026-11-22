"""
tests/test_ltlcfg.py - Unit tests for LATERALUS configuration format (.ltlcfg)
"""
import pytest
from lateralus_lang.ltlcfg import parse_config


@pytest.mark.parametrize("assignment, closing_comment", [
    ("banner: str", ""),
    ("banner", "  # explanation"),
])
def test_multiline_string_keeps_its_content_and_following_fields(assignment, closing_comment):
    config = parse_config(
        f'[app]\n{assignment} = """first\nsecond # literal"""{closing_comment}\n'
        'port: int = 8080\n'
    )

    assert config["app"] == {"banner": "first\nsecond # literal", "port": 8080}


def test_one_line_strings_still_parse():
    config = parse_config('[app]\nquoted = "a # b"\nliteral = """one line"""\n')

    assert config["app"] == {"quoted": "a # b", "literal": "one line"}


def test_unterminated_multiline_string_is_not_stored():
    config = parse_config('[app]\nport = 8080\nbanner = """first\nsecond\n')

    assert config["app"] == {"port": 8080}


def test_basic_ltlcfg_types():
    src = """
    [server]
    host: str = "0.0.0.0"
    port: int = 9000
    debug: bool = true
    timeout: float = 30.5
    tags: list = ["api", "web"]
    """
    cfg = parse_config(src)
    assert cfg["server"]["host"] == "0.0.0.0"
    assert cfg["server"]["port"] == 9000
    assert cfg["server"]["debug"] is True
    assert cfg["server"]["timeout"] == 30.5
    assert cfg["server"]["tags"] == ["api", "web"]
