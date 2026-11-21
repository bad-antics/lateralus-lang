# Color Manipulation and Palettes with `stdlib.color`

The `stdlib.color` module provides utilities for packing, unpacking, blending, converting, and formatting colors in Lateralus. Colors are represented as packed 24-bit (`0xRRGGBB`) or 32-bit (`0xAARRGGBB`) integers, enabling high-performance integer manipulation alongside rich color transforms.

---

## 1. Creating and Packing Colors

Pack red, green, blue, and optional alpha channels into integer color representations:

```lateralus
import color

// Create packed 0xRRGGBB color
let orange = color.rgb(255, 140, 0)

// Create packed 0xAARRGGBB color with alpha channel
let semi_transparent_blue = color.rgba(0, 0, 255, 128)
```

Values passed to `rgb` and `rgba` are automatically clamped within the valid byte range `[0, 255]`.

---

## 2. Extracting Color Components

Extract individual channel intensities using fast bitwise component extractors:

```lateralus
let my_color = color.rgb(255, 128, 64)

let r = color.red(my_color)    // 255
let g = color.green(my_color)  // 128
let b = color.blue(my_color)   // 64

let transparent_red = color.rgba(255, 0, 0, 192)
let a = color.alpha(transparent_red) // 192
```

---

## 3. Hexadecimal Conversion

Format packed color integers into standard web hexadecimal color strings (`#RRGGBB`):

```lateralus
let c = color.rgb(255, 0, 128)
let hex_code = color.to_hex(c) // "#ff0080"
```

---

## 4. Color Manipulation and Blending

Transform and composite colors using blending functions:

| Function | Signature | Description |
| :--- | :--- | :--- |
| **`lighten(color, factor)`** | `(int, float) -> int` | Lightens a color towards white by factor `[0.0, 1.0]`. |
| **`darken(color, factor)`** | `(int, float) -> int` | Darkens a color towards black by factor `[0.0, 1.0]`. |
| **`mix(color_a, color_b, ratio)`** | `(int, int, float) -> int` | Linearly interpolates between two colors with `ratio` (`0.0` = `a`, `1.0` = `b`). |
| **`invert(color)`** | `(int) -> int` | Computes the RGB complement (`255 - channel`). |
| **`grayscale(color)`** | `(int) -> int` | Converts color to grayscale using standard luminance weights (`0.299 R + 0.587 G + 0.114 B`). |

### Example Blending:

```lateralus
let base_color = color.rgb(100, 150, 200)

let tint = color.lighten(base_color, 0.25)
let shade = color.darken(base_color, 0.3)
let blended = color.mix(color.RED, color.BLUE, 0.5) // Purple blend
let comp = color.invert(color.BLACK)                // WHITE
let gray = color.grayscale(color.rgb(255, 0, 0))
```

---

## 5. Builtin Palettes and Theme Constants

Standard primary, secondary, and terminal/UI theme colors are provided as module constants:

### Named Web Colors:
- `color.BLACK` (`0x000000`)
- `color.WHITE` (`0xFFFFFF`)
- `color.RED` (`0xFF0000`)
- `color.GREEN` (`0x00FF00`)
- `color.BLUE` (`0x0000FF`)
- `color.YELLOW`, `color.CYAN`, `color.MAGENTA`, `color.ORANGE`, `color.PURPLE`, `color.GRAY`, `color.SILVER`

### Lateralus Theme Colors:
- `color.LTL_BG` (`0x1E1E2E` - Mocha background)
- `color.LTL_FG` (`0xCDD6F4` - Foreground text)
- `color.LTL_ACCENT` (`0xCBA6F7` - Accent purple)
- `color.LTL_SUCCESS` (`0xA6E3A1` - Success green)
- `color.LTL_WARNING` (`0xF9E2AF` - Warning peach/yellow)
- `color.LTL_ERROR` (`0xF38BA8` - Error red)
- `color.LTL_INFO` (`0x89B4FA` - Info blue)
- `color.LTL_SURFACE` (`0x313244`)
- `color.LTL_OVERLAY` (`0x45475A`)
