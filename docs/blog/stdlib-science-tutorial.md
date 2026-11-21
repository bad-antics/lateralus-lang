# Scientific Computing with `stdlib/science.ltl`

Physics and astronomy code is mostly unit conversion and closed-form
relations. `stdlib/science.ltl` bundles the SI constants plus the
formulas that use them: temperature/distance/energy conversions,
EM wave relations, quantum energies, orbital mechanics, ideal gas,
entropy, and Wien's black-body peak.

This tutorial exercises every function family. Companion:
`examples/science_tutorial.ltl`.

---

## Coverage

- **Units:** °C↔°F↔K, m↔ft, km↔mi, ly↔m, pc→ly
- **Energy:** J↔eV, E=mc², ½mv², mgh
- **EM/quantum:** λ↔f at c, E=hf, de Broglie λ=h/(mv)
- **Orbital:** v=√(GM/r), escape=√(2GM/r), T=2π√(a³/GM)
- **Thermo:** PV=nRT, ΔS=Q/T, Wien λ_max=b/T

## Verified against known values

- Earth orbital velocity ≈ 7909.7 m/s (accepted ~7906)
- Earth escape velocity ≈ 11186.0 m/s (accepted ~11186)
- Low-Earth-orbit period ≈ 5545 s (~92.4 min)
- Ideal gas at STP ≈ 101388 Pa (~1 atm)
- Sun black-body peak ≈ 501.5 nm (visible green-yellow)

Module ran cleanly — no source changes needed.

## Running the tutorial

```bash
python -m lateralus_lang run examples/science_tutorial.ltl
python -m lateralus_lang check examples/science_tutorial.ltl
python -m pytest tests/test_science_tutorial.py -x -q
```
