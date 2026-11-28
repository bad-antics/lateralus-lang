# Terrain grid survey

The Python reference and Lateralus port survey the same synthetic elevation grid using constant working memory. They report minimum and maximum elevation in meters, mean elevation in millimeters, the count of cells at or above 800 m, and the mean absolute elevation change between adjacent cells along each axis. Each shared edge is counted once. The integer means round down.

The 8×8 fixture checks the boundary cells and both directions. The 1536×1536 fixture exercises the same calculation over 2,359,296 cells, including the full ridge cycles and basin steps. Both executables produced the following output byte for byte. A separate reference calculation using adjacent rows and columns reproduced all reported values.

```text
8x8 min_m=400 max_m=746 mean_mm=597625 high_cells=0 east_step_mm=28714 south_step_mm=23714
1536x1536 min_m=316 max_m=952 mean_mm=630824 high_cells=282089 east_step_mm=26321 south_step_mm=18907
```

## Build and run

Run these commands from this directory in an x64 Visual Studio Developer PowerShell with CPython available as `python`. The v3.2.1 release carries the v3.2.0 Python toolchain. The C backend emits C source, which MSVC builds into a native executable. [Official release assets](https://github.com/bad-antics/lateralus-lang/releases/expanded_assets/v3.2.1)

```powershell
$wheel = 'lateralus_lang-3.2.0-py3-none-any.whl'
$release = 'https://github.com/bad-antics/lateralus-lang/releases/download/v3.2.1'
Invoke-WebRequest "$release/$wheel" -OutFile $wheel
if ((Get-FileHash $wheel -Algorithm SHA256).Hash -ne '202cb5ef2672d5bb721dc0ebbd8be3f7c8b996e79874fb0ddd5c7a0a5acff94c') {
    throw 'Unexpected Lateralus wheel checksum'
}
python -m zipfile -e $wheel .lateralus-toolchain
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = (Resolve-Path .lateralus-toolchain).Path
python -m lateralus_lang --version
python -X utf8 -m lateralus_lang check terrain_grid.ltl
python -m lateralus_lang c terrain_grid.ltl -o terrain_grid.c
$env:PYTHONPATH = $previousPythonPath
cl /nologo /utf-8 /O2 /std:c11 terrain_grid.c /Feterrain_grid.exe
python benchmark.py
```

The Lateralus port prints the labels and integers separately to work with the v3.2.0 C backend. Keep the generated C and build artifacts local.

## Measured wall time

Windows 11 x64 build 26300, Intel Core Ultra 9 285H, CPython 3.12.14, Lateralus 3.2.0, and MSVC 19.51.36260 x64.

The benchmark discards one warm-up per implementation and measures 11 pairs, swapping which process runs first after every pair. Each measurement includes process startup, both grids, output capture, and process exit. Compilation is outside the timed runs. The runner checks both expected output lines after every process exits.

| Pair | CPython (ms) | Lateralus native (ms) |
| --- | ---: | ---: |
| 1 | 927.525 | 21.466 |
| 2 | 980.772 | 21.514 |
| 3 | 878.596 | 21.429 |
| 4 | 906.526 | 21.217 |
| 5 | 905.402 | 32.320 |
| 6 | 978.094 | 25.697 |
| 7 | 906.807 | 31.666 |
| 8 | 918.642 | 23.262 |
| 9 | 918.616 | 23.971 |
| 10 | 916.762 | 22.060 |
| 11 | 966.885 | 23.259 |
| **Median** | **918.616** | **23.259** |

The CPython median was about **39.5×** the native median on this workload and machine.

The reference, port, and benchmark are original contributions under the repository's MIT license. [Bounty reservation issue](https://github.com/bad-antics/lateralus-lang/issues/1148)
