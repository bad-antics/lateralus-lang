"""
lateralus_lang/async_runtime.py — Async/concurrent execution runtime for LATERALUS

Provides:
  - Async task execution (coroutine-based)
  - Parallel pipeline execution
  - Channel-based communication (CSP-style, Go-inspired)
  - Task groups with structured concurrency
  - Rate limiting and backpressure
"""

from __future__ import annotations

import asyncio
import time
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from enum import Enum, auto

T = TypeVar("T")
R = TypeVar("R")


# ─── Task Status ───────────────────────────────────────────────────────

class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


# ─── Task Result ───────────────────────────────────────────────────────

@dataclass
class TaskResult:
    """Result of an async task execution."""
    status: TaskStatus
    value: Any = None
    error: Optional[Exception] = None
    elapsed_ms: float = 0.0
    task_id: str = ""

    @property
    def is_ok(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def is_err(self) -> bool:
        return self.status == TaskStatus.FAILED


# ─── Channel (CSP-style) ──────────────────────────────────────────────

class Channel:
    """
    A bounded, thread-safe channel for communicating between tasks.
    Inspired by Go channels and Rust's mpsc.

    Usage:
        ch = Channel(capacity=10)
        ch.send("hello")
        msg = ch.recv()
    """

    def __init__(self, capacity: int = 0):
        """
        Create a channel.
        capacity=0 means unbuffered (synchronous send/recv).
        capacity>0 means buffered.
        """
        self._capacity = max(capacity, 0)
        self._buffer: deque = deque()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._closed = False
        self._send_count = 0
        self._recv_count = 0

    def send(self, value: Any, timeout: Optional[float] = None) -> bool:
        """
        Send a value on the channel.
        Blocks if buffer is full. Returns False if channel is closed.
        """
        with self._not_full:
            if self._closed:
                return False

            while self._capacity > 0 and len(self._buffer) >= self._capacity:
                if self._closed:
                    return False
                if not self._not_full.wait(timeout=timeout):
                    return False  # Timeout

            if self._closed:
                return False

            self._buffer.append(value)
            self._send_count += 1
            self._not_empty.notify()
            return True

    def recv(self, timeout: Optional[float] = None) -> Optional[Any]:
        """
        Receive a value from the channel.
        Blocks if buffer is empty. Returns None if channel is closed and empty.
        """
        with self._not_empty:
            while len(self._buffer) == 0:
                if self._closed:
                    return None
                if not self._not_empty.wait(timeout=timeout):
                    return None  # Timeout

            value = self._buffer.popleft()
            self._recv_count += 1
            self._not_full.notify()
            return value

    def try_send(self, value: Any) -> bool:
        """Non-blocking send. Returns True if successful."""
        with self._lock:
            if self._closed:
                return False
            if self._capacity > 0 and len(self._buffer) >= self._capacity:
                return False
            self._buffer.append(value)
            self._send_count += 1
            self._not_empty.notify()
            return True

    def try_recv(self) -> Optional[Any]:
        """Non-blocking receive. Returns None if empty."""
        with self._lock:
            if len(self._buffer) == 0:
                return None
            value = self._buffer.popleft()
            self._recv_count += 1
            self._not_full.notify()
            return value

    def close(self):
        """Close the channel. No more sends allowed."""
        with self._lock:
            self._closed = True
            self._not_empty.notify_all()
            self._not_full.notify_all()

    @property
    def is_closed(self) -> bool:
        return self._closed

    @property
    def is_empty(self) -> bool:
        return len(self._buffer) == 0

    def __len__(self) -> int:
        return len(self._buffer)

    def __iter__(self):
        """Iterate over channel values until closed."""
        while True:
            val = self.recv()
            if val is None and self._closed:
                break
            yield val


# ─── Task Group ────────────────────────────────────────────────────────

class TaskGroup:
    """
    Structured concurrency: run multiple tasks and wait for all to complete.
    Similar to Python's asyncio.TaskGroup or Trio's nurseries.

    Usage:
        group = TaskGroup()
        group.spawn(fn1, args1)
        group.spawn(fn2, args2)
        results = group.wait_all()
    """

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: List[Future] = []
        self._task_ids: List[str] = []
        self._counter = 0

    def spawn(self, fn: Callable, *args, task_id: Optional[str] = None, **kwargs) -> str:
        """Spawn a new task in this group."""
        self._counter += 1
        tid = task_id or f"task-{self._counter}"
        future = self._executor.submit(fn, *args, **kwargs)
        self._futures.append(future)
        self._task_ids.append(tid)
        return tid

    def wait_all(self, timeout: Optional[float] = None) -> List[TaskResult]:
        """Wait for all tasks to complete and return results."""
        results = []
        for future, tid in zip(self._futures, self._task_ids):
            start = time.perf_counter()
            try:
                value = future.result(timeout=timeout)
                elapsed = (time.perf_counter() - start) * 1000
                results.append(TaskResult(
                    status=TaskStatus.COMPLETED,
                    value=value,
                    elapsed_ms=elapsed,
                    task_id=tid,
                ))
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                results.append(TaskResult(
                    status=TaskStatus.FAILED,
                    error=e,
                    elapsed_ms=elapsed,
                    task_id=tid,
                ))
        return results

    def wait_first(self, timeout: Optional[float] = None) -> TaskResult:
        """Wait for the first task to complete."""
        from concurrent.futures import wait, FIRST_COMPLETED
        done, pending = wait(self._futures, timeout=timeout, return_when=FIRST_COMPLETED)

        if not done:
            return TaskResult(status=TaskStatus.PENDING)

        future = done.pop()
        idx = self._futures.index(future)
        tid = self._task_ids[idx]

        try:
            value = future.result()
            return TaskResult(
                status=TaskStatus.COMPLETED,
                value=value,
                task_id=tid,
            )
        except Exception as e:
            return TaskResult(
                status=TaskStatus.FAILED,
                error=e,
                task_id=tid,
            )

    def cancel_all(self):
        """Cancel all pending tasks."""
        for future in self._futures:
            future.cancel()

    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False


# ─── Parallel Pipeline ────────────────────────────────────────────────

class ParallelPipeline:
    """
    Execute pipeline stages in parallel where possible.

    Supports:
    - Parallel map (split data across workers)
    - Pipeline parallelism (stages run concurrently on different data)
    - Ordered and unordered results
    """

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._stages: List[Callable] = []

    def map(self, fn: Callable) -> ParallelPipeline:
        """Add a map stage."""
        self._stages.append(("map", fn))
        return self

    def filter(self, fn: Callable) -> ParallelPipeline:
        """Add a filter stage."""
        self._stages.append(("filter", fn))
        return self

    def execute(self, data: List[Any], ordered: bool = True) -> List[Any]:
        """Execute the pipeline on input data."""
        result = data

        for stage_type, fn in self._stages:
            if stage_type == "map":
                if ordered:
                    futures = [self._executor.submit(fn, item) for item in result]
                    result = [f.result() for f in futures]
                else:
                    from concurrent.futures import as_completed
                    futures = {self._executor.submit(fn, item): i for i, item in enumerate(result)}
                    result = [f.result() for f in as_completed(futures)]

            elif stage_type == "filter":
                futures = [(item, self._executor.submit(fn, item)) for item in result]
                result = [item for item, f in futures if f.result()]

        return result

    def shutdown(self):
        self._executor.shutdown(wait=False)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.shutdown()


# ─── Rate Limiter ──────────────────────────────────────────────────────

class RateLimiter:
    """
    Token bucket rate limiter for controlling execution speed.
    Useful for API calls, I/O throttling, etc.
    """

    def __init__(self, rate: float, burst: int = 1):
        """
        Args:
            rate: Number of operations per second
            burst: Maximum burst size (bucket capacity)
        """
        self._rate = rate
        self._burst = burst
        self._tokens = float(burst)
        self._last_time = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a token. Blocks until available or timeout.
        Returns True if token acquired, False on timeout.
        """
        deadline = time.monotonic() + timeout if timeout else float("inf")

        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return True

            now = time.monotonic()
            if now >= deadline:
                return False

            # Wait for next token
            wait_time = min(1.0 / self._rate, deadline - now)
            if wait_time > 0:
                time.sleep(wait_time)

    def try_acquire(self) -> bool:
        """Non-blocking acquire. Returns True if token available."""
        with self._lock:
            self._refill()
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_time
        self._tokens = min(self._burst, self._tokens + elapsed * self._rate)
        self._last_time = now


# ─── Async Pipeline Executor ──────────────────────────────────────────

class AsyncPipelineExecutor:
    """
    Execute LATERALUS pipelines with async support.

    Transforms:
        data |> stage1 |> stage2 |> stage3

    Into concurrent execution where possible.
    """

    def __init__(self):
        self._stages: List[Callable] = []

    def add_stage(self, fn: Callable) -> AsyncPipelineExecutor:
        self._stages.append(fn)
        return self

    async def execute_async(self, data: Any) -> Any:
        """Execute pipeline stages sequentially but with async support."""
        result = data
        for stage in self._stages:
            if asyncio.iscoroutinefunction(stage):
                result = await stage(result)
            else:
                result = stage(result)
        return result

    def execute_sync(self, data: Any) -> Any:
        """Execute pipeline stages synchronously."""
        result = data
        for stage in self._stages:
            result = stage(result)
        return result


# ─── Convenience functions ─────────────────────────────────────────────

def parallel_map(fn: Callable, items: List[Any], workers: int = 4) -> List[Any]:
    """Map a function over items in parallel."""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(fn, items))


def parallel_filter(fn: Callable, items: List[Any], workers: int = 4) -> List[Any]:
    """Filter items in parallel."""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(lambda x: (x, fn(x)), items))
        return [item for item, keep in results if keep]


def run_with_timeout(fn: Callable, timeout: float, *args, **kwargs) -> TaskResult:
    """Run a function with a timeout."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn, *args, **kwargs)
        start = time.perf_counter()
        try:
            value = future.result(timeout=timeout)
            elapsed = (time.perf_counter() - start) * 1000
            return TaskResult(
                status=TaskStatus.COMPLETED,
                value=value,
                elapsed_ms=elapsed,
            )
        except TimeoutError:
            future.cancel()
            elapsed = (time.perf_counter() - start) * 1000
            return TaskResult(
                status=TaskStatus.CANCELLED,
                elapsed_ms=elapsed,
                error=TimeoutError(f"Execution exceeded {timeout}s"),
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return TaskResult(
                status=TaskStatus.FAILED,
                error=e,
                elapsed_ms=elapsed,
            )


# ─── Builtins registry ────────────────────────────────────────────────

ASYNC_BUILTINS = {
    "Channel": Channel,
    "TaskGroup": TaskGroup,
    "ParallelPipeline": ParallelPipeline,
    "RateLimiter": RateLimiter,
    "CancellationToken": None,   # placeholder, set below
    "Nursery": None,             # placeholder, set below
    "parallel_map": parallel_map,
    "parallel_filter": parallel_filter,
    "parallel_reduce": None,     # placeholder, set below
    "run_with_timeout": run_with_timeout,
    "select": None,              # placeholder, set below
}


# ─── Cancellation Token ───────────────────────────────────────────────

class CancellationToken:
    """
    A cooperative cancellation token.  Pass it to tasks so they can
    periodically check ``is_cancelled`` and bail out early.

    Usage::

        token = CancellationToken()
        group.spawn(work, cancel_token=token)
        token.cancel()          # signal all holders
        token.cancel("reason")  # optional reason string
    """

    def __init__(self):
        self._cancelled = False
        self._reason: Optional[str] = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable] = []

    def cancel(self, reason: Optional[str] = None):
        """Cancel the token and invoke all registered callbacks."""
        with self._lock:
            if self._cancelled:
                return
            self._cancelled = True
            self._reason = reason
            cbs = list(self._callbacks)
        for cb in cbs:
            try:
                cb(reason)
            except Exception:
                pass

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @property
    def reason(self) -> Optional[str]:
        return self._reason

    def on_cancel(self, callback: Callable):
        """Register a callback invoked when cancellation fires."""
        with self._lock:
            if self._cancelled:
                callback(self._reason)
            else:
                self._callbacks.append(callback)

    def check(self):
        """Raise ``CancelledError`` if the token has been cancelled."""
        if self._cancelled:
            raise CancelledError(self._reason or "task cancelled")


class CancelledError(Exception):
    """Raised when a cancellation token fires inside a task."""
    pass


# ─── Nursery (structured concurrency) ─────────────────────────────────

class Nursery:
    """
    Structured concurrency scope.  All tasks spawned inside the nursery
    must finish before the nursery exits.  If any child raises, the
    remaining siblings are cancelled and the first error is re-raised.

    Usage::

        with Nursery() as n:
            n.spawn(work_a)
            n.spawn(work_b)
        # both work_a and work_b are done (or failed) here
    """

    def __init__(self, max_workers: int = 8):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: List[Future] = []
        self._token = CancellationToken()
        self._results: List[TaskResult] = []

    @property
    def cancel_token(self) -> CancellationToken:
        return self._token

    def spawn(self, fn: Callable, *args, **kwargs) -> str:
        """Spawn a child task inside this nursery."""
        tid = f"nursery-{len(self._futures) + 1}"
        future = self._executor.submit(fn, *args, **kwargs)
        self._futures.append(future)
        return tid

    def _collect(self):
        """Wait for all futures and build result list."""
        first_error = None
        for i, future in enumerate(self._futures):
            tid = f"nursery-{i + 1}"
            try:
                value = future.result()
                self._results.append(TaskResult(
                    status=TaskStatus.COMPLETED, value=value, task_id=tid))
            except Exception as e:
                self._results.append(TaskResult(
                    status=TaskStatus.FAILED, error=e, task_id=tid))
                if first_error is None:
                    first_error = e
                    self._token.cancel(str(e))
        return first_error

    @property
    def results(self) -> List[TaskResult]:
        return list(self._results)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        err = self._collect()
        self._executor.shutdown(wait=True)
        if err is not None and exc_type is None:
            raise err
        return False


# ─── Select (channel multiplexing) ────────────────────────────────────

def select(*channels: Channel, timeout: Optional[float] = None) -> Optional[dict]:
    """
    Wait for the first channel that has data ready.

    Returns ``{"channel": ch, "index": i, "value": v}`` for the
    first ready channel, or ``None`` on timeout.

    Usage::

        result = select(ch1, ch2, timeout=1.0)
        if result:
            print(result["value"])
    """
    deadline = time.monotonic() + timeout if timeout else None
    while True:
        for i, ch in enumerate(channels):
            val = ch.try_recv()
            if val is not None:
                return {"channel": ch, "index": i, "value": val}
        if deadline and time.monotonic() >= deadline:
            return None
        time.sleep(0.001)   # avoid busy-spin


# ─── Parallel reduce ──────────────────────────────────────────────────

def parallel_reduce(fn: Callable, items: List[Any],
                    initial: Any = None, workers: int = 4) -> Any:
    """
    Reduce a list in parallel by splitting into chunks, reducing each
    chunk, and then reducing the partial results.
    """
    if not items:
        return initial

    chunk_size = max(1, len(items) // workers)
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

    def reduce_chunk(chunk):
        from functools import reduce as _reduce
        if initial is not None:
            return _reduce(fn, chunk, initial)
        return _reduce(fn, chunk)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        partials = list(executor.map(reduce_chunk, chunks))

    from functools import reduce as _reduce
    return _reduce(fn, partials)


# ─── Update builtins registry with concrete references ────────────────

ASYNC_BUILTINS["CancellationToken"] = CancellationToken
ASYNC_BUILTINS["Nursery"] = Nursery
ASYNC_BUILTINS["parallel_reduce"] = parallel_reduce
ASYNC_BUILTINS["select"] = select
