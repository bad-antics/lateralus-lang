"""
tests/test_lt_logs.py — apps/lt_logs.ltl (the lt-logs-shipper bounty)

Runs the app the way a user would (`lateralus run apps/lt_logs.ltl ...`
with log lines on stdin) and checks what it writes.  Where an independent
implementation is installed, the outputs are also read back with it:
python-lz4 for the LZ4 frames, pyarrow for the Parquet files, and
`cryptography`'s ChaCha20Poly1305 for sealed rollups.  Those checks skip
when the package is missing; the rest only need the toolchain.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
APP = REPO / "apps" / "lt_logs.ltl"
KEY = bytes(range(32))
KEY_HEX = KEY.hex()

SAMPLE = "\n".join([
    'ts=2026-11-15T12:00:01Z level=info msg="request served" path=/api/users status=200',
    '{"time":"2026-11-15T12:00:20.500Z","level":"error","msg":"upstream timed out",'
    '"path":"/api/orders","status":504}',
    '<11>1 2026-11-15T12:00:42Z web01 nginx 812 - [req@1 id="a1"] connection reset by peer',
    'ts=2026-11-15T12:01:05Z level=warn msg="slow query" ms=812',
    '',
    'ts=2026-11-15T12:01:30Z level=error msg="panic: nil map" svc=billing',
    'ts=2026-11-15T12:03:59.999Z level=error msg="out of memory" svc=billing',
]) + "\n"

pytestmark = pytest.mark.e2e


def run(args, stdin="", cwd=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "lateralus_lang", "run", str(APP), *args],
        input=stdin.encode("utf-8"), capture_output=True, timeout=300,
        cwd=str(cwd or REPO), env=env,
    )


def manifests(proc):
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines()]


def test_selftest_passes():
    proc = run(["selftest"])
    out = proc.stdout.decode("utf-8", "replace")
    assert proc.returncode == 0, out + proc.stderr.decode("utf-8", "replace")
    assert "fail=0" in out
    assert "FAIL" not in out


def test_help():
    proc = run(["--help"])
    assert proc.returncode == 0
    assert b"--filter EXPR" in proc.stdout


def test_one_rollup_per_minute(tmp_path):
    ms = manifests(run(["--out", str(tmp_path)], SAMPLE))
    assert [m["window_start"] for m in ms] == [
        "2026-11-15T12:00:00.000Z", "2026-11-15T12:01:00.000Z", "2026-11-15T12:03:00.000Z"]
    assert [m["records"] for m in ms] == [3, 2, 1]
    assert ms[0]["levels"] == {"info": 1, "error": 2}   # syslog severity 3 -> error
    assert all(Path(m["file"]).name.endswith(".jsonl.lz4") for m in ms)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(Path(m["file"]).name for m in ms)


def test_cat_reads_back_jsonl(tmp_path):
    ms = manifests(run(["--out", str(tmp_path)], SAMPLE))
    proc = run(["cat", ms[0]["file"]])
    assert proc.returncode == 0, proc.stderr
    rows = [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines()]
    assert [r["format"] for r in rows] == ["logfmt", "json", "syslog"]
    assert rows[1] == {"ts": "2026-11-15T12:00:20.500Z", "level": "error",
                       "msg": "upstream timed out", "format": "json",
                       "fields": {"path": "/api/orders", "status": 504}}
    assert rows[2]["fields"]["req@1.id"] == "a1"
    assert rows[2]["fields"]["host"] == "web01"


def test_jsonl_is_a_standard_lz4_frame(tmp_path):
    lz4_frame = pytest.importorskip("lz4.frame")
    ms = manifests(run(["--out", str(tmp_path)], SAMPLE))
    total = 0
    for m in ms:
        lines = lz4_frame.decompress(Path(m["file"]).read_bytes()).decode().splitlines()
        assert len(lines) == m["records"]
        total += len(lines)
    assert total == 6


def test_filters():
    proc = run(["--out", "-", "--filter", "level=error or has(reset)"], SAMPLE)
    rows = [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines()]
    assert [r["msg"] for r in rows] == [
        "upstream timed out", "connection reset by peer", "panic: nil map", "out of memory"]
    # with --out - the per-rollup summaries go to stderr
    summaries = [json.loads(line) for line in proc.stderr.decode("utf-8").splitlines()
                 if line.startswith("{")]
    assert [s["records"] for s in summaries] == [2, 1, 1]

    proc = run(["--out", "-", "--filter", "svc=billing", "--filter", 'msg~"^out of"'], SAMPLE)
    rows = [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines()]
    assert [r["msg"] for r in rows] == ["out of memory"]

    proc = run(["--out", "-", "--filter", "app=nginx and not level=info"], SAMPLE)
    rows = [json.loads(line) for line in proc.stdout.decode("utf-8").splitlines()]
    assert [r["fields"]["procid"] for r in rows] == ["812"]


@pytest.mark.parametrize("args, message", [
    (["--filter", "level="], b"bad --filter"),
    (["--filter", "(level=error"], b"bad --filter"),
    (["--filter", 'msg~"("'], b"bad regex"),
    (["--format", "csv"], b"--format must be"),
    (["--key", "abcd"], b"--key must be 64 hex"),
    (["--out", "-", "--format", "parquet"], b"cannot be combined"),
    (["--nope"], b"unknown option"),
])
def test_bad_arguments_exit_2(args, message):
    proc = run(args, SAMPLE)
    assert proc.returncode == 2
    assert message in proc.stderr
    assert proc.stdout == b""


def test_parquet_rollups(tmp_path):
    pq = pytest.importorskip("pyarrow.parquet")
    ms = manifests(run(["--format", "parquet", "--out", str(tmp_path)], SAMPLE))
    assert all(m["file"].endswith(".parquet") for m in ms)
    table = pq.read_table(ms[0]["file"])
    assert table.column_names == ["ts", "level", "msg", "format", "fields"]
    assert str(table.schema.field("ts").type) == "timestamp[ms, tz=UTC]"
    assert table.column("ts").cast("int64").to_pylist() == [
        1794744001000, 1794744020500, 1794744042000]
    assert table.column("msg").to_pylist() == [
        "request served", "upstream timed out", "connection reset by peer"]
    assert json.loads(table.column("fields").to_pylist()[0]) == {
        "path": "/api/users", "status": "200"}
    assert sum(pq.read_table(m["file"]).num_rows for m in ms) == 6


def test_sealed_rollups_open_with_reference_aead(tmp_path):
    aead = pytest.importorskip("cryptography.hazmat.primitives.ciphers.aead")
    lz4_frame = pytest.importorskip("lz4.frame")
    ms = manifests(run(["--key", KEY_HEX, "--out", str(tmp_path)], SAMPLE))
    nonces = set()
    for m in ms:
        assert m["encrypted"] and m["file"].endswith(".jsonl.lz4.enc")
        blob = Path(m["file"]).read_bytes()
        assert blob[:5] == b"LTLE\x01"
        nonces.add(blob[5:17])
        plain = aead.ChaCha20Poly1305(KEY).decrypt(blob[5:17], blob[17:], blob[:5])
        assert len(lz4_frame.decompress(plain).splitlines()) == m["records"]
    assert len(nonces) == len(ms)


def test_sealed_parquet_decrypt_command(tmp_path):
    key_file = tmp_path / "key.hex"
    key_file.write_text(KEY_HEX + "\n")
    out = tmp_path / "out"
    out.mkdir()
    ms = manifests(run(["--format", "parquet", "--key", "@" + str(key_file),
                        "--out", str(out)], SAMPLE))
    proc = run(["decrypt", "--key", KEY_HEX, ms[0]["file"]])
    assert proc.returncode == 0
    assert proc.stdout[:4] == b"PAR1" and proc.stdout[-4:] == b"PAR1"

    wrong = bytes([1]) + KEY[1:]
    proc = run(["decrypt", "--key", wrong.hex(), ms[0]["file"]])
    assert proc.returncode == 2
    assert b"cannot decrypt" in proc.stderr
    assert proc.stdout == b""


def test_cat_sealed_jsonl_needs_key(tmp_path):
    ms = manifests(run(["--key", KEY_HEX, "--out", str(tmp_path)], SAMPLE))
    assert run(["cat", ms[0]["file"]]).returncode == 2
    proc = run(["cat", "--key", KEY_HEX, ms[0]["file"]])
    assert proc.returncode == 0
    assert len(proc.stdout.splitlines()) == 3


def test_late_lines_and_grace(tmp_path):
    lines = "\n".join([
        "ts=2026-11-15T12:00:10Z msg=a",
        "ts=2026-11-15T12:01:03Z msg=b",   # within grace: 12:00 window still open
        "ts=2026-11-15T12:00:50Z msg=c",   # late but accepted into 12:00
        "ts=2026-11-15T12:01:06Z msg=d",   # past 12:01:05 -> 12:00 window closes
        "ts=2026-11-15T12:00:55Z msg=e",   # too late: its own, later rollup
    ]) + "\n"
    ms = manifests(run(["--out", str(tmp_path)], lines))
    assert [(m["window_start"][11:16], m["records"]) for m in ms] == [
        ("12:00", 2), ("12:00", 1), ("12:01", 2)]
    assert len({m["file"] for m in ms}) == 3     # same window, distinct files


def test_window_option(tmp_path):
    ms = manifests(run(["--window", "3600", "--out", str(tmp_path)], SAMPLE))
    assert [m["records"] for m in ms] == [6]
    assert ms[0]["window_end"] == "2026-11-15T13:00:00.000Z"


def test_unwritable_out_dir_is_a_clean_error(tmp_path):
    proc = run(["--out", str(tmp_path / "missing")], SAMPLE)
    assert proc.returncode == 2
    assert b"cannot write" in proc.stderr
    assert b"Traceback" not in proc.stderr
