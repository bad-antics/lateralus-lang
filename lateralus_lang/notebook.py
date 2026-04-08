"""
lateralus_lang/notebook.py
LATERALUS Notebook Format (.ltlnb)

A Jupyter-inspired notebook format tailored for LATERALUS:
  - JSON-based storage (.ltlnb extension)
  - Cell types: code, markdown, math, output, ltlml
  - Execution tracking with timing and output capture
  - Rich output: text, html, images (base64), error tracebacks
  - Export to HTML, Markdown, and .ltl source files
  - Python API for programmatic notebook creation and execution
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import textwrap
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from datetime import timezone as _tz
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

# ---------------------------------------------------------------------------
# Cell types and output types
# ---------------------------------------------------------------------------

class CellType(str, Enum):
    CODE     = "code"
    MARKDOWN = "markdown"
    MATH     = "math"        # KaTeX / LaTeX math block
    LTLML    = "ltlml"       # LATERALUS markup
    RAW      = "raw"         # raw text, not rendered


class OutputType(str, Enum):
    STREAM        = "stream"          # stdout / stderr
    DISPLAY_DATA  = "display_data"    # rich display (HTML, images)
    EXECUTE_RESULT = "execute_result" # return value
    ERROR         = "error"           # exception traceback
    TIMING        = "timing"          # execution time info


# ---------------------------------------------------------------------------
# Output model
# ---------------------------------------------------------------------------

@dataclass
class NotebookOutput:
    output_type: str
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_count: Optional[int] = None

    # Convenience constructors
    @classmethod
    def stream(cls, text: str, stream: str = "stdout") -> "NotebookOutput":
        return cls(
            output_type=OutputType.STREAM,
            data={"text/plain": text},
            metadata={"stream": stream},
        )

    @classmethod
    def display(cls, html: Optional[str] = None, text: Optional[str] = None,
                image_b64: Optional[str] = None, mime: str = "image/png") -> "NotebookOutput":
        data: dict[str, Any] = {}
        if html:
            data["text/html"] = html
        if text:
            data["text/plain"] = text
        if image_b64:
            data[mime] = image_b64
        return cls(output_type=OutputType.DISPLAY_DATA, data=data)

    @classmethod
    def execute_result(cls, value: Any, execution_count: int = 0) -> "NotebookOutput":
        return cls(
            output_type=OutputType.EXECUTE_RESULT,
            data={"text/plain": str(value)},
            execution_count=execution_count,
        )

    @classmethod
    def error(cls, etype: str, evalue: str, tb: list[str]) -> "NotebookOutput":
        return cls(
            output_type=OutputType.ERROR,
            data={"etype": etype, "evalue": evalue, "traceback": tb},
        )

    @classmethod
    def timing(cls, elapsed_s: float, phase_data: Optional[dict] = None) -> "NotebookOutput":
        """Create a timing output. elapsed_s is in seconds; elapsed_ms is stored."""
        return cls(
            output_type=OutputType.TIMING,
            data={"elapsed_ms": elapsed_s * 1000.0, "phases": phase_data or {}},
        )

    def to_dict(self) -> dict:
        d = {
            "output_type": self.output_type,
            "data": self.data,
            "metadata": self.metadata,
        }
        if self.execution_count is not None:
            d["execution_count"] = self.execution_count
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "NotebookOutput":
        return cls(
            output_type=d["output_type"],
            data=d.get("data", {}),
            metadata=d.get("metadata", {}),
            execution_count=d.get("execution_count"),
        )

    # -- Convenience property accessors ------------------------------------

    @property
    def text(self) -> Optional[str]:
        """For STREAM / EXECUTE_RESULT outputs: the plain text content."""
        return self.data.get("text/plain")

    @property
    def error_name(self) -> Optional[str]:
        """For ERROR outputs: the exception type name."""
        return self.data.get("etype")

    @property
    def traceback(self) -> list[str]:
        """For ERROR outputs: list of traceback lines."""
        return self.data.get("traceback", [])

    @property
    def elapsed_ms(self) -> Optional[float]:
        """For TIMING outputs: elapsed time in milliseconds."""
        return self.data.get("elapsed_ms")


# ---------------------------------------------------------------------------
# Cell model
# ---------------------------------------------------------------------------

@dataclass
class NotebookCell:
    cell_type: str
    source: str
    cell_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    outputs: list[NotebookOutput] = field(default_factory=list)
    execution_count: Optional[int] = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.cell_id:
            h = hashlib.sha1(
                f"{self.cell_type}{self.source}{time.time()}".encode()
            ).hexdigest()[:8]
            self.cell_id = h

    def is_code(self) -> bool:
        return self.cell_type == CellType.CODE

    def clear_outputs(self) -> None:
        self.outputs = []
        self.execution_count = None

    def add_output(self, output: NotebookOutput) -> None:
        self.outputs.append(output)

    def to_dict(self) -> dict:
        return {
            "cell_type": self.cell_type,
            "cell_id": self.cell_id,
            "source": self.source,
            "metadata": self.metadata,
            "outputs": [o.to_dict() for o in self.outputs],
            "execution_count": self.execution_count,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NotebookCell":
        outputs = [NotebookOutput.from_dict(o) for o in d.get("outputs", [])]
        return cls(
            cell_type=d["cell_type"],
            source=d.get("source", ""),
            cell_id=d.get("cell_id", ""),
            metadata=d.get("metadata", {}),
            outputs=outputs,
            execution_count=d.get("execution_count"),
            tags=d.get("tags", []),
        )


# ---------------------------------------------------------------------------
# Notebook model
# ---------------------------------------------------------------------------

NOTEBOOK_FORMAT_VERSION = "1.0"


@dataclass
class Notebook:
    """
    A LATERALUS Notebook (.ltlnb) document.

    Usage:
        nb = Notebook("Physics Exploration")
        nb.add_markdown("## De Broglie Wavelength")
        nb.add_code("let lambda = PLANCK / (ELECTRON_MASS * 2e6)")
        nb.add_math(r"\\lambda = \\frac{h}{mv}")
        nb.save("physics.ltlnb")
    """

    title: str = "Untitled Notebook"
    cells: list[NotebookCell] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    modified_at: str = ""
    kernel_info: dict[str, str] = field(default_factory=lambda: {
        "name": "lateralus",
        "version": "1.5.0",
        "language": "lateralus",
    })
    author: str = ""

    def __post_init__(self) -> None:
        now = datetime.now(_tz.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        self.modified_at = now
        # Populate metadata so callers can retrieve title/author via metadata.get()
        if self.title and self.title != "Untitled Notebook":
            if "title" not in self.metadata:
                self.metadata["title"] = self.title
        if self.author:
            if "author" not in self.metadata:
                self.metadata["author"] = self.author

    # -- Cell management ---------------------------------------------------

    def add_cell(self, cell: NotebookCell) -> NotebookCell:
        self.cells.append(cell)
        self._touch()
        return cell

    def add_code(self, source: str, tags: Optional[list[str]] = None) -> NotebookCell:
        return self.add_cell(NotebookCell(
            cell_type=CellType.CODE,
            source=textwrap.dedent(source).strip(),
            tags=tags or [],
        ))

    def add_markdown(self, source: str) -> NotebookCell:
        return self.add_cell(NotebookCell(
            cell_type=CellType.MARKDOWN,
            source=textwrap.dedent(source).strip(),
        ))

    def add_math(self, latex: str, display: bool = True) -> NotebookCell:
        """Add a math cell. latex is raw LaTeX/KaTeX."""
        return self.add_cell(NotebookCell(
            cell_type=CellType.MATH,
            source=latex.strip(),
            metadata={"display": display},
        ))

    def add_ltlml(self, source: str) -> NotebookCell:
        return self.add_cell(NotebookCell(
            cell_type=CellType.LTLML,
            source=textwrap.dedent(source).strip(),
        ))

    def add_raw(self, source: str, mime: str = "text/plain") -> NotebookCell:
        return self.add_cell(NotebookCell(
            cell_type=CellType.RAW,
            source=source,
            metadata={"mime_type": mime},
        ))

    def insert_cell(self, cell_or_index, index_or_cell=None) -> None:
        """Insert a cell. Supports (cell, index) and legacy (index, cell) signatures."""
        if isinstance(cell_or_index, int):
            # Legacy API: insert_cell(index, cell)
            index, cell = cell_or_index, index_or_cell
        else:
            # New API: insert_cell(cell, index)
            cell = cell_or_index
            index = index_or_cell if index_or_cell is not None else len(self.cells)
        self.cells.insert(index, cell)
        self._touch()

    def remove_cell(self, cell_id: str) -> bool:
        before = len(self.cells)
        self.cells = [c for c in self.cells if c.cell_id != cell_id]
        self._touch()
        return len(self.cells) < before

    def get_cell(self, cell_id: str) -> Optional[NotebookCell]:
        for c in self.cells:
            if c.cell_id == cell_id:
                return c
        return None

    def move_cell(self, cell_id: str, new_index: int) -> None:
        cell = self.get_cell(cell_id)
        if cell:
            self.cells.remove(cell)
            self.cells.insert(new_index, cell)
            self._touch()

    @property
    def code_cells(self) -> list[NotebookCell]:
        return [c for c in self.cells if c.is_code()]

    @property
    def cell_count(self) -> int:
        return len(self.cells)

    def clear_all_outputs(self) -> None:
        for c in self.cells:
            c.clear_outputs()

    # -- Serialization -----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "format_version": NOTEBOOK_FORMAT_VERSION,
            "title": self.title,
            "metadata": self.metadata,
            "kernel_info": self.kernel_info,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "cells": [c.to_dict() for c in self.cells],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Notebook":
        cells = [NotebookCell.from_dict(c) for c in d.get("cells", [])]
        metadata = d.get("metadata", {})
        # Support both old "nbformat" and new "format_version" key
        title = d.get("title", metadata.get("title", "Untitled Notebook"))
        nb = cls(
            title=title,
            cells=cells,
            metadata=metadata,
            created_at=d.get("created_at", ""),
            modified_at=d.get("modified_at", ""),
            kernel_info=d.get("kernel_info", {}),
        )
        # Ensure title is in metadata for round-trip consistency
        if title and title != "Untitled Notebook" and "title" not in nb.metadata:
            nb.metadata["title"] = title
        return nb

    def save(self, path: Union[str, Path]) -> None:
        """Save notebook to .ltlnb file."""
        path = Path(path)
        if not path.suffix:
            path = path.with_suffix(".ltlnb")
        self._touch()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "Notebook":
        """Load notebook from .ltlnb file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def _touch(self) -> None:
        self.modified_at = datetime.now(_tz.utc).isoformat()

    # -- Export ------------------------------------------------------------

    def export_html(self, path: Optional[Union[str, Path]] = None) -> str:
        """Export notebook to a standalone HTML file."""
        html = _render_html(self)
        if path:
            Path(path).write_text(html, encoding="utf-8")
        return html

    def export_markdown(self, path: Optional[Union[str, Path]] = None) -> str:
        """Export notebook to Markdown."""
        md = _render_markdown(self)
        if path:
            Path(path).write_text(md, encoding="utf-8")
        return md

    def export_ltl(self, path: Optional[Union[str, Path]] = None) -> str:
        """Extract all code cells as a single .ltl source file."""
        lines = [f"// Exported from notebook: {self.title}", f"// {self.created_at}", ""]
        for i, cell in enumerate(self.code_cells):
            lines.append(f"// Cell {i + 1}")
            lines.append(cell.source)
            lines.append("")
        source = "\n".join(lines)
        if path:
            Path(path).write_text(source, encoding="utf-8")
        return source

    # -- Execution ---------------------------------------------------------

    def execute(self, executor: Optional["NotebookExecutor"] = None) -> "Notebook":
        """Execute all code cells in order."""
        exec_ = executor or NotebookExecutor()
        exec_.execute_notebook(self)
        return self

    def __repr__(self) -> str:
        return f"Notebook({self.title!r}, cells={self.cell_count})"


