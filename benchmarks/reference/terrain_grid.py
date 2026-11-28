"""Synthetic terrain-grid survey used by the native-port benchmark."""
import sys


GRIDS = (
    ((1, 2, 4, 3), (2, 3, 5, 4), (0, 1, 2, 2), (1, 2, 3, 1)),
    ((7, 6, 4), (6, 5, 3), (4, 3, 2), (2, 1, 0), (1, 2, 1)),
)

def survey(grid):
    rows = len(grid)
    cols = len(grid[0])
    height = sum(sum(row) for row in grid)
    roughness = 0
    for y in range(rows):
        for x in range(cols):
            if x + 1 < cols:
                roughness += abs(grid[y][x] - grid[y][x + 1])
            if y + 1 < rows:
                roughness += abs(grid[y][x] - grid[y + 1][x])
    return height, roughness


if __name__ == "__main__":
    for grid in GRIDS:
        height, roughness = survey(grid)
        print(height)
        print(roughness)
