# Container-Ready File Packaging with Lateralus `stdlib/tar.ltl` (POSIX ustar)

Container virtualization (Docker, OCI), package registries, and operating system backups serialize directory trees into uncompressed archive streams. Defined by **POSIX.1-1988** and modernized in **POSIX.1-2001**, the **ustar** (Unix Standard TAR) format packs files, directories, symbolic links, and Unix permission metadata into a sequential stream of 512-byte blocks.

Lateralus includes a pure standard library implementation for reading and writing ustar archives in `stdlib/tar.ltl`.

---

## 1. POSIX ustar 512-Byte Header Block Layout

Every archived entity begins with a 512-byte header block containing ASCII-encoded octal fields:

| Offset | Length | Field | Description |
| :--- | :--- | :--- | :--- |
| `0` | 100 | `name` | File path (NUL-terminated ASCII string). |
| `100` | 8 | `mode` | Unix file permissions (octal ASCII, e.g. `0000644\0`). |
| `108` | 8 | `uid` | User ID (octal ASCII). |
| `116` | 8 | `gid` | Group ID (octal ASCII). |
| `124` | 12 | `size` | Payload byte length (octal ASCII). |
| `136` | 12 | `mtime` | Unix modification timestamp (octal ASCII). |
| `148` | 8 | `chksum` | Simple sum of all header bytes (treating chksum as 8 spaces `0x20`). |
| `156` | 1 | `typeflag` | Type: `'0'` regular, `'1'` link, `'2'` symlink, `'5'` directory. |
| `257` | 6 | `magic` | Exact string `"ustar\0"`. |
| `263` | 2 | `version` | Exact string `"00"`. |

### Block Alignment & Payload Sizing
Payload data immediately follows the 512-byte header. If `size` is not an exact multiple of 512 bytes, the data is zero-padded up to the next 512-byte boundary:

$$\text{Padded Size} = \lceil \text{size} / 512 \rceil \times 512$$

### End-of-Archive (EOA) Marker
A standard ustar archive terminates with **two consecutive 512-byte blocks filled entirely with zeros** ($1024\text{ bytes}$ of `0x00`).

---

## 2. API Reference

| Function | Signature | Description |
| :--- | :--- | :--- |
| `tar_read` | `(archive: list) -> list` | Parses a raw byte list into a list of file maps `{name, mode, size, mtime, type, bytes}`. |
| `tar_write` | `(entries: list) -> list` | Serializes a list of file maps into a 512-byte aligned ustar archive with EOA marker. |
| `tar_block_size` | `() -> int` | Returns the canonical block size constant (`512`). |
| `tar_type_regular` / `type_dir` | `() -> str` | Type flag constants (`"0"` for file, `"5"` for directory). |

---

## 3. Practical Example: In-Memory Deployment Bundle

Creating and extracting files entirely in memory without touching the local disk:

```lateralus
import tar

pub fn main() {
    // 1. Define files to package
    let f1 = {}
    f1["name"] = "package.json"
    f1["bytes"] = bytes_of("{\"name\":\"lateralus-pkg\",\"version\":\"1.0.0\"}\n")
    f1["mode"] = 420 // 0644 octal

    // 2. Package into tar archive stream
    let tar_bytes = tar_write([f1])
    print("Archive size: " + str(len(tar_bytes)) + " bytes")

    // 3. Extract and verify files
    let files = tar_read(tar_bytes)
    print("Extracted filename: " + files[0]["name"])
}
```

---

## 4. Verification & Test Suite

The test suite in `tests/stdlib_tar_tutorial.ltl` validates:
- Strict 512-byte block alignment and 1024-byte zero-block trailing termination.
- Ustar magic string matching (`"ustar\000"` at byte offset 257).
- Exact header checksum calculation and round-trip payload extraction.

Verify locally:
```bash
python -m lateralus_lang check tests/stdlib_tar_tutorial.ltl
python -m lateralus_lang check examples/tar_tutorial.ltl
```
