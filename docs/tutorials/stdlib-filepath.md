# Cross-Platform Path Manipulation with `stdlib.filepath`

The `stdlib.filepath` module provides path parsing, manipulation, normalization, and inspection utilities for Lateralus applications. It simplifies file system routing, CLI file processing, asset bundling, and cross-platform path resolution without external dependencies.

---

## 1. Path Deconstruction & Component Extraction

The module exposes intuitive primitives for splitting file paths:

| Function | Input Example | Output | Description |
| :--- | :--- | :--- | :--- |
| **`dirname(path)`** | `"/home/user/docs/report.pdf"` | `"/home/user/docs"` | Returns the directory segment; returns `"."` for bare filenames. |
| **`basename(path)`** | `"/home/user/docs/report.pdf"` | `"report.pdf"` | Returns the final filename component including extension. |
| **`stem(path)`** | `"archive.tar.gz"` | `"archive.tar"` | Returns the filename without its terminal extension. |
| **`extension(path)`** | `"archive.tar.gz"` | `".gz"` | Returns the terminal file extension including the leading dot. |

```lateralus
import filepath

let p = "/var/log/nginx/access.log"
let dir = filepath.dirname(p)    // "/var/log/nginx"
let file = filepath.basename(p)  // "access.log"
let ext = filepath.extension(p)  // ".log"
let name = filepath.stem(p)      // "access"
```

---

## 2. Path Composition and Normalization

- **`join_path(parts)`**: Merges a list of path segments into a clean canonical path, automatically handling boundary slashes.
- **`normalize(path)`**: Resolves redundant `.` and `..` segments and collapses consecutive slashes into a single delimiter.

```lateralus
// Joining segments
let full = filepath.join_path(["/srv", "data", "storage", "users.json"])
// full == "/srv/data/storage/users.json"

// Resolving navigation dots
let clean = filepath.normalize("/app/backend/../frontend/./build")
// clean == "/app/frontend/build"
```

---

## 3. Path Queries and Transformations

- **`is_absolute(path)`**: Returns `true` if the path starts with a root slash (`/`).
- **`is_relative(path)`**: Returns `true` if the path is relative.
- **`has_extension(path, ext)`**: Checks whether the target file matches a specific extension.
- **`with_extension(path, new_ext)`**: Replaces the current file extension with a new target format.

```lateralus
let script = "src/compiler/main.ltl"

if filepath.is_relative(script) {
    println("Compiling relative path: " + script)
}

if filepath.has_extension(script, ".ltl") {
    let py_output = filepath.with_extension(script, ".py")
    // py_output == "src/compiler/main.py"
}
```

---

## 4. Practical Example: Asset Compiler Pipeline

```lateralus
import filepath

fn compile_asset(src_path: str, out_dir: str) -> str {
    let base = filepath.basename(src_path)
    let stem_name = filepath.stem(src_path)
    let target_name = stem_name + ".bundle.js"
    let destination = filepath.join_path([out_dir, target_name])
    return filepath.normalize(destination)
}

fn main() {
    let output = compile_asset("src/views/index.ts", "/var/www/static/../dist")
    println("Compiled target: " + output)
    // Output: "/var/www/dist/index.bundle.js"
}
```
