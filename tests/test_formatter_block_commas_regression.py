"""Formatter regressions: formatting must not invalidate statement blocks."""
from dataclasses import asdict
import subprocess
import sys

import pytest

from lateralus_lang.formatter import LateralusFormatter
from lateralus_lang.parser import parse


def test_function_body_remains_valid_and_idempotent():
    source = 'fn main() {\n    println("hello")\n}\n'
    formatted = LateralusFormatter().format(source)
    parse(source, '<before>')
    parse(formatted, '<after>')
    assert 'println("hello"),' not in formatted
    assert LateralusFormatter().format(formatted) == formatted


def test_nested_statement_blocks_remain_valid():
    source = 'fn main() {\n    if true {\n        println("hello")\n    }\n}\n'
    parse(LateralusFormatter().format(source), '<after>')


def test_struct_trailing_comma_still_added():
    source = 'struct Point {\n    x: int\n    y: int\n}\n'
    result = LateralusFormatter().format(source)
    assert 'y: int,' in result
    parse(result, '<after>')


def test_grouped_expression_is_not_converted_to_tuple():
    source = 'fn main() {\n    let x = (\n        1\n    )\n}\n'
    formatted = LateralusFormatter().format(source)
    parse(source, '<before>')
    before = parse(source, '<before>').body[0].body.stmts[0].value
    after = parse(formatted, '<after>').body[0].body.stmts[0].value
    assert type(after) is type(before)
    before_value, after_value = asdict(before), asdict(after)
    before_value.pop('span')
    after_value.pop('span')
    assert before_value == after_value


def test_multiline_index_remains_valid():
    source = 'fn main() {\n    let a = [1, 2]\n    let x = a[\n        0\n    ]\n}\n'
    parse(source, '<before>')
    parse(LateralusFormatter().format(source), '<after>')


def test_multiline_list_keeps_trailing_comma():
    source = 'fn main() {\n    let a = [\n        1,\n        2\n    ]\n}\n'
    result = LateralusFormatter().format(source)
    assert '2,' in result
    parse(result, '<after>')


def test_multiline_index_on_string_literal_remains_valid():
    source = 'fn main() {\n    let x = "ab"[\n        0\n    ]\n}\n'
    parse(source, '<before>')
    parse(LateralusFormatter().format(source), '<after>')


def test_list_comprehension_remains_valid():
    source = 'fn main() {\n    let x = [\n        n for n in [1, 2]\n    ]\n}\n'
    parse(source, '<before>')
    parse(LateralusFormatter().format(source), '<after>')


def test_list_with_block_comment_remains_valid():
    source = 'fn main() {\n    let x = [\n        1, /* last */\n    ]\n}\n'
    parse(source, '<before>')
    parse(LateralusFormatter().format(source), '<after>')


def test_empty_list_with_block_comment_remains_valid():
    source = 'fn main() {\n    let x = [\n        /* empty */\n    ]\n}\n'
    parse(source, '<before>')
    parse(LateralusFormatter().format(source), '<after>')


def test_struct_decorator_is_not_struct_declaration():
    source = '@struct\nfn main() {\n    println("ok")\n}\n'
    parse(source, '<before>')
    parse(LateralusFormatter().format(source), '<after>')


@pytest.mark.parametrize('source', ['let x = 0x', 'let x = 1e', '-1', "let x = '"])
def test_incomplete_tokens_do_not_crash_formatter(source):
    # 不完整输入仍应保留文本，供编辑器继续显示和用户修复。
    assert LateralusFormatter().format(source) == source + '\n'


def test_incomplete_tail_does_not_insert_commas_in_earlier_list():
    # 词法上下文不完整时，前面的合法列表也不应被推测性地改写标点。
    source = 'let x = [\n    1\n]\nlet y = 0x\n'
    assert LateralusFormatter().format(source).splitlines()[1].strip() == '1'


def test_directory_formatter_continues_after_incomplete_source(tmp_path):
    # 无效的第一个文件不应阻止后续有效文件的格式化。
    (tmp_path / 'a.ltl').write_text('let x = 0x\n')
    good = tmp_path / 'b.ltl'
    good.write_text('fn main() {\nprintln("ok")\n}\n')
    result = subprocess.run(
        [sys.executable, '-m', 'lateralus_lang.formatter', str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert good.read_text() == 'fn main() {\n    println("ok")\n}\n'
