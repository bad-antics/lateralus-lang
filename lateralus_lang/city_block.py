"""
lateralus_lang.city_block
==========================

Provides a two‑pass Manhattan (city‑block) distance transform implementation.

The function operates on a rectangular bitmap represented as a list of
lists of integers where ``0`` denotes a source (foreground) pixel and any
non‑zero value denotes background.  The returned matrix contains the
Manhattan distance from each cell to the nearest source cell.

The algorithm runs in O(rows × cols) time and O(1) additional space
besides the output matrix.
"""

from __future__ import annotations

from typing import List


def city_block_distance_transform(bitmap: List[List[int]]) -> List[List[int]]:
    """
    Compute the city‑block (Manhattan) distance transform of a binary bitmap.

    Parameters
    ----------
    bitmap :
        A rectangular 2‑D list where ``0`` marks source cells.  Any non‑zero
        value is treated as background.

    Returns
    -------
    List[List[int]]
        A matrix of the same dimensions where each entry is the Manhattan
        distance to the nearest source cell.

    Example
    -------
    >>> bitmap = [
    ...     [0, 1, 1],
    ...     [1, 1, 1],
    ...     [1, 1, 0],
    ... ]
    >>> city_block_distance_transform(bitmap)
    [[0, 1, 2], [1, 1, 1], [2, 1, 0]]
    """
    if not bitmap or not bitmap[0]:
        return []

    rows = len(bitmap)
    cols = len(bitmap[0])

    # Initialize distance matrix: 0 for sources, large value for background
    INF = rows + cols  # Maximum possible Manhattan distance in this grid
    dist = [[0 if bitmap[r][c] == 0 else INF for c in range(cols)] for r in range(rows)]

    # Forward pass: top-left to bottom-right
    for r in range(rows):
        for c in range(cols):
            if dist[r][c] != 0:
                # Check top neighbor
                if r > 0:
                    dist[r][c] = min(dist[r][c], dist[r - 1][c] + 1)
                # Check left neighbor
                if c > 0:
                    dist[r][c] = min(dist[r][c], dist[r][c - 1] + 1)

    # Reverse pass: bottom-right to top-left
    for r in range(rows - 1, -1, -1):
        for c in range(cols - 1, -1, -1):
            if dist[r][c] != 0:
                # Check bottom neighbor
                if r < rows - 1:
                    dist[r][c] = min(dist[r][c], dist[r + 1][c] + 1)
                # Check right neighbor
                if c < cols - 1:
                    dist[r][c] = min(dist[r][c], dist[r][c + 1] + 1)

    return dist


if __name__ == "__main__":
    # Simple sanity check
    bitmap = [
        [0, 1, 1],
        [1, 1, 1],
        [1, 1, 0],
    ]
    result = city_block_distance_transform(bitmap)
    for row in result:
        print(row)
