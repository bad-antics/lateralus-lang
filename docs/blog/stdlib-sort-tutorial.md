# Sorting Algorithms in Practice with `stdlib/sort.ltl`

Sorting is the most-studied problem in computer science — and the algorithm
you pick decides whether your pipeline finishes in milliseconds or hours.
Lateralus ships `stdlib/sort.ltl`, a batteries-included sorting toolkit that
gives you five comparison sorts plus the utilities you actually reach for in
production code: order checks, order statistics, and binary search.

In this tutorial we tour every public function in the module, work through
the complexity trade-offs, and run a self-contained companion script
(`examples/sort_tutorial.ltl`) that exercises each algorithm on the same
input so you can compare outputs side by side.

---

## The API surface

| Function | What it does | Average | Worst |
|---|---|---|---|
| `sorted(items)` | ascending sort (quicksort) | O(n log n) | O(n²) |
| `sorted_desc(items)` | descending sort | O(n log n) | O(n²) |
| `sort_by_key(items, fn)` | decorate-sort-undecorate | O(n log n) | O(n²) |
| `is_sorted(items)` | ascending-order check | O(n) | O(n) |
| `quicksort(items)` | three-way partition quicksort | O(n log n) | O(n²) |
| `mergesort(items)` | stable merge sort | O(n log n) | O(n log n) |
| `insertion_sort(items)` | incremental insertion | O(n²) | O(n²) |
| `selection_sort(items)` | repeated minimum extraction | O(n²) | O(n²) |
| `nsmallest(items, n)` / `nlargest(items, n)` | order statistics | O(n log n) | O(n log n) |
| `binary_search(items, target)` | index in a sorted list | O(log n) | O(log n) |
| `count_inversions(items)` | "sortedness" metric | O(n²) | O(n²) |

`sorted()` is the entry point most code should use; the named algorithms are
there for when you need stability (`mergesort`), guaranteed O(n log n)
(`mergesort` again — quicksort degrades on adversarial input), or minimal
swaps (`selection_sort`).

---

## Quicksort: three-way partition

`stdlib/sort.ltl` implements the classic Lomuto-style quicksort with a
three-way partition, which is what makes it gracefully handle lists with
many duplicate keys:

```text
pivot = items[len(items) / 2]
lo   = items |> filter(fn(x) { x <  pivot })
mid  = items |> filter(fn(x) { x == pivot })
hi   = items |> filter(fn(x) { x >  pivot })
return quicksort(lo) + mid + quicksort(hi)
```

Every element equal to the pivot lands in `mid` in a single pass, so a list of
all-identical elements costs O(n) per level instead of O(n²). The middle
pivot also avoids the classic sorted-input pathology of first/last-element
pivot selection.

Cost model: average O(n log n) time and O(log n) stack depth; worst case
O(n²) time and O(n) stack on adversarial pivot choices — which is why the
module also ships mergesort.

## Mergesort: the stable guarantee

`mergesort` splits the list in half, sorts each half recursively, and merges
the two sorted runs. The merge step only advances the left pointer on ties
(`a[i] <= b[j]`), which makes mergesort **stable**: equal elements keep their
original relative order. That property matters when sorting records by a key
where the secondary order carries meaning (e.g. transactions by timestamp,
then by insertion order).

Unlike quicksort, mergesort is O(n log n) in the worst case — there is no bad
input — at the price of O(n) auxiliary space for the merge output.

## Insertion and selection sort: when O(n²) is fine

`insertion_sort` shines on **small or nearly-sorted** inputs: each element is
bubbled left past larger predecessors, so a sorted list costs O(n). The
stdlib version uses the textbook shift-in-place formulation.

`selection_sort` finds the minimum of the unsorted suffix each pass. It is
the right choice when **writes are expensive** — it performs at most n−1
swaps regardless of input — but it always costs O(n²) comparisons.

## The utilities that earn their keep

### `is_sorted`

One linear pass comparing neighbours. Run it before `binary_search` —
binary search on an unsorted list returns confidently wrong answers.

### `binary_search`

Classic halving search returning the index or `-1`. It requires a sorted
list; combine with `is_sorted` when the input's provenance is uncertain.

### `count_inversions`

Counts pairs `(i, j)` with `i < j` and `items[i] > items[j]` — a direct
measure of how far a list is from sorted. An inversion count of 0 means
sorted; `n·(n−1)/2` means reverse-sorted. It's O(n²) here; for large lists a
merge-sort-based counter gives O(n log n), which is a nice exercise.

### `nsmallest` / `nlargest`

Order statistics without materialising a full sort of the whole space:
they sort once and slice. For "top-k of a huge stream" you'd want a heap —
`stdlib/heap.ltl` covers that — but for lists already in memory this is the
simple correct answer.

### `sort_by_key`

The Schwartzian transform: decorate each element with its key, sort the
`[key, element]` pairs, then undecorate. Each key is computed exactly once —
important when the key function is expensive (parsing, hashing, I/O).

---

## Running the companion script

`examples/sort_tutorial.ltl` re-implements the same algorithms
self-contained (so it runs under `lateralus run` without stdlib import
resolution) and prints pinned, deterministic output:

```bash
$ lateralus run examples/sort_tutorial.ltl
=== LATERALUS STDLIB SORT TUTORIAL ===
INPUT: [5, 2, 9, 1, 7, 3, 8, 4, 6, 0]
STEP 1: is_sorted(input) = false
STEP 2: quicksort: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
STEP 3: mergesort: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
STEP 4: insertion_sort: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
STEP 5: selection_sort: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
STEP 6: is_sorted(quicksort) = true
STEP 7: count_inversions(input) = 25
STEP 8: binary_search(quicksort, 7) = 7
STEP 8b: binary_search(quicksort, 42) = -1
STEP 9: nsmallest(input, 3): [0, 1, 2]
STEP 10: nlargest(input, 3): [7, 8, 9]
STEP 11: words by length: [fig, pear, kiwi, plum, banana]
PINNED_VECTORS: sorted=[0,1,2,3,4,5,6,7,8,9] inversions=25 binsearch_7=7 binsearch_42=-1
```

Every algorithm agrees on the sorted output — as it must — while
`count_inversions` quantifies the input's disorder (25 inversions out of a
maximum of 45 pairs) and `binary_search` finds `7` at index 7 while
correctly reporting `-1` for the absent `42`.

`tests/test_sort_tutorial.py` pins all of these vectors in CI, so any
regression in the tutorial script — or a change in list-printing or
arithmetic semantics — fails loudly.

## Which sort should you reach for?

- **Default**: `sorted(items)` — fast, concise, handles duplicates well.
- **Need stability or worst-case guarantees**: `mergesort(items)`.
- **Nearly-sorted or tiny inputs**: `insertion_sort(items)`.
- **Expensive writes / embedded targets**: `selection_sort(items)`.
- **Just need top-k or membership**: `nsmallest`, `nlargest`,
  `binary_search` — don't sort what you don't have to.

That is the whole `stdlib/sort.ltl` surface: five sorts, five utilities,
and one rule of thumb — start with `sorted()`, and reach for the named
algorithm only when you can name the property you need.
