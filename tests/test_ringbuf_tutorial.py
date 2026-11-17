"""Exercise the exact example and vectors shipped with the ringbuf article."""
import runpy
from pathlib import Path

def test_ringbuf_tutorial():
    root = Path(__file__).resolve().parents[1]
    runner = root / "examples/tutorials/run_ringbuf_tutorial.py"
    helpers = runpy.run_path(str(runner))
    output, count = helpers["verify"](root, runner.with_name("ringbuf_tutorial.ltl"))
    assert output == helpers["EXPECTED_OUTPUT"]
    assert count == 18
