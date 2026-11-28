"""Survey synthetic raster heights without storing the whole grid."""


def height_at(row: int, column: int) -> int:
    """Superimpose two ridges and a stepped basin, in whole meters."""
    ridge = (3 * column + row) % 97
    if ridge > 48:
        ridge = 96 - ridge
    fold = (column + 5 * row) % 61
    if fold > 30:
        fold = 60 - fold
    basin = (row // 11 + column // 17) % 29
    return 400 + 9 * ridge + 4 * fold - 3 * basin


def survey(side: int) -> None:
    minimum = maximum = height_at(0, 0)
    height_total = high_cells = 0
    horizontal_change = vertical_change = 0

    for row in range(side):
        left = height_at(row, 0)
        for column in range(side):
            height = height_at(row, column)
            if height < minimum:
                minimum = height
            if height > maximum:
                maximum = height
            if height >= 800:
                high_cells += 1
            height_total += height

            # Count each shared edge once, from its right or bottom cell.
            if column > 0:
                horizontal_change += abs(height - left)
            if row > 0:
                vertical_change += abs(height - height_at(row - 1, column))
            left = height

    edges_per_direction = side * (side - 1)
    mean_mm = height_total * 1000 // (side * side)
    east_step_mm = horizontal_change * 1000 // edges_per_direction
    south_step_mm = vertical_change * 1000 // edges_per_direction
    print(
        f"{side}x{side} min_m={minimum} max_m={maximum} "
        f"mean_mm={mean_mm} high_cells={high_cells} "
        f"east_step_mm={east_step_mm} south_step_mm={south_step_mm}"
    )


if __name__ == "__main__":
    survey(8)
    survey(1536)
