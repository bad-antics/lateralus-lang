"""
tests/test_reactive.py
Tests for lateralus_lang.reactive — Signals, Observables, Subjects, Store
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from lateralus_lang.reactive import (
    BehaviorSubject,
    Computed,
    Effect,
    Observable,
    ReplaySubject,
    Signal,
    Store,
    Subject,
    batch,
    get_reactive_builtins,
)

# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------

class TestSignal:
    def test_initial_value(self):
        s = Signal(42)
        assert s.get() == 42

    def test_set_value(self):
        s = Signal(0)
        s.set(99)
        assert s.get() == 99

    def test_update_value(self):
        s = Signal(10)
        s.update(lambda x: x * 2)
        assert s.get() == 20

    def test_observer_called_on_change(self):
        s = Signal(1)
        seen = []
        s.subscribe(lambda v: seen.append(v))
        s.set(2)
        s.set(3)
        assert 2 in seen
        assert 3 in seen

    def test_observer_not_called_when_same_value(self):
        s = Signal(5)
        count = [0]
        s.subscribe(lambda v: count.__setitem__(0, count[0] + 1))
        s.set(5)  # same value
        assert count[0] == 0

    def test_multiple_observers(self):
        s = Signal("hello")
        log1, log2 = [], []
        s.subscribe(lambda v: log1.append(v))
        s.subscribe(lambda v: log2.append(v))
        s.set("world")
        assert "world" in log1
        assert "world" in log2

    def test_unsubscribe(self):
        s = Signal(0)
        seen = []
        dispose = s.subscribe(lambda v: seen.append(v))
        s.set(1)
        dispose()
        s.set(2)
        assert 1 in seen
        assert 2 not in seen

    def test_repr(self):
        s = Signal(42)
        assert "42" in repr(s)


# ---------------------------------------------------------------------------
# Computed
# ---------------------------------------------------------------------------

class TestComputed:
    def test_derived_value(self):
        a = Signal(3)
        b = Signal(4)
        c = Computed(lambda: a.get() ** 2 + b.get() ** 2)
        assert c.get() == 25

    def test_auto_recompute(self):
        x = Signal(2)
        doubled = Computed(lambda: x.get() * 2)
        assert doubled.get() == 4
        x.set(5)
        assert doubled.get() == 10

    def test_chain_computed(self):
        x = Signal(1)
        y = Computed(lambda: x.get() + 1)
        z = Computed(lambda: y.get() * 2)
        assert z.get() == 4
        x.set(4)
        assert z.get() == 10

    def test_computed_only_recomputes_when_needed(self):
        compute_count = [0]
        x = Signal(1)

        def expensive():
            compute_count[0] += 1
            return x.get() * 10

        c = Computed(expensive)
        _ = c.get()
        _ = c.get()  # second access should not recompute
        x.set(2)
        _ = c.get()  # recompute due to dependency change

        assert compute_count[0] == 2  # initial + after x changed


# ---------------------------------------------------------------------------
# Effect
# ---------------------------------------------------------------------------

class TestEffect:
    def test_effect_runs_immediately(self):
        x = Signal(1)
        log = []
        eff = Effect(lambda: log.append(x.get()))
        assert len(log) > 0

    def test_effect_reruns_on_signal_change(self):
        x = Signal(0)
        log = []
        eff = Effect(lambda: log.append(x.get()))
        x.set(1)
        x.set(2)
        assert 1 in log
        assert 2 in log

    def test_effect_dispose_stops_reruns(self):
        x = Signal(0)
        count = [0]
        eff = Effect(lambda: (count.__setitem__(0, count[0] + 1), x.get()))
        initial = count[0]
        eff.dispose()
        x.set(99)
        assert count[0] == initial


# ---------------------------------------------------------------------------
# Observable
# ---------------------------------------------------------------------------

class TestObservable:
    def test_of_creates_observable(self):
        obs = Observable.of(1, 2, 3)
        collected = []
        obs.subscribe(lambda v: collected.append(v))
        assert collected == [1, 2, 3]

    def test_from_iterable(self):
        obs = Observable.from_iterable(range(5))
        result = []
        obs.subscribe(lambda v: result.append(v))
        assert result == [0, 1, 2, 3, 4]

    def test_map(self):
        obs = Observable.of(1, 2, 3).map(lambda x: x * 10)
        result = []
        obs.subscribe(lambda v: result.append(v))
        assert result == [10, 20, 30]

    def test_filter(self):
        obs = Observable.of(1, 2, 3, 4, 5).filter(lambda x: x % 2 == 0)
        result = []
        obs.subscribe(lambda v: result.append(v))
        assert result == [2, 4]

    def test_take(self):
        obs = Observable.from_iterable(range(100)).take(3)
        result = []
        obs.subscribe(lambda v: result.append(v))
        assert result == [0, 1, 2]

    def test_skip(self):
        obs = Observable.of(1, 2, 3, 4, 5).skip(3)
        result = []
        obs.subscribe(lambda v: result.append(v))
        assert result == [4, 5]

    def test_scan(self):
        obs = Observable.of(1, 2, 3, 4).scan(lambda acc, x: acc + x, 0)
        result = []
        obs.subscribe(lambda v: result.append(v))
        assert result[-1] == 10

    def test_reduce(self):
        total = Observable.of(1, 2, 3, 4, 5).reduce(lambda acc, x: acc + x, 0)
        assert total == 15

    def test_distinct_until_changed(self):
        obs = Observable.of(1, 1, 2, 2, 3, 1, 1).distinct_until_changed()
        result = []
        obs.subscribe(lambda v: result.append(v))
        assert result == [1, 2, 3, 1]

    def test_flat_map(self):
        obs = Observable.of(1, 2, 3).flat_map(lambda x: Observable.of(x, x * 10))
        result = []
        obs.subscribe(lambda v: result.append(v))
        assert result == [1, 10, 2, 20, 3, 30]

    def test_buffer(self):
        obs = Observable.of(1, 2, 3, 4, 5, 6).buffer(2)
        result = []
        obs.subscribe(lambda v: result.append(v))
        assert result == [[1, 2], [3, 4], [5, 6]]

    def test_sum_operator(self):
        total = Observable.of(10, 20, 30).sum()
        assert total == 60

    def test_count_operator(self):
        n = Observable.of(1, 2, 3, 4).count()
        assert n == 4

    def test_empty(self):
        result = []
        Observable.empty().subscribe(lambda v: result.append(v))
        assert result == []

    def test_range(self):
        result = []
        Observable.range(1, 5).subscribe(lambda v: result.append(v))
        assert result == [1, 2, 3, 4, 5]

    def test_merge(self):
        a = Observable.of(1, 3)
        b = Observable.of(2, 4)
        result = []
        Observable.merge(a, b).subscribe(lambda v: result.append(v))
        assert set(result) == {1, 2, 3, 4}

    def test_concat(self):
        a = Observable.of(1, 2)
        b = Observable.of(3, 4)
        result = []
        Observable.concat(a, b).subscribe(lambda v: result.append(v))
        assert result == [1, 2, 3, 4]

    def test_tap_does_not_change_values(self):
        log = []
        result = []
        (Observable.of(1, 2, 3)
         .tap(lambda v: log.append(v))
         .subscribe(lambda v: result.append(v)))
        assert log == [1, 2, 3]
        assert result == [1, 2, 3]

    def test_from_signal(self):
        s = Signal(0)
        result = []
        obs = Observable.from_signal(s)
        obs.subscribe(lambda v: result.append(v))
        s.set(1)
        s.set(2)
        assert 1 in result
        assert 2 in result


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------

class TestSubject:
    def test_emit_pushes_to_subscribers(self):
        subj = Subject()
        result = []
        subj.subscribe(lambda v: result.append(v))
        subj.emit(42)
        assert 42 in result

    def test_multiple_subscribers(self):
        subj = Subject()
        r1, r2 = [], []
        subj.subscribe(lambda v: r1.append(v))
        subj.subscribe(lambda v: r2.append(v))
        subj.emit("hello")
        assert "hello" in r1
        assert "hello" in r2

    def test_complete_stops_emissions(self):
        subj = Subject()
        result = []
        subj.subscribe(lambda v: result.append(v))
        subj.emit(1)
        subj.complete()
        subj.emit(2)
        assert 1 in result
        assert 2 not in result


class TestBehaviorSubject:
    def test_initial_value_replayed(self):
        subj = BehaviorSubject(100)
        result = []
        subj.subscribe(lambda v: result.append(v))
        assert 100 in result

    def test_latest_value_replayed(self):
        subj = BehaviorSubject(1)
        subj.emit(2)
        subj.emit(3)
        result = []
        subj.subscribe(lambda v: result.append(v))
        assert result[0] == 3

    def test_value_property(self):
        subj = BehaviorSubject(42)
        subj.emit(99)
        assert subj.value == 99


class TestReplaySubject:
    def test_replays_buffered_values(self):
        subj = ReplaySubject(buffer_size=3)
        subj.emit(1)
        subj.emit(2)
        subj.emit(3)
        subj.emit(4)
        result = []
        subj.subscribe(lambda v: result.append(v))
        # Should replay last 3
        assert result == [2, 3, 4]

    def test_new_emissions_after_subscribe(self):
        subj = ReplaySubject(buffer_size=2)
        subj.emit(1)
        result = []
        subj.subscribe(lambda v: result.append(v))
        subj.emit(5)
        assert 5 in result


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class TestStore:
    def test_initial_state(self):
        store = Store({"count": 0})
        assert store.state["count"] == 0

    def test_dispatch_updates_state(self):
        store = Store({"count": 0})

        @store.action
        def increment(state, amount=1):
            return {**state, "count": state["count"] + amount}

        store.dispatch("increment")
        assert store.state["count"] == 1

    def test_dispatch_with_payload(self):
        store = Store({"count": 0})

        @store.action
        def add(state, amount=1):
            return {**state, "count": state["count"] + amount}

        store.dispatch("add", amount=5)
        assert store.state["count"] == 5

    def test_selector(self):
        store = Store({"user": {"name": "Alice", "age": 30}})

        @store.selector
        def get_name(state):
            return state["user"]["name"]

        assert get_name() == "Alice"

    def test_subscribe_called_on_change(self):
        store = Store({"x": 0})

        @store.action
        def set_x(state, val=0):
            return {**state, "x": val}

        log = []
        store.subscribe(lambda s: log.append(s["x"]))
        store.dispatch("set_x", val=42)
        assert 42 in log

    def test_action_log(self):
        store = Store({"n": 0})

        @store.action
        def tick(state):
            return {**state, "n": state["n"] + 1}

        store.dispatch("tick")
        store.dispatch("tick")
        history = store.action_log
        assert len(history) >= 2


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------

class TestBatch:
    def test_batch_suppresses_intermediate_notifications(self):
        a = Signal(0)
        b = Signal(0)
        log = []

        # Subscribe to computed that watches both
        c = Computed(lambda: a.get() + b.get())
        eff = Effect(lambda: log.append(c.get()))

        initial_count = len(log)

        # Without batch: multiple notifications
        # With batch: only one notification at end
        with batch():
            a.set(10)
            b.set(20)

        # After batch, at most one notification
        final_count = len(log)
        assert final_count - initial_count <= 1


# ---------------------------------------------------------------------------
# Builtins
# ---------------------------------------------------------------------------

class TestBuiltins:
    def test_get_reactive_builtins(self):
        builtins = get_reactive_builtins()
        assert "Signal" in builtins
        assert "Computed" in builtins
        assert "Effect" in builtins
        assert "Observable" in builtins
        assert "Subject" in builtins
        assert "Store" in builtins

    def test_builtins_are_callable(self):
        builtins = get_reactive_builtins()
        s = builtins["Signal"](42)
        assert s.get() == 42
