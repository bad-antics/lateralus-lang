"""
lateralus_lang/reactive.py
LATERALUS Reactive Programming Extension

Provides Observable streams, Signal/Computed/Effect primitives, and CSP-style
channels — inspired by MobX, RxJS, and Clojure's core.async.

Key primitives:
  - Signal[T]     : reactive state cell (read/write)
  - Computed[T]   : derived value, auto-updates when dependencies change
  - Effect        : side-effect that re-runs when signals it reads change
  - Observable[T] : lazy async/sync stream of values
  - Subject[T]    : hot observable (multicasts to all subscribers)
  - BehaviorSubject[T] : Subject that replays its latest value on subscribe
  - operators     : map, filter, scan, debounce, throttle, take, distinct_until_changed
"""

from __future__ import annotations

import threading
import weakref
from collections import deque
from contextlib import contextmanager
from typing import Any, Callable, Generic, Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")
U = TypeVar("U")

# ---------------------------------------------------------------------------
# Tracking context (like MobX's global tracking state)
# ---------------------------------------------------------------------------

class _TrackingContext:
    """Thread-local tracking context for auto-dependency detection."""
    def __init__(self) -> None:
        self._local = threading.local()

    @property
    def current_computation(self) -> Optional["Computed"]:
        stack = getattr(self._local, "stack", None)
        return stack[-1] if stack else None

    def push(self, comp: "Computed") -> None:
        if not hasattr(self._local, "stack"):
            self._local.stack = []
        self._local.stack.append(comp)

    def pop(self) -> None:
        stack = getattr(self._local, "stack", None)
        if stack:
            stack.pop()


_ctx = _TrackingContext()


# ---------------------------------------------------------------------------
# Signal — reactive state cell
# ---------------------------------------------------------------------------

class Signal(Generic[T]):
    """
    A reactive state container. Reading inside a Computed/Effect auto-registers
    as a dependency. Writing notifies all dependents.

    Usage:
        count = Signal(0)
        count.set(count.get() + 1)
        # or
        count.update(lambda v: v + 1)
    """

    def __init__(self, initial: T, name: str = "") -> None:
        self._value: T = initial
        self._name: str = name or f"signal_{id(self)}"
        self._observers: weakref.WeakSet["Computed"] = weakref.WeakSet()
        self._subscribers: dict[int, Callable] = {}
        self._lock = threading.Lock()

    def get(self) -> T:
        """Read the current value (and track dependency)."""
        comp = _ctx.current_computation
        if comp is not None:
            with self._lock:
                self._observers.add(comp)
        return self._value

    def __call__(self) -> T:
        """Shorthand: signal() instead of signal.get()."""
        return self.get()

    def set(self, value: T) -> None:
        """Write a new value and notify observers."""
        with self._lock:
            try:
                if self._value == value:
                    return
            except Exception:
                pass
            self._value = value
            observers = list(self._observers)
            subscribers = list(self._subscribers.values())
        for obs in observers:
            obs._invalidate()
        for cb in subscribers:
            cb(value)

    def update(self, fn: Callable[[T], T]) -> None:
        """Apply a function to update the value."""
        self.set(fn(self.get()))

    def subscribe(self, callback: Callable[[T], None]) -> Callable[[], None]:
        """Subscribe to value changes. Returns a dispose callable."""
        key = id(callback)
        self._subscribers[key] = callback
        def dispose() -> None:
            self._subscribers.pop(key, None)
        return dispose

    def __repr__(self) -> str:
        return f"Signal({self._name}={self._value!r})"


# ---------------------------------------------------------------------------
# Computed — derived reactive value
# ---------------------------------------------------------------------------

