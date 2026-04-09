"""
lateralus_lang/errors/bridge.py  -  Bridge to Lateralus Error Intelligence
===========================================================================
Connects the LTL compiler error system to the Lateralus project's
error_engine (nine pioneering error subsystems).

Behaviour
---------
  · Tries to import `lateralus.error_engine.ErrorIntelligence` at runtime.
  · If available, routes every LTL error through:
      - Error DNA registration
      - Causal graph recording
      - Error archaeology (match to historical twins)
      - Self-healing contract evaluation
      - Error budget deduction
  · If the engine is NOT installed (standalone mode), all bridge calls
    silently no-op so the compiler works without the full Lateralus stack.

This bridge is the integration seam — it NEVER blocks compilation.
===========================================================================
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .handler import ErrorContext, ErrorReporter, LTLError, Severity

_log = logging.getLogger("lateralus_lang.errors.bridge")

# -- Optional import of the Lateralus error engine ----------------------------

_engine: Any = None
_engine_module_name = "lateralus.error_engine"


def _load_engine() -> Any:
    global _engine
    if _engine is not None:
        return _engine
    try:
        import importlib
        mod = importlib.import_module(_engine_module_name)
        intel = getattr(mod, "ErrorIntelligence", None)
        if intel is None:
            # Try the singleton getter
            getter = getattr(mod, "get_intelligence", None)
            if getter:
                _engine = getter()
            else:
                _engine = None
        else:
            _engine = intel()
        _log.debug("Lateralus error_engine loaded: %s", _engine)
    except ImportError:
        _log.debug("Lateralus error_engine not available — bridge in standalone mode")
        _engine = None
    return _engine


# -----------------------------------------------------------------------------
# Bridge class
# -----------------------------------------------------------------------------

class ErrorBridge:
    """
    Routes LTL compiler errors to the Lateralus error_engine when present.

    Usage::
        bridge = ErrorBridge(reporter)
        bridge.submit(ctx)          # submit one ErrorContext
        bridge.submit_all()         # submit everything in reporter
        healing = bridge.check_heal("MyError", ctx)
    """

    # Module-level tag used when recording in the error engine
    MODULE_TAG = "lateralus_lang.compiler"

    def __init__(self, reporter: Optional[ErrorReporter] = None):
        self._reporter = reporter
        self._engine   = _load_engine()
        self._dna_cache: Dict[str, Any] = {}

    # -- submit ----------------------------------------------------------------

    def submit(self, ctx: ErrorContext) -> None:
        """Forward *ctx* to the error engine if available."""
        if self._engine is None:
            return
        try:
            self._record_dna(ctx)
            self._record_causal(ctx)
            self._deduct_budget(ctx)
            self._check_archaeology(ctx)
        except Exception as exc:
            _log.debug("Error bridge submission failed: %s", exc)

    def submit_all(self) -> None:
        """Submit every error in the attached reporter."""
        if not self._reporter:
            return
        for ctx in self._reporter.all():
            self.submit(ctx)

    # -- healing ---------------------------------------------------------------

    def check_heal(self, error_code: str,
                   ctx: Optional[ErrorContext] = None) -> Optional[str]:
        """
        Query the self-healing contracts for *error_code*.
        Returns a healing action description, or None.
        """
        if self._engine is None:
            return None
        try:
            contracts = getattr(self._engine, "_healing_contracts", {})
            contract  = contracts.get(error_code) or contracts.get("*")
            if contract:
                action = getattr(contract, "strategy", None)
                desc   = getattr(contract, "description", str(contract))
                _log.info("Healing contract matched for %s: %s", error_code, desc)
                return str(desc)
        except Exception as exc:
            _log.debug("Healing check failed: %s", exc)
        return None

    # -- private helpers -------------------------------------------------------

    def _record_dna(self, ctx: ErrorContext) -> None:
        dna_fn = getattr(self._engine, "record_dna", None)
        if dna_fn:
            dna_fn(
                module   = self.MODULE_TAG,
                error_id = ctx.dna,
                exc_type = ctx.code,
                message  = ctx.message,
                severity = ctx.severity.name,
            )

    def _record_causal(self, ctx: ErrorContext) -> None:
        causal_fn = getattr(self._engine, "record_causal_edge", None)
        if causal_fn and ctx.chain:
            for cause in ctx.chain:
                causal_fn(
                    cause_id  = cause.dna,
                    effect_id = ctx.dna,
                    module    = self.MODULE_TAG,
                )

    def _deduct_budget(self, ctx: ErrorContext) -> None:
        budget_fn = getattr(self._engine, "deduct_budget", None)
        if budget_fn and ctx.severity in (Severity.ERROR, Severity.FATAL):
            budget_fn(module=self.MODULE_TAG, weight=1.0)

    def _check_archaeology(self, ctx: ErrorContext) -> None:
        arch_fn = getattr(self._engine, "find_historical_twin", None)
        if arch_fn:
            twin = arch_fn(dna=ctx.dna, module=self.MODULE_TAG)
            if twin:
                ctx.notes.append(
                    f"Historical twin found: {twin.get('error_id', '?')} "
                    f"at {twin.get('timestamp', '?')}"
                )


# -----------------------------------------------------------------------------
# Module-level singleton
# -----------------------------------------------------------------------------

_default_bridge: Optional[ErrorBridge] = None


def get_bridge(reporter: Optional[ErrorReporter] = None) -> ErrorBridge:
    """Get (or lazily create) the module-level bridge singleton."""
    global _default_bridge
    if _default_bridge is None or reporter is not None:
        _default_bridge = ErrorBridge(reporter)
    return _default_bridge


def submit_error(ctx: ErrorContext) -> None:
    """Convenience: submit one error to the default bridge."""
    get_bridge().submit(ctx)


def submit_exception(exc: Exception,
                     severity: Severity = Severity.ERROR,
                     reporter: Optional[ErrorReporter] = None) -> None:
    """Wrap and submit any Python exception."""
    bridge   = get_bridge(reporter)
    if reporter:
        reporter.add_exception(exc, severity)
        bridge.submit_all()
    else:
        if isinstance(exc, LTLError):
            ctx = exc.to_context(severity)
            bridge.submit(ctx)
