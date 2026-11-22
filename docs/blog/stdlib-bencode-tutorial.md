---
title: "BitTorrent Bencode Serialization: Deterministic Dictionary Ordering & Wire Framing in Lateralus"
description: "A deep-dive tutorial on stdlib/bencode.ltl — implementing BEP-0003 Bencode integer, byte-string, list, and canonical dictionary serialization in Lateralus for deterministic cryptographic info-hash verification."
date: "2026-11-22"
author: "Lateralus Standard Library Team"
tags: ["bencode", "serialization", "bittorrent", "parsing", "standard-library"]
---

# BitTorrent Bencode Serialization: Deterministic Dictionary Ordering & Wire Framing in Lateralus

In peer-to-peer content distribution (BitTorrent BEP-0003) and content-addressed replication protocols, wire serialization must be **bijective**: every logical data structure must map to exactly one canonical byte sequence so that its cryptographic digest (`info_hash`) is invariant across implementations.

The **`stdlib/bencode.ltl`** module implements deterministic encoding and state-machine decoding for the four Bencode primitives: integers, length-prefixed byte strings, lists, and lexicographically sorted dictionaries.

---

## 1. BEP-0003 Wire Format Grammar

Bencode defines four self-delimiting production rules:

1. **Integers (`i<digits>e`)**: Base-10 ASCII representation enclosed between `i` and `e` (e.g., `i42e`, `i-7e`, `i0e`). Leading zeros (`i04e`) and negative zero (`i-0e`) are invalid.
2. **Byte Strings (`<length>:<bytes>`)**: Decimal byte length followed by `:` and the exact payload (e.g., `7:torrent`).
3. **Lists (`l<items>e`)**: Ordered sequence of bencoded elements enclosed between `l` and `e` (e.g., `l4:spami42ee`).
4. **Canonical Dictionaries (`d<pairs>e`)**: Key-value pairs where keys are byte strings ordered strictly in **lexicographical byte order**.

---

## 2. Deterministic Encoding & Parsing Implementation

Below is the runnable implementation from `examples/bencode_tutorial.ltl`:

```ltl
pub fn bencode_int(val) {
    return "i" + str(val) + "e"
}

pub fn bencode_str(s) {
    return str(len(s)) + ":" + s
}

pub fn bencode_list_ints(arr, n) {
    let out = "l"
    let i = 0
    while i < n {
        out = out + bencode_int(arr[i])
        i = i + 1
    }
    return out + "e"
}
```

---

## 3. Pinned Test Vectors (BEP-0003 Conformance)

| Logical Value | Canonical Bencode Wire String | Byte Length |
| :--- | :--- | :--- |
| `0` | `i0e` | 3 |
| `1048576` (1 MiB piece length) | `i1048576e` | 9 |
| `-42` | `i-42e` | 5 |
| `"lateralus"` | `9:lateralus` | 11 |
| `[10, 20, 30]` | `li10ei20ei30ee` | 14 |
| `{"announce": "udp://tracker.local:6969", "pieces": 16}` | `d8:announce24:udp://tracker.local:69696:piecesi16ee` | 51 |