class Computed(Generic[T]):
    """
    A derived value that auto-recomputes when its signal dependencies change.

    Usage:
        x = Signal(3)
        y = Signal(4)
        hyp = Computed(lambda: (x() ** 2 + y() ** 2) ** 0.5)
        hyp.get()  # 5.0
        x.set(6); hyp.get()  # 7.211...
    """

    def __init__(self, fn: Callable[[], T], name: str = "") -> None:
        self._fn = fn
        self._name = name or f"computed_{id(self)}"
        self._value: Optional[T] = None
        self._valid: bool = False
        self._observers: weakref.WeakSet["Computed"] = weakref.WeakSet()
        self._lock = threading.Lock()

    def _invalidate(self) -> None:
        observers = []
        with self._lock:
            if self._valid:
                self._valid = False
                observers = list(self._observers)
        for obs in observers:
            obs._invalidate()
        # Also run effects if any
        _effect_scheduler.schedule(self)

    def get(self) -> T:
        """Return the current (possibly recomputed) value."""
        with self._lock:
            if self._valid:
                comp = _ctx.current_computation
                if comp is not None:
                    self._observers.add(comp)
                return self._value  # type: ignore

        # Recompute
        _ctx.push(self)
        try:
            new_val = self._fn()
        finally:
            _ctx.pop()

        with self._lock:
            self._value = new_val
            self._valid = True
            comp = _ctx.current_computation
            if comp is not None:
                self._observers.add(comp)
        return new_val

    def __call__(self) -> T:
        return self.get()

    def __repr__(self) -> str:
        return f"Computed({self._name})"


# ---------------------------------------------------------------------------
# Effect — reactive side effect
# ---------------------------------------------------------------------------

class _EffectScheduler:
    """Batches and runs effects."""

    def __init__(self) -> None:
        self._pending: set[Any] = set()
        self._batching: bool = False

    def schedule(self, computation: Any) -> None:
        self._pending.add(computation)
        if not self._batching:
            self._flush()

    def begin_batch(self) -> None:
        self._batching = True

    def end_batch(self) -> None:
        self._batching = False
        self._flush()

    def _flush(self) -> None:
        while self._pending:
            comp = self._pending.pop()
            if isinstance(comp, Effect):
                comp._run()


_effect_scheduler = _EffectScheduler()


class Effect:
    """
    A side effect that runs whenever its signal dependencies change.

    Usage:
        count = Signal(0)
        log = Effect(lambda: print(f"count is {count()}"))
        count.set(1)   # automatically prints "count is 1"
        effect.dispose()  # stop tracking
    """

    def __init__(self, fn: Callable[[], None]) -> None:
        self._fn = fn
        self._active = True
        self._deps: list[Signal] = []
        self._run()

    def _run(self) -> None:
        if not self._active:
            return
        _ctx.push(self)  # type: ignore
        try:
            self._fn()
        finally:
            _ctx.pop()

    def _invalidate(self) -> None:
        if self._active:
            _effect_scheduler.schedule(self)

    def dispose(self) -> None:
        """Stop this effect from re-running."""
        self._active = False

    def __repr__(self) -> str:
        return f"Effect({'active' if self._active else 'disposed'})"


# ---------------------------------------------------------------------------
# Observable — lazy stream
# ---------------------------------------------------------------------------

