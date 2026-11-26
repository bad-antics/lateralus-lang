# NOTE: This hunk is reconstructed from the issue text because the full
# source of lateralus_lang/law_generalizer.py was not available in the
# provided context. Apply the `_rename_vars` helper and the `as_ltl_law`
# change below to the existing module; unrelated code in the module
# (candidate templates, trial runner, CLI glue) is unchanged.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Mapping

# Matches a whole identifier token. Using a single compiled pattern lets us
# substitute every identifier in one pass.
_IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


def _rename_vars(expr: str, mapping: Mapping[str, str]) -> str:
    """Rename identifiers in ``expr`` *simultaneously*.

    Every identifier token in the original expression is looked up in
    ``mapping`` exactly once, and replacement text is never re-scanned.
    This guarantees swaps and chained renames cannot alias each other,
    e.g. ``{"x": "y", "y": "x"}`` turns ``"x - y"`` into ``"y - x"``
    (sequential renaming would produce ``"x - x"``).
    """
    if not mapping:
        return expr

    def _sub(match: "re.Match[str]") -> str:
        name = match.group(0)
        return mapping.get(name, name)

    return _IDENT_RE.sub(_sub, expr)


def _rename_var(expr: str, old: str, new: str) -> str:
    """Backward-compatible single-pair rename (whole-word)."""
    return _rename_vars(expr, {old: new})


@dataclass
class Characterization:
    """Result of characterizing a user function against a template."""

    fn_name: str
    expr: str
    param_names: List[str] = field(default_factory=list)
    trials: int = 0

    def as_ltl_law(self) -> str:
        # Build ONE mapping from template variables to the user's real
        # parameter names and apply it in a single simultaneous pass.
        # Sequential renaming aliased parameters when the first parameter
        # was named `y` (x -> y, then y -> second_param clobbered both).
        mapping: Dict[str, str] = {}
        if len(self.param_names) >= 1 and self.param_names[0] != "x":
            mapping["x"] = self.param_names[0]
        if len(self.param_names) >= 2 and self.param_names[1] != "y":
            mapping["y"] = self.param_names[1]

        expr = _rename_vars(self.expr, mapping)

        params = ", ".join(self.param_names)
        return f"@law\nfn {self.fn_name}_law({params}) -> bool {{\n    return {self.fn_name}({params}) == ({expr})\n}}\n"