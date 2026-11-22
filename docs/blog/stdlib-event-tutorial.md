# Pub/Sub Events with `stdlib/event.ltl`

The event emitter is the glue of every UI framework and plugin system:
register handlers, fire events, let components stay decoupled.
`stdlib/event.ltl` implements a compact version in about 140 lines —
plain maps of event name → handler list, with one-shot wrappers,
filtering, and cross-emitter piping.

This tutorial exercises the full lifecycle. Companion:
`examples/event_tutorial.ltl`.

---

## Registration

- `on(emitter, event, handler)` appends a handler
- `once(emitter, event, handler)` wraps it as `["once", handler]` so
  `fire` knows to discard it after one call
- `off` removes a *specific* handler (function equality); `off_all`
  clears the event

## Emission

`fire(emitter, event, data)` calls every handler with `data`. One-shot
entries fire then drop out of the kept list — the tutorial shows
`user.login` going from 3 handlers to 2 after the first fire. Firing an
unregistered event is a no-op; `fire_empty` passes `nil`.

## Inspection & utilities

`event_names`, `handler_count`, `has_listeners`, `total_handlers` read
the emitter; `filter_events(emitter, pred)` builds a view containing
only events whose *name* matches; `pipe(source, target, event)` forwards
one event from emitter to emitter; `reset` returns a fresh emitter.

## Two runtime quirks the tutorial works around

1. **`typeof(h) == "list"` never matches** — `typeof` yields the Python
   class object (`<class 'list'>`), not the string `"list"`, so the
   module's once-detection was dead code and `fire` would have tried to
   *call* the `["once", handler]` list. The inlined copy compares
   `typeof(h) == typeof([])` instead. Module bug flagged for a fix PR.
2. **Lambdas can't rebind globals** — demo handlers close over a shared
   `box` map (`box["log"] = box["log"] + […]`) rather than a top-level
   `LOG` variable, which raises `UnboundLocalError`.

## Running the tutorial

```bash
python -m lateralus_lang run examples/event_tutorial.ltl
python -m lateralus_lang check examples/event_tutorial.ltl
python -m pytest tests/test_event_tutorial.py -x -q
```
