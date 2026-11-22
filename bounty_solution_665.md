2. Code Patch / Fix
**File: `lsp_server.py`** (or equivalent LSP entry point)

```python
import os
import re
from typing import Dict, List, Optional, Any

# ... existing imports ...

class LSPHandler:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.stdlib_index: Dict[str, Dict[str, Any]] = {}
        self._index_stdlib()

    def _index_stdlib(self):
        """Index stdlib/*.ltl files for pub fn signatures and docstrings."""
        stdlib_dir = os.path.join(self.root_path, "stdlib")
        if not os.path.exists(stdlib_dir):
            return

        for filename in os.listdir(stdlib_dir):
            if not filename.endswith(".ltl"):
                continue
            
            module_name = filename[:-4]  # Remove .ltl extension
            filepath = os.path.join(stdlib_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception:
                continue

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Look for pub fn declaration
                if line.startswith("pub fn "):
                    # Extract function name
                    match = re.match(r"pub fn (\w+)", line)
                    if match:
                        func_name = match.group(1)
                        
                        # Look backwards for docstring (/// line directly above)
                        doc_line = ""
                        if i > 0:
                            prev_line = lines[i-1].strip()
                            if prev_line.startswith("///"):
                                doc_line = prev_line[3:].strip()
                        
                        # Store in index
                        self.stdlib_index[func_name] = {
                            "signature": line,
                            "doc": doc_line,
                            "module": module_name
                        }
                i += 1

    def handle_hover(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle textDocument/hover request."""
        uri = params.get("textDocument", {}).get("uri", "")
        position = params.get("position", {})
        line = position.get("line", 0)
        character = position.get("character", 0)
        
        # Read the file content
        try:
            file_path = uri.replace("file://", "")
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception:
            return None

        if line >= len(lines):
            return None

        current_line = lines[line]
        
        # Extract identifier at cursor position
        # Simple heuristic: