---
title: "Deterministic Finite State Machines: Guarded Transition Tables & Protocol Automata in Lateralus"
description: "A deep-dive tutorial on stdlib/fsm.ltl — modeling formal deterministic finite automata (DFA) and guarded protocol state machines in Lateralus with transition table verification."
date: "2026-11-22"
author: "Lateralus Standard Library Team"
tags: ["fsm", "automata", "state-machine", "protocols", "standard-library"]
---

# Deterministic Finite State Machines: Guarded Transition Tables & Protocol Automata in Lateralus

Network protocols (TCP connection lifecycle), payment escrow workflows, and lexical analyzers rely on **Deterministic Finite State Machines (FSM)** to guarantee that invalid state transitions are structurally impossible.

The **`stdlib/fsm.ltl`** module provides a formal transition-table engine where a state machine is defined as a 5-tuple $(Q, \Sigma, \delta, q_0, F)$ augmented with boolean transition guards.

---

## 1. Formal Definition & Guarded Transition Function

A deterministic guarded finite automaton consists of:
- $Q$: Finite set of integer state identifiers $\{0, 1, \dots, |Q|-1\}$.
- $\Sigma$: Finite alphabet of event codes.
- $\delta: Q \times \Sigma \times \text{Guard} \to Q$: Transition relation mapping `(from_state, event, guard_ok)` to `to_state`.
- $q_0 \in Q$: Initial state.
- $F \subseteq Q$: Set of accepting/terminal states.

When an event $e \in \Sigma$ arrives in state $q \in Q$, the machine scans its transition table for a rule $(q_{\text{from}}, e_{\text{code}}, q_{\text{to}}, g)$ satisfying $q_{\text{from}} = q \land e_{\text{code}} = e \land g = \text{true}$. If found, the state advances to $q_{\text{to}}$; otherwise the automaton remains in $q$ (or transitions to an explicit reject state).

---

## 2. Runnable Lateralus Implementation

From `examples/fsm_tutorial.ltl` (Escrow Payment Settlement Lifecycle):

```ltl
pub fn add_transition(table, idx, from_st, ev_code, to_st, guard_ok) {
    let tr = dict()
    tr["from"] = from_st
    tr["event"] = ev_code
    tr["to"] = to_st
    tr["guard"] = guard_ok
    table[idx] = tr
    return idx + 1
}

pub fn dispatch_event(table, num_rules, cur_state, ev_code) {
    let i = 0
    while i < num_rules {
        let tr = table[i]
        if (tr["from"] == cur_state) && (tr["event"] == ev_code) && (tr["guard"] == 1) {
            return tr["to"]
        }
        i = i + 1
    }
    return cur_state
}
```

---

## 3. Pinned Verification Vectors

| Current State | Event Dispatched | Guard Condition | Resulting State |
| :--- | :--- | :--- | :--- |
| `0 (CREATED)` | `10 (FUND_ESCROW)` | `1 (Valid Deposit)` | `1 (FUNDED)` |
| `1 (FUNDED)` | `20 (DELIVER_WORK)` | `1 (CI Green)` | `2 (UNDER_REVIEW)` |
| `2 (UNDER_REVIEW)` | `30 (APPROVE_RELEASE)` | `1 (Maintainer Signed)` | `3 (RELEASED)` |
| `1 (FUNDED)` | `30 (APPROVE_RELEASE)` | `1` (Illegal Skip) | `1 (FUNDED)` (Blocked) |
