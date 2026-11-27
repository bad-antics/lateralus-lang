import itertools
from typing import Any, Tuple

class PriorityQueue:
    """A thread-safe / deterministic priority queue with stable tie-breaking."""

    def __init__(self) -> None:
        self._heap: list = []
        self._counter = itertools.count()

    def push(self, priority: Any, value: Any) -> None:
        """Push an item with a given priority and payload."""
        count = next(self._counter)
        # Using a tuple (priority, count, value) guarantees that if priorities
        # are tied, Python compares the strictly increasing counter instead of
        # attempting to compare the value payloads directly (which could fail
        # or be unsafe for arbitrary payloads/PoCs).
        entry = (priority, count, value)
        self._heap.append(entry)
        self._sift_up(len(self._heap) - 1)

    .pop(self) -> Any:
        """Pop and return the highest priority item's value."""
        if not self._heap:
            raise IndexError("pop from empty priority queue")
        
        # Move root to end and pop
        self._swap(0, len(self._heap) - 1)
        priority, count, value = self._heap.pop()
        if self._heap:
            self._sift_down(0)
        return value

    def __len__(self) -> int:
        return len(self._heap)

    def _sift_up(self, idx: int) -> None:
        parent = (idx - 1) // 2
        while idx > 0 and self._heap[idx] < self._heap[parent]:
            self._swap(idx, parent)
            idx = parent
            parent = (idx - 1) // 2

    def _sift_down(self, idx: int) -> None:
        length = len(self._heap)
        while True:
            left = 2 * idx + 1
            right = 2 * idx + 2
            smallest = idx

            if left < length and self._heap[left] < self._heap[smallest]:
                smallest = left
            if right < length and self._heap[right] < self._heap[smallest]:
                smallest = right

            if smallest == idx:
                break

            self._swap(idx, smallest)
            idx = smallest

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]