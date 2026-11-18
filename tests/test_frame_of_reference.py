import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lateralus_lang.compiler import Target

SOURCE = Path(__file__).resolve().parents[1] / "stdlib" / "frame_of_reference.ltl"


def test_timestamp_round_trips(compiler):
    result = compiler.compile_source(SOURCE.read_text(encoding="utf-8"), target=Target.PYTHON)
    assert result.ok, result.errors
    module = {}
    exec(result.python_src, module)
    encode, decode = module["encode_dod"], module["decode_dod"]

    for timestamps in ([], [0], [0, 0], [7], [7, 7], [7, 9], [7, 7, 8]):
        assert decode(encode(timestamps)) == timestamps

    # Old frames did not distinguish empty, singleton and repeated pairs.
    assert decode({"first": 0, "second_delta": 0, "dods": []}) == [0]
    assert decode({"first": 7, "second_delta": 0, "dods": []}) == [7]
    assert decode({"first": 7, "second_delta": 2, "dods": []}) == [7, 9]
    assert decode({"first": 7, "second_delta": 0, "dods": [1]}) == [7, 7, 8]


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js is required to run generated JS")
def test_javascript_decodes_short_frames(compiler):
    result = compiler.compile_source(SOURCE.read_text(encoding="utf-8"), target=Target.JAVASCRIPT)
    assert result.ok, result.errors
    frames = [
        {"first": 0, "second_delta": 0, "dods": [], "count": 0},
        {"first": 7, "second_delta": 0, "dods": [], "count": 2},
        {"first": 7, "second_delta": 0, "dods": []},
    ]
    driver = f"console.log(JSON.stringify({json.dumps(frames)}.map(decode_dod)));"
    run = subprocess.run(
        ["node", "--input-type=module", "-"],
        input=result.js_src + "\n" + driver,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    assert json.loads(run.stdout) == [[], [7, 7], [7]]