# ---------------------------------------------------------------------------
# NotebookExecutor — runs cells
# ---------------------------------------------------------------------------

class NotebookExecutor:
    """
    Executes LATERALUS notebook cells.

    Uses the LATERALUS compiler pipeline (Python transpiler target)
    to run each code cell, capturing stdout and return values.
    """

    def __init__(self, timeout_ms: float = 30_000) -> None:
        self.timeout_ms = timeout_ms
        self._exec_count = 0
        self._globals: dict[str, Any] = {}

    def execute_notebook(self, notebook: Notebook) -> None:
        """Execute all code cells, updating their outputs in place."""
        notebook.clear_all_outputs()
        for cell in notebook.cells:
            if cell.is_code():
                self.execute_cell(cell)

    def execute_cell(self, cell: NotebookCell) -> None:
        """Execute a single code cell."""
        self._exec_count += 1
        cell.execution_count = self._exec_count
        cell.outputs.clear()

        t0 = time.perf_counter()
        stdout_capture = io.StringIO()

        try:
            # Attempt to compile+run via LATERALUS pipeline
            output = self._run_lateralus(cell.source, stdout_capture)
            elapsed = (time.perf_counter() - t0) * 1000

            captured = stdout_capture.getvalue()
            if captured:
                cell.add_output(NotebookOutput.stream(captured))

            if output is not None:
                cell.add_output(NotebookOutput.execute_result(output, self._exec_count))

            cell.add_output(NotebookOutput.timing(elapsed))

        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            tb_lines = traceback.format_exc().splitlines()
            cell.add_output(NotebookOutput.error(
                type(e).__name__, str(e), tb_lines
            ))
            cell.add_output(NotebookOutput.timing(elapsed))

    def _run_lateralus(self, source: str, stdout_capture: io.StringIO) -> Any:
        """
        Compile and run LATERALUS source code.
        Returns the last expression value, if any.
        """
        try:
            from lateralus_lang.codegen.python import Target
            from lateralus_lang.compiler import CompileOptions, Compiler

            options = CompileOptions(target=Target.PYTHON, optimize=1)
            compiler = Compiler(options)
            py_code = compiler.compile_string(source)

            # Redirect stdout
            old_stdout = sys.stdout
            sys.stdout = stdout_capture
            try:
                exec(py_code, self._globals)
            finally:
                sys.stdout = old_stdout

            return self._globals.get("__last_value__")

        except ImportError:
            # Fallback: treat as Python for testing
            old_stdout = sys.stdout
            sys.stdout = stdout_capture
            try:
                exec(compile(source, "<notebook>", "exec"), self._globals)
            finally:
                sys.stdout = old_stdout
            return None