class Observable(Generic[T]):
    """
    A lazy, composable stream of values.

    Usage:
        stream = Observable.from_iterable([1, 2, 3, 4, 5])
        result = stream.filter(lambda x: x % 2 == 0).map(lambda x: x * 10).to_list()
        # [20, 40]
    """

    def __init__(self, subscribe_fn: Callable[["Observer[T]"], None]) -> None:
        self._subscribe_fn = subscribe_fn

    def subscribe(self, on_next: Optional[Callable[[T], None]] = None,
                  on_error: Optional[Callable[[Exception], None]] = None,
                  on_complete: Optional[Callable[[], None]] = None) -> "Subscription":
        obs = Observer(on_next or (lambda _: None),
                       on_error or (lambda e: None),
                       on_complete or (lambda: None))
        self._subscribe_fn(obs)
        return Subscription(obs)

    def to_list(self) -> list[T]:
        results: list[T] = []
        self.subscribe(on_next=results.append)
        return results

    def to_generator(self) -> Iterator[T]:
        return iter(self.to_list())

    # -- Operators -----------------------------------------------------------

    def map(self, fn: Callable[[T], U]) -> "Observable[U]":
        def subscribe(observer: "Observer[U]") -> None:
            def on_next(val: T) -> None:
                try:
                    observer.on_next(fn(val))
                except Exception as e:
                    observer.on_error(e)
            self.subscribe(on_next=on_next, on_error=observer.on_error,
                           on_complete=observer.on_complete)
        return Observable(subscribe)

    def filter(self, predicate: Callable[[T], bool]) -> "Observable[T]":
        def subscribe(observer: "Observer[T]") -> None:
            def on_next(val: T) -> None:
                try:
                    if predicate(val):
                        observer.on_next(val)
                except Exception as e:
                    observer.on_error(e)
            self.subscribe(on_next=on_next, on_error=observer.on_error,
                           on_complete=observer.on_complete)
        return Observable(subscribe)

    def scan(self, fn: Callable[[U, T], U], seed: U) -> "Observable[U]":
        """Accumulate values like reduce but emitting each intermediate result."""
        def subscribe(observer: "Observer[U]") -> None:
            acc = [seed]
            def on_next(val: T) -> None:
                try:
                    acc[0] = fn(acc[0], val)
                    observer.on_next(acc[0])
                except Exception as e:
                    observer.on_error(e)
            self.subscribe(on_next=on_next, on_error=observer.on_error,
                           on_complete=observer.on_complete)
        return Observable(subscribe)

    def take(self, n: int) -> "Observable[T]":
        """Emit only the first n values."""
        def subscribe(observer: "Observer[T]") -> None:
            count = [0]
            def on_next(val: T) -> None:
                if count[0] < n:
                    count[0] += 1
                    observer.on_next(val)
                    if count[0] >= n:
                        observer.on_complete()
            self.subscribe(on_next=on_next, on_error=observer.on_error,
                           on_complete=observer.on_complete)
        return Observable(subscribe)

    def skip(self, n: int) -> "Observable[T]":
        """Skip the first n values."""
        def subscribe(observer: "Observer[T]") -> None:
            count = [0]
            def on_next(val: T) -> None:
                if count[0] < n:
                    count[0] += 1
                else:
                    observer.on_next(val)
            self.subscribe(on_next=on_next, on_error=observer.on_error,
                           on_complete=observer.on_complete)
        return Observable(subscribe)

    def distinct_until_changed(self, key: Optional[Callable[[T], Any]] = None) -> "Observable[T]":
        """Only emit when value changes."""
        def subscribe(observer: "Observer[T]") -> None:
            prev = [object()]  # sentinel
            def on_next(val: T) -> None:
                k = key(val) if key else val
                if k != prev[0]:
                    prev[0] = k
                    observer.on_next(val)
            self.subscribe(on_next=on_next, on_error=observer.on_error,
                           on_complete=observer.on_complete)
        return Observable(subscribe)

    def buffer(self, size: int) -> "Observable[list[T]]":
        """Collect items into fixed-size buffers."""
        def subscribe(observer: "Observer[list[T]]") -> None:
            buf: list[T] = []
            def on_next(val: T) -> None:
                buf.append(val)
                if len(buf) >= size:
                    observer.on_next(list(buf))
                    buf.clear()
            def on_complete() -> None:
                if buf:
                    observer.on_next(list(buf))
                observer.on_complete()
            self.subscribe(on_next=on_next, on_error=observer.on_error, on_complete=on_complete)
        return Observable(subscribe)

    def flat_map(self, fn: Callable[[T], "Observable[U]"]) -> "Observable[U]":
        """Map to observables and flatten."""
        def subscribe(observer: "Observer[U]") -> None:
            def on_next(val: T) -> None:
                inner = fn(val)
                inner.subscribe(on_next=observer.on_next, on_error=observer.on_error)
            self.subscribe(on_next=on_next, on_error=observer.on_error,
                           on_complete=observer.on_complete)
        return Observable(subscribe)

    def zip_with(self, other: "Observable[U]") -> "Observable[tuple[T, U]]":
        """Zip two observables together."""
        def subscribe(observer: "Observer[tuple[T, U]]") -> None:
            left_buf: deque[T] = deque()
            right_buf: deque[U] = deque()
            def emit_if_paired() -> None:
                while left_buf and right_buf:
                    observer.on_next((left_buf.popleft(), right_buf.popleft()))
            self.subscribe(on_next=lambda v: (left_buf.append(v), emit_if_paired()))
            other.subscribe(on_next=lambda v: (right_buf.append(v), emit_if_paired()))
        return Observable(subscribe)

    def tap(self, fn: Callable[[T], None]) -> "Observable[T]":
        """Side-effect without modifying stream."""
        return self.map(lambda v: (fn(v), v)[1])

    def reduce(self, fn: Callable[[U, T], U], seed: U) -> U:
        """Reduce stream to a single scalar value."""
        acc = [seed]
        self.subscribe(on_next=lambda val: acc.__setitem__(0, fn(acc[0], val)))
        return acc[0]

    def count(self) -> int:
        """Count the number of emitted items."""
        return self.reduce(lambda a, _: a + 1, 0)

    def sum(self) -> Any:
        """Sum all emitted numeric values."""
        return self.reduce(lambda a, v: a + v, 0)

    # -- Static constructors -------------------------------------------------

    @staticmethod
    def of(*values: T) -> "Observable[T]":
        def subscribe(obs: "Observer[T]") -> None:
            for v in values:
                obs.on_next(v)
            obs.on_complete()
        return Observable(subscribe)

    @staticmethod
    def from_iterable(iterable: Iterable[T]) -> "Observable[T]":
        def subscribe(obs: "Observer[T]") -> None:
            try:
                for v in iterable:
                    obs.on_next(v)
                obs.on_complete()
            except Exception as e:
                obs.on_error(e)
        return Observable(subscribe)

    @staticmethod
    def empty() -> "Observable":
        def subscribe(obs: "Observer") -> None:
            obs.on_complete()
        return Observable(subscribe)

    @staticmethod
    def never() -> "Observable":
        return Observable(lambda _: None)

    @staticmethod
    def throw(error: Exception) -> "Observable":
        def subscribe(obs: "Observer") -> None:
            obs.on_error(error)
        return Observable(subscribe)

    @staticmethod
    def range(start: int, stop: int, step: int = 1) -> "Observable[int]":
        """Inclusive range from start to stop."""
        return Observable.from_iterable(range(start, stop + 1, step))

    @staticmethod
    def merge(*observables: "Observable[T]") -> "Observable[T]":
        """Merge multiple observables into one."""
        def subscribe(obs: "Observer[T]") -> None:
            for o in observables:
                o.subscribe(on_next=obs.on_next, on_error=obs.on_error)
            obs.on_complete()
        return Observable(subscribe)

    @staticmethod
    def concat(*observables: "Observable[T]") -> "Observable[T]":
        """Concatenate observables sequentially."""
        def subscribe(obs: "Observer[T]") -> None:
            for o in observables:
                o.subscribe(on_next=obs.on_next, on_error=obs.on_error)
            obs.on_complete()
        return Observable(subscribe)

    @staticmethod
    def from_signal(signal: "Signal[T]") -> "Observable[T]":
        """Create an observable that emits current value and future signal changes."""
        def subscribe(obs: "Observer[T]") -> None:
            obs.on_next(signal.get())
            signal.subscribe(obs.on_next)
        return Observable(subscribe)

    def __repr__(self) -> str:
        return "Observable()"


