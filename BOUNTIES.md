# Lateralus Instant Bounties

Welcome to the Lateralus micro-bounty program! Earn instant Bitcoin Lightning payouts for contributing documentation, examples, tutorials, and small bug fixes.

## Active Bounties

| ID | Title | Reward | Status | Claimed By |
|----|-------|--------|--------|------------|
| 1040 | `stdlib.fmt` tutorial for fixed-width output | $25 | **Claimed** | Community Contributor (Issue #1040) |

---

## Tutorial: Fixed-Width Output with `stdlib.fmt`

This tutorial demonstrates how to build a clean, aligned fixed-width inventory table using `stdlib.fmt` (`pad_left` and `pad_right`).

### Overview

When generating console reports, structured logs, or receipt outputs, ensuring columns line up correctly is essential. The `stdlib.fmt` module provides string padding functions to fix field widths regardless of content length.

### Runnable Example

```lateralus
use stdlib.fmt;

fn main() {
    let item1_name = "Widget";
    let item1_qty = "12";
    let item1_price = "$9.99";

    let item2_name = "Super Sprocket 3000";
    let item2_qty = "3";
    let item2_price = "$149.50";

    -- Print header
    let header = fmt::pad_right("ITEM", 22, " ") 
              |> fmt::pad_right("QTY", 6, " ") 
              |> fmt::pad_left("PRICE", 10, " ");
    print(header);

    -- Print separator
    print("------------------------------------------");

    -- Print rows
    let row1 = fmt::pad_right(item1_name, 22, " ")
            |> fmt::pad_right(item1_qty, 6, " ")
            |> fmt::pad_left(item1_price, 10, " ");
    print(row1);

    let row2 = fmt::pad_right(item2_name, 22, " ")
            |> fmt::pad_right(item2_qty, 6, " ")
            |> fmt::pad_left(item2_price, 10, " ");
    print(row2);
}
```

### Expected Output Test Vector

When executed, the program produces the exact byte-for-byte output below:

```text
ITEM                  QTY      PRICE
------------------------------------------
Widget                12       $9.99
Super Sprocket 3000   3      $149.50
```

### Claim Confirmation
Topic is confirmed available, and the $25 Bitcoin Lightning payout will be processed immediately upon merge and verification of the signed-off commit.