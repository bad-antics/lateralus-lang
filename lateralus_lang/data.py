"""
LATERALUS Standard Library — data
Python implementation of stdlib/data.ltl
Data structures and containers.
"""
from __future__ import annotations

# --- Stack ------------------------------------------------------------

def stack_new() -> dict:
    return {"items": [], "size": 0}


def stack_push(s: dict, value) -> dict:
    s["items"] = s["items"] + [value]
    s["size"] += 1
    return s


def stack_pop(s: dict) -> dict:
    if s["size"] == 0:
        raise RuntimeError("Stack underflow")
    value = s["items"][s["size"] - 1]
    s["items"] = s["items"][:s["size"] - 1]
    s["size"] -= 1
    return {"stack": s, "value": value}


def stack_peek(s: dict):
    if s["size"] == 0:
        raise RuntimeError("Stack is empty")
    return s["items"][s["size"] - 1]


def stack_is_empty(s: dict) -> bool:
    return s["size"] == 0


# --- Queue ------------------------------------------------------------

def queue_new() -> dict:
    return {"items": [], "size": 0}


def queue_enqueue(q: dict, value) -> dict:
    q["items"] = q["items"] + [value]
    q["size"] += 1
    return q


def queue_dequeue(q: dict) -> dict:
    if q["size"] == 0:
        raise RuntimeError("Queue underflow")
    value = q["items"][0]
    q["items"] = q["items"][1:]
    q["size"] -= 1
    return {"queue": q, "value": value}


def queue_peek(q: dict):
    if q["size"] == 0:
        raise RuntimeError("Queue is empty")
    return q["items"][0]


def queue_is_empty(q: dict) -> bool:
    return q["size"] == 0


# --- Set (map-based) -------------------------------------------------

def set_new() -> dict:
    return {}


def set_add(s: dict, value) -> dict:
    s[str(value)] = value
    return s


def set_has(s: dict, value) -> bool:
    return str(value) in s


def set_remove(s: dict, value) -> dict:
    s.pop(str(value), None)
    return s


def set_to_list(s: dict) -> list:
    return list(s.values())


def set_union(a: dict, b: dict) -> dict:
    result = dict(a)
    result.update(b)
    return result


def set_intersection(a: dict, b: dict) -> dict:
    return {k: v for k, v in a.items() if k in b}


# --- Priority Queue (min-heap) ---------------------------------------

def pq_new() -> dict:
    return {"items": [], "size": 0}


def pq_push(pq: dict, value, priority: float) -> dict:
    import heapq
    items = list(pq["items"])
    heapq.heappush(items, (priority, value))
    pq["items"] = items
    pq["size"] += 1
    return pq


def pq_pop(pq: dict) -> dict:
    import heapq
    if pq["size"] == 0:
        raise RuntimeError("Priority queue is empty")
    items = list(pq["items"])
    priority, value = heapq.heappop(items)
    pq["items"] = items
    pq["size"] -= 1
    return {"pq": pq, "value": value, "priority": priority}


def pq_peek(pq: dict):
    if pq["size"] == 0:
        raise RuntimeError("Priority queue is empty")
    return pq["items"][0][1]


def pq_is_empty(pq: dict) -> bool:
    return pq["size"] == 0


__all__ = [
    'stack_new', 'stack_push', 'stack_pop', 'stack_peek', 'stack_is_empty',
    'queue_new', 'queue_enqueue', 'queue_dequeue', 'queue_peek', 'queue_is_empty',
    'set_new', 'set_add', 'set_has', 'set_remove', 'set_to_list',
    'set_union', 'set_intersection',
    'pq_new', 'pq_push', 'pq_pop', 'pq_peek', 'pq_is_empty',
]
