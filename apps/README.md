# apps/

Complete programs built on the stdlib.

## lt_logs.ltl: log shipper

One file that reads log lines on stdin, keeps the ones that match a filter,
batches them into 1-minute rollups, and writes each rollup as an
LZ4-compressed JSON-lines file or a Parquet file. With `--key`, each rollup
is also sealed with ChaCha20-Poly1305.

```sh
# all error lines from a service, one .jsonl.lz4 per minute in ./rollups
tail -F /var/log/app.log | lateralus run apps/lt_logs.ltl \
    --filter 'level=error or has(panic, "out of memory")' --out rollups

# Parquet, sealed with a key kept in a file
lateralus run apps/lt_logs.ltl --format parquet --key @/etc/lt-logs.key --out rollups < app.log

# look at what passes a filter, without writing files
lateralus run apps/lt_logs.ltl --out - --filter 'app=nginx and status!=200' < access.log

# read a rollup back (decrypts too, given --key)
lateralus run apps/lt_logs.ltl cat --key @/etc/lt-logs.key rollups/lt-logs-20261115T120000Z-0001.jsonl.lz4.enc
```

`lateralus run apps/lt_logs.ltl --help` lists every option.

### Input

Each line is detected on its own, so one stream can mix formats. You can
also force one format with `--input`.

| Format | Recognised by | Timestamp / level / message taken from |
|---|---|---|
| JSON | starts with `{` | `ts`/`time`/`timestamp`/`@timestamp`, `level`/`lvl`/`severity`, `msg`/`message` |
| RFC 5424 syslog | `<PRI>VERSION ...` | TIMESTAMP, PRI severity, MSG; HOSTNAME/APP-NAME/PROCID/MSGID become `host`/`app`/`procid`/`msgid`, SD params become `sdid.name` |
| logfmt | has `key=value` | same keys as JSON |
| anything else | | kept as `format: "raw"`, with the whole line as `msg` |

Timestamps can be RFC 3339 (with any offset), epoch seconds, or epoch
milliseconds. A line with no usable timestamp is stamped with its arrival
time. Levels are lowercased, and `err` and `warning` become `error` and
`warn`, so one filter matches syslog and application logs alike.

### Filters

```
level=error                    field equals value
status!=200                    field differs
msg~"time(d)? ?out"            regex search in a field
~"^GET /api"                   regex search in the whole line
has(panic, "out of memory")    any of the words in the line (Aho-Corasick)
path has(admin, login)         any of the words in one field
a and b   a or b   not a   ( ... )
```

`and` binds tighter than `or`. Several `--filter` options must all match. A
missing field compares as the empty string.

### Rollups

Records are grouped by window: `--window` seconds, 60 by default. A window
is written once a record arrives that is newer than the window's end plus
`--grace` (default 5 s). Any windows still open at end of input are written
then. A line that arrives after its window was written goes into a new file
for that window, so nothing is dropped.

Each file is named `lt-logs-<window start>-<seq>.<ext>`. For each file, one
JSON line goes to stdout:

```json
{"window_start":"2026-11-15T12:00:00.000Z","window_end":"2026-11-15T12:01:00.000Z","records":3,
 "levels":{"info":1,"error":2},"format":"jsonl","encrypted":false,
 "file":"rollups/lt-logs-20261115T120000Z-0001.jsonl.lz4","bytes":286}
```

| Format | Contents |
|---|---|
| `.jsonl.lz4` | A standard LZ4 frame (`lz4 -d`, python-lz4, ...) holding one JSON object per record: `{"ts","level","msg","format","fields"}` |
| `.parquet` | One row group: `ts` (timestamp ms, UTC), `level`, `msg`, `format`, `fields` (JSON text). Plain encoding, uncompressed. Tested with pyarrow |
| `.enc` suffix | `"LTLE"` `0x01`, a random 12-byte nonce, the ciphertext, and a 16-byte tag. This is RFC 8439 ChaCha20-Poly1305, with the 5 header bytes as associated data. `lt_logs decrypt --key KEY FILE` or any RFC 8439 implementation opens it |

Each sealed file gets a random 96-bit nonce. That is the standard limit for
random nonces: it's fine for millions of files under one key, but rotate
keys well before 2³² files.

### Stdlib modules used

`logfmt`, `regex`, `aho_corasick`, `lz4`, `parquet` (file framing and
Thrift compact primitives), `chacha20`, and `poly1305`. JSON uses the
`json_parse` / `json_encode` builtins.

### Tests

* `lateralus run apps/lt_logs.ltl selftest`: in-file checks. They include
  the RFC 8439 §2.8.2 AEAD vector and the RFC 5424 §6.5 example.
* `pytest tests/test_lt_logs.py`: end-to-end runs. Outputs are read back
  with python-lz4, pyarrow and `cryptography` when those are installed.

### Native build

`lateralus c apps/lt_logs.ltl` transpiles, but gcc can't compile the
result yet. The C backend has no lowering for maps, dynamic lists or
`import`: it emits `/* unsupported: BlockStmt */` and `map`/`list` types
that don't exist in C. This isn't specific to the app. `stdlib/logfmt.ltl`
and `stdlib/aho_corasick.ltl` fail to compile on their own the same way.
Until the C backend can handle these, the app runs through `lateralus run`
(the Python backend).