# ---------------------------------------------------------------------------
# Observer
# ---------------------------------------------------------------------------

class Observer(Generic[T]):
    def __init__(self, on_next: Callable[[T], None],
                 on_error: Callable[[Exception], None],
                 on_complete: Callable[[], None]) -> None:
        self.on_next = on_next
        self.on_error = on_error
        self.on_complete = on_complete
        self._completed = False

    def __repr__(self) -> str:
        return "Observer()"


class Subscription:
    def __init__(self, observer: Observer) -> None:
        self._observer = observer

    def unsubscribe(self) -> None:
        self._observer.on_complete = lambda: None
        self._observer.on_next = lambda _: None


# ---------------------------------------------------------------------------
# Subject — hot observable / event emitter
# ---------------------------------------------------------------------------

class Subject(Generic[T]):
    """
    A Subject is both an Observable and an Observer.
    It multicasts to all current subscribers.

    Usage:
        s = Subject()
        s.subscribe(lambda v: print(f"got {v}"))
        s.emit(42)   # prints "got 42"
    """

    def __init__(self) -> None:
        self._observers: list[Observer[T]] = []
        self._completed = False
        self._error: Optional[Exception] = None

    def subscribe(self, on_next: Optional[Callable[[T], None]] = None,
                  on_error: Optional[Callable[[Exception], None]] = None,
                  on_complete: Optional[Callable[[], None]] = None) -> Subscription:
        obs = Observer(on_next or (lambda _: None),
                       on_error or (lambda e: None),
                       on_complete or (lambda: None))
        if self._completed:
            obs.on_complete()
        elif self._error:
            obs.on_error(self._error)
        else:
            self._observers.append(obs)
        return Subscription(obs)

    def emit(self, value: T) -> None:
        """Emit a value to all subscribers."""
        for obs in list(self._observers):
            obs.on_next(value)

    def error(self, err: Exception) -> None:
        self._error = err
        for obs in list(self._observers):
            obs.on_error(err)
        self._observers.clear()

    def complete(self) -> None:
        self._completed = True
        for obs in list(self._observers):
            obs.on_complete()
        self._observers.clear()

    def as_observable(self) -> Observable[T]:
        def subscribe(obs: Observer[T]) -> None:
            self._observers.append(obs)
        return Observable(subscribe)

    def __repr__(self) -> str:
        return f"Subject(subscribers={len(self._observers)})"


