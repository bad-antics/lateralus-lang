"""Run the real heap module and a pinned Lateralus example without installation."""
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "1\n[1, 4, 7, 9]\n[-3, -3, 0, 2]\n[None, []]\n"

def main():
    with tempfile.TemporaryDirectory(prefix="lateralus-heap-") as tmp:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join([tmp, str(ROOT)])
        generated = Path(tmp) / "heap.py"
        subprocess.run([sys.executable, "-m", "lateralus_lang", "py",
                        str(ROOT / "stdlib/heap.ltl"), "-o", str(generated)],
                       cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        result = subprocess.run([sys.executable, "-m", "lateralus_lang", "run",
                                 str(ROOT / "examples/heap_priority_queue.ltl")],
                                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
        if result.returncode or result.stdout != EXPECTED:
            raise AssertionError(f"Example failed: {result.stdout!r} {result.stderr!r}")
        sys.path.insert(0, str(ROOT))
        spec = importlib.util.spec_from_file_location("verified_heap", generated)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rng = random.Random(17011)
        cases = [[], [0], [5, 1], [-5, -5, 0, 4], [9, 1, 4, 1, 7]]
        cases += [[rng.randint(-10000, 10000) for _ in range(rng.randrange(70))] for _ in range(250)]
        for values in cases:
            assert module.heap_sort(values[:]) == sorted(values), values
            pending = module.from_list(values[:])
            output = []
            while pending:
                value, pending = module.pop(pending)
                output.append(value)
            assert output == sorted(values), values
            assert module.n_smallest(module.from_list(values[:]), 3) == sorted(values)[:3], values
        print(result.stdout, end="")
        print(json.dumps({"cases": len(cases), "queue_assertions": 3 * len(cases),
                          "pinned_example": "passed", "backend": "Python"}))

if __name__ == "__main__":
    main()
