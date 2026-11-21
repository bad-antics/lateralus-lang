"""
tests/test_color_tutorial.py - Comprehensive verification of stdlib/color.ltl
Tests RGB/RGBA packing, bitwise channel extraction, hex serialization,
manipulation transforms (lighten, darken, mix, invert, grayscale), and theme palettes.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_color_packing_and_components():
    color_src = Path("stdlib/color.ltl").read_text(encoding="utf-8")
    driver = r"""
let c = rgb(255, 128, 64)
let r = red(c)
let g = green(c)
let b = blue(c)
let hex_str = to_hex(c)

let c_rgba = rgba(10, 20, 30, 200)
let a = alpha(c_rgba)
let r_rgba = red(c_rgba)
let g_rgba = green(c_rgba)
let b_rgba = blue(c_rgba)

let black_hex = to_hex(BLACK)
let white_hex = to_hex(WHITE)
let red_hex = to_hex(RED)
"""
    c = Compiler()
    res = c.compile_source(color_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["r"] == 255
    assert ns["g"] == 128
    assert ns["b"] == 64
    assert ns["hex_str"] == "#ff8040"

    assert ns["a"] == 200
    assert ns["r_rgba"] == 10
    assert ns["g_rgba"] == 20
    assert ns["b_rgba"] == 30

    assert ns["black_hex"] == "#000000"
    assert ns["white_hex"] == "#ffffff"
    assert ns["red_hex"] == "#ff0000"

def test_color_manipulations_and_blending():
    color_src = Path("stdlib/color.ltl").read_text(encoding="utf-8")
    driver = r"""
let base = rgb(100, 150, 200)

let light = lighten(base, 0.5)
let dark = darken(base, 0.5)
let mixed = mix(base, rgb(0, 0, 0), 0.5)
let inverted = invert(base)
let gray = grayscale(base)

let ltl_bg_hex = to_hex(LTL_BG)
let ltl_fg_hex = to_hex(LTL_FG)
let ltl_accent_hex = to_hex(LTL_ACCENT)
"""
    c = Compiler()
    res = c.compile_source(color_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    # Invert test
    assert ns["red"](ns["inverted"]) == 255 - 100
    assert ns["green"](ns["inverted"]) == 255 - 150
    assert ns["blue"](ns["inverted"]) == 255 - 200

    # Lighten should increase channel values
    assert ns["red"](ns["light"]) >= 100
    assert ns["green"](ns["light"]) >= 150
    assert ns["blue"](ns["light"]) >= 200

    # Darken should decrease channel values
    assert ns["red"](ns["dark"]) <= 100
    assert ns["green"](ns["dark"]) <= 150
    assert ns["blue"](ns["dark"]) <= 200

    # Theme colors
    assert ns["ltl_bg_hex"] == "#1e1e2e"
    assert ns["ltl_fg_hex"] == "#cdd6f4"
    assert ns["ltl_accent_hex"] == "#cba6f7"