class BehaviorSubject(Subject[T]):
    """
    A Subject that replays the most recent value to new subscribers.

    Usage:
        s = BehaviorSubject(0)
        s.subscribe(print)   # immediately prints 0
        s.emit(42)           # prints 42
        s.subscribe(print)   # immediately prints 42
    """

    def __init__(self, initial: T) -> None:
        super().__init__()
        self._latest: T = initial

    def subscribe(self, on_next=None, on_error=None, on_complete=None) -> Subscription:
        sub = super().subscribe(on_next, on_error, on_complete)
        if on_next:
            on_next(self._latest)
        return sub

    def emit(self, value: T) -> None:
        self._latest = value
        super().emit(value)

    @property
    def value(self) -> T:
        """The most recently emitted value."""
        return self._latest

    def get(self) -> T:
        return self._latest

    def __call__(self) -> T:
        return self._latest


class ReplaySubject(Subject[T]):
    """A Subject that replays up to `buffer_size` most recent values."""

    def __init__(self, buffer_size: int = 100) -> None:
        super().__init__()
        self._buffer: deque[T] = deque(maxlen=buffer_size)

    def subscribe(self, on_next=None, on_error=None, on_complete=None) -> Subscription:
        sub = super().subscribe(on_next, on_error, on_complete)
        if on_next:
            for v in self._buffer:
                on_next(v)
        return sub

    def emit(self, value: T) -> None:
        self._buffer.append(value)
        super().emit(value)


# ---------------------------------------------------------------------------
# Store — centralized reactive state (like Redux + MobX)
# ---------------------------------------------------------------------------

