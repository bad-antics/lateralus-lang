from lateralus_lang.data import pq_new, pq_push, pq_pop, pq_peek


def test_tied_priorities_allow_unorderable_payloads():
    q = pq_new()
    pq_push(q, "first job", 1)
    pq_push(q, 42, 1)
    assert pq_pop(q)["value"] == "first job"
    assert pq_pop(q)["value"] == 42


def test_tied_priorities_keep_insertion_order():
    q = pq_new()
    for index, priority in enumerate([2, 0, 1, 1]):
        pq_push(q, {"job": index}, priority)
    order = [pq_pop(q)["value"]["job"] for _ in range(4)]
    assert order == [1, 2, 3, 0]


def test_peek_does_not_remove_payload():
    q = pq_new()
    pq_push(q, {"job": "a"}, 1)
    pq_push(q, {"job": "b"}, 1)
    assert pq_peek(q) == {"job": "a"}
    assert q["size"] == 2
