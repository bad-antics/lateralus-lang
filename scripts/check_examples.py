#!/usr/bin/env python3
"""Check which example .ltl files compile successfully."""
import os, glob, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lateralus_lang.compiler import Compiler, Target

files = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'examples', '*.ltl')))
print(f'Found {len(files)} .ltl files\n')
print(f'{"FILE":<35} RESULT')
print('-' * 80)
ok_count = 0
fail_count = 0
for f in files:
    fname = os.path.basename(f)
    try:
        src = open(f).read()
        r = Compiler().compile_source(src, target=Target.PYTHON, filename=fname)
        if r.ok:
            print(f'{fname:<35} OK')
            ok_count += 1
        else:
            msg = r.errors[0].message if r.errors else 'unknown'
            print(f'{fname:<35} FAIL: {msg}')
            fail_count += 1
    except Exception as e:
        print(f'{fname:<35} EXCEPTION: {e}')
        fail_count += 1

print('-' * 80)
print(f'Total: {ok_count} OK, {fail_count} FAIL, {ok_count + fail_count} total')
