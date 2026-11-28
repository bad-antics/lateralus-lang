"""
Regression test for examples/nats_tutorial.ltl and stdlib/nats.ltl behavior.
Asserts that the executable tutorial runs cleanly and produces exact pinned NATS wire frames.
Includes an offline checkout test for the UNSUB 7 1 request-reply transcript that runs the
repository's own stdlib/nats.ltl, so any future change to the shipped encoder is caught.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_ltl(cmd_args, env=None, **kwargs):
    _env = os.environ.copy()
    _env["PYTHONPATH"] = str(REPO_ROOT)
    if env:
        _env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "lateralus_lang"] + cmd_args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
        env=_env,
        **kwargs,
    )


def test_nats_tutorial_execution():
    res = _run_ltl(["run", str(REPO_ROOT / "examples" / "nats_tutorial.ltl")])
    stdout = res.stdout

    assert "=== LATERALUS STDLIB NATS TUTORIAL ===" in stdout
    assert "STEP 1: Multiline PUB with reply inbox (6 payload bytes):" in stdout
    assert "PUB press.status _INBOX.press 6" in stdout
    assert "STEP 2: Multiline PUB without reply (17 payload bytes):" in stdout
    assert "PUB telemetry.sensor 17" in stdout
    assert "STEP 3: Empty PUB heartbeat (0 payload bytes):" in stdout
    assert "PUB heartbeat 0" in stdout
    assert "STEP 4: PUB with trailing CRLF in payload (10 payload bytes):" in stdout
    assert "PUB logs.app 10" in stdout
    assert "STEP 5: Parsed incoming server message:" in stdout
    assert "op=MSG" in stdout
    assert "subject=press.status" in stdout
    # Step 6: UNSUB 7 1 request-reply transcript
    assert "STEP 6: Request-Reply with UNSUB 7 1 (single-delivery):" in stdout
    assert "SUB _INBOX.lesson 7" in stdout
    assert "UNSUB 7 1" in stdout
    assert "PUB lesson.press _INBOX.lesson 6" in stdout
    assert "transcript_ok=true" in stdout
    assert "PINNED_VECTORS: len1=41 len2=44 len3=19 len4=29 op=MSG transcript_ok=true" in stdout


def test_nats_tutorial_typecheck():
    res = _run_ltl(["check", str(REPO_ROOT / "examples" / "nats_tutorial.ltl")])
    assert "OK" in res.stdout


def test_one_reply_transcript_from_checkout():
    """
    Offline checkout test: exercises the UNSUB 7 1 request-reply transcript using
    the repository's own stdlib/nats.ltl, so a future change to the shipped encoder
    is caught automatically without needing a live NATS server.
    """
    module = (REPO_ROOT / "stdlib" / "nats.ltl").read_bytes()
    lesson = (
        b'\nfn main() {\n'
        b'    let subscribe      = sub("_INBOX.lesson", "", "7")\n'
        b'    let stop_after_one = unsub("7", 1)\n'
        b'    let request        = pub_msg("lesson.press", "_INBOX.lesson", "ok\\r\\n42")\n'
        b'    let expected       = "SUB _INBOX.lesson 7\\r\\nUNSUB 7 1\\r\\nPUB lesson.press _INBOX.lesson 6\\r\\nok\\r\\n42\\r\\n"\n'
        b'    let commands       = subscribe + stop_after_one + request\n'
        b'    assert_eq(commands, expected, "one-reply request transcript")\n'
        b'    print(commands)\n'
        b'}\n'
        b'main()\n'
    )
    with tempfile.TemporaryDirectory() as tmp:
        unit = Path(tmp) / "lesson.ltl"
        unit.write_bytes(module + b"\n" + lesson)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        result = subprocess.check_output(
            [sys.executable, "-m", "lateralus_lang", "run", str(unit)],
            env=env,
            cwd=str(REPO_ROOT),
        )
    # print() appends one newline after the protocol bytes
    expected = (
        b"SUB _INBOX.lesson 7\r\nUNSUB 7 1\r\n"
        b"PUB lesson.press _INBOX.lesson 6\r\nok\r\n42\r\n\n"
    )
    assert result == expected, (
        f"transcript mismatch:\n  got:      {result!r}\n  expected: {expected!r}"
    )


if __name__ == "__main__":
    test_nats_tutorial_execution()
    test_nats_tutorial_typecheck()
    test_one_reply_transcript_from_checkout()
    print("PASS")