# ---------------------------------------------------------------------------
# HTML renderer
# ---------------------------------------------------------------------------

def _render_html(notebook: Notebook) -> str:
    cells_html = "\n".join(_cell_to_html(c, i) for i, c in enumerate(notebook.cells))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{notebook.title}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body)"></script>
  <style>
    body {{ font-family: 'Inter', system-ui, sans-serif; max-width: 900px; margin: 0 auto;
           padding: 2rem; background: #0b0d14; color: #e8eaf6; }}
    .notebook-title {{ font-size: 2rem; font-weight: 900; color: #e94560; margin-bottom: 0.5rem; }}
    .cell {{ margin: 1.5rem 0; border-radius: 8px; overflow: hidden; }}
    .cell-code {{ background: #111520; border: 1px solid #1e2640; }}
    .cell-code .source {{ font-family: 'JetBrains Mono', monospace; font-size: 0.88rem;
                         color: #e8eaf6; padding: 1rem; white-space: pre-wrap; line-height: 1.7; }}
    .cell-markdown {{ padding: 0.5rem 0; color: #c8cfe8; line-height: 1.8; }}
    .cell-math {{ background: #111520; border: 1px solid #1e2640; padding: 1.5rem;
                 text-align: center; font-size: 1.2rem; overflow-x: auto; }}
    .output {{ background: #0d1117; border-top: 1px solid #1e2640; padding: 0.75rem 1rem;
               font-family: 'JetBrains Mono', monospace; font-size: 0.82rem;
               color: #39d353; white-space: pre-wrap; }}
    .output-error {{ color: #e94560; }}
    .output-timing {{ color: #6272a4; font-size: 0.75rem; text-align: right; }}
    .exec-count {{ color: #6272a4; font-size: 0.75rem; padding: 0.4rem 0.75rem;
                  font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body>
  <div class="notebook-title">{notebook.title}</div>
  <div style="color:#6272a4; font-size:0.85rem; margin-bottom:2rem;">
    LATERALUS Notebook · {notebook.created_at[:10]}
  </div>
  {cells_html}
</body>
</html>"""


def _cell_to_html(cell: NotebookCell, idx: int) -> str:
    if cell.cell_type == CellType.CODE:
        outputs_html = "".join(_output_to_html(o) for o in cell.outputs)
        exec_label = f"[{cell.execution_count}]" if cell.execution_count else "[ ]"
        return f"""<div class="cell cell-code">
  <div class="exec-count">{exec_label}</div>
  <div class="source">{_escape_html(cell.source)}</div>
  {outputs_html}
</div>"""
    elif cell.cell_type == CellType.MARKDOWN:
        return f'<div class="cell cell-markdown">{_simple_md(cell.source)}</div>'
    elif cell.cell_type == CellType.MATH:
        latex = cell.source
        return f'<div class="cell cell-math">$${latex}$$</div>'
    else:
        return f'<div class="cell"><pre>{_escape_html(cell.source)}</pre></div>'


def _output_to_html(output: NotebookOutput) -> str:
    if output.output_type == OutputType.ERROR:
        tb = "\n".join(output.data.get("traceback", []))
        return f'<div class="output output-error">{_escape_html(tb)}</div>'
    elif output.output_type == OutputType.TIMING:
        ms = output.data.get("elapsed_ms", 0)
        return f'<div class="output output-timing">⏱ {ms:.2f}ms</div>'
    elif output.output_type in (OutputType.STREAM, OutputType.EXECUTE_RESULT):
        text = output.data.get("text/plain", "")
        if output.data.get("text/html"):
            return f'<div class="output">{output.data["text/html"]}</div>'
        return f'<div class="output">{_escape_html(str(text))}</div>'
    return ""


def _escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _simple_md(text: str) -> str:
    """Very basic Markdown to HTML conversion."""
    import re
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    text = text.replace("\n\n", "</p><p>")
    return f"<p>{text}</p>"


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def _render_markdown(notebook: Notebook) -> str:
    lines = [f"# {notebook.title}", "", f"> LATERALUS Notebook · {notebook.created_at[:10]}", ""]
    for cell in notebook.cells:
        if cell.cell_type == CellType.CODE:
            ec = f" [{cell.execution_count}]" if cell.execution_count else ""
            lines.append(f"```lateralus{ec}")
            lines.append(cell.source)
            lines.append("```")
            for out in cell.outputs:
                if out.output_type in (OutputType.STREAM, OutputType.EXECUTE_RESULT):
                    text = out.data.get("text/plain", "")
                    if text:
                        lines.append("```")
                        lines.append(str(text))
                        lines.append("```")
        elif cell.cell_type == CellType.MARKDOWN:
            lines.append(cell.source)
        elif cell.cell_type == CellType.MATH:
            lines.append(f"$$\n{cell.source}\n$$")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def new_notebook(title: str = "Untitled") -> Notebook:
    """Create a new empty notebook."""
    return Notebook(title=title)


def load_notebook(path: Union[str, Path]) -> Notebook:
    """Load a notebook from disk."""
    return Notebook.load(path)


def get_notebook_builtins() -> dict:
    return {
        "Notebook":         Notebook,
        "NotebookCell":     NotebookCell,
        "NotebookOutput":   NotebookOutput,
        "NotebookExecutor": NotebookExecutor,
        "new_notebook":     new_notebook,
        "load_notebook":    load_notebook,
        "CellType":         CellType,
        "OutputType":       OutputType,
    }