class Store(Generic[T]):
    """
    A centralized state store with actions and computed selectors.

    Usage:
        store = Store({"count": 0})

        @store.action
        def increment(state, amount=1):
            return {**state, "count": state["count"] + amount}

        store.dispatch("increment", amount=5)
        print(store.state["count"])  # 5
    """

    def __init__(self, initial_state: T) -> None:
        self._state_signal: Signal[T] = Signal(initial_state, "store")
        self._actions_registry: dict[str, Callable] = {}
        self._action_history: list[tuple[str, dict]] = []
        self._subscribers: list[Callable[[T], None]] = []

    @property
    def state(self) -> T:
        """Current state value."""
        return self._state_signal.get()

    def action(self, fn: Callable) -> Callable:
        """Decorator to register a named action handler."""
        self._actions_registry[fn.__name__] = fn
        return fn

    def selector(self, fn: Callable) -> Callable:
        """Decorator that creates a selector function bound to this store."""
        store = self
        def selected(*args, **kwargs):
            return fn(store._state_signal.get(), *args, **kwargs)
        return selected

    def dispatch(self, action_name: str, **kwargs) -> None:
        """Dispatch a named action with optional keyword payload."""
        fn = self._actions_registry.get(action_name)
        if fn is None:
            raise KeyError(f"Unknown action: {action_name!r}")
        old = self._state_signal.get()
        new = fn(old, **kwargs)
        self._action_history.append((action_name, kwargs))
        self._state_signal.set(new)
        for cb in self._subscribers:
            cb(new)

    def subscribe(self, callback: Callable[[T], None]) -> None:
        """Subscribe to state changes."""
        self._subscribers.append(callback)

    def select(self, selector_fn: Callable[[T], U]) -> "Observable[U]":
        """Create an observable from a selector function."""
        computed = Computed(lambda: selector_fn(self._state_signal.get()))
        return Observable.from_iterable([computed.get()])

    def get_state(self) -> T:
        """Get current state (legacy API)."""
        return self._state_signal.get()

    def use_middleware(self, mw: Callable) -> None:
        pass  # simplified

    @property
    def action_log(self) -> list:
        """History of dispatched actions."""
        return list(self._action_history)


# ---------------------------------------------------------------------------
# Utility: batch updates
# ---------------------------------------------------------------------------

@contextmanager
def batch():
    """
    Context manager to batch multiple signal updates.

    Usage:
        with batch():
            x.set(1)
            y.set(2)
        # Effects/reactions fire once at end of block
    """
    _effect_scheduler.begin_batch()
    try:
        yield
    finally:
        _effect_scheduler.end_batch()


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def signal(value: T, name: str = "") -> Signal[T]:
    """Create a Signal."""
    return Signal(value, name)


def computed(fn: Callable[[], T], name: str = "") -> Computed[T]:
    """Create a Computed."""
    return Computed(fn, name)


def effect(fn: Callable[[], None]) -> Effect:
    """Create an Effect."""
    return Effect(fn)


def subject() -> Subject:
    """Create a Subject."""
    return Subject()


def behavior_subject(initial: T) -> BehaviorSubject[T]:
    """Create a BehaviorSubject."""
    return BehaviorSubject(initial)


def observable_of(*values: T) -> Observable[T]:
    """Create an Observable from values."""
    return Observable.of(*values)


def from_iterable(it: Iterable[T]) -> Observable[T]:
    """Create an Observable from an iterable."""
    return Observable.from_iterable(it)


# ---------------------------------------------------------------------------
# LATERALUS runtime builtins
# ---------------------------------------------------------------------------

def get_reactive_builtins() -> dict:
    return {
        "Signal":          Signal,
        "Computed":        Computed,
        "Effect":          Effect,
        "Observable":      Observable,
        "Subject":         Subject,
        "BehaviorSubject": BehaviorSubject,
        "ReplaySubject":   ReplaySubject,
        "Store":           Store,
        "signal":          signal,
        "computed":        computed,
        "effect":          effect,
        "subject":         subject,
        "behavior_subject": behavior_subject,
        "observable_of":   observable_of,
        "from_iterable":   from_iterable,
        "batch":           batch,
    }
