"""
tests/test_issue_195_stdlib_import.py  -  Regression tests for Issue #195
Verifies that stdlib modules (algorithms, data, science, crypto) can be imported
into .ltl code via `import <mod>`, `import stdlib.<mod>`, `import stdlib.<mod> as <alias>`,
and selective `from <mod> import <fn>` without NameError on the Python target.
"""
from lateralus_lang.compiler import Compiler, Target


def test_import_algorithms_unqualified_call():
    """import algorithms makes primes_up_to and bubble_sort callable unqualified."""
    src = """
    import algorithms

    fn main() {
        let p = primes_up_to(10)
        assert_eq(p, [2, 3, 5, 7])
        let s = bubble_sort([3, 1, 2])
        assert_eq(s, [1, 2, 3])
    }
    """
    r = Compiler().compile_source(src, target=Target.PYTHON)
    assert r.ok, r.errors
    exec(r.python_src, {"__name__": "__main__"})


def test_import_stdlib_algorithms_unqualified_and_qualified():
    """import stdlib.algorithms makes functions callable both unqualified and through namespace."""
    src = """
    import stdlib.algorithms

    fn main() {
        let p1 = primes_up_to(10)
        assert_eq(p1, [2, 3, 5, 7])
        let p2 = algorithms.primes_up_to(10)
        assert_eq(p2, [2, 3, 5, 7])
    }
    """
    r = Compiler().compile_source(src, target=Target.PYTHON)
    assert r.ok, r.errors
    exec(r.python_src, {"__name__": "__main__"})


def test_import_stdlib_algorithms_aliased():
    """import stdlib.algorithms as alg binds the alias and provides symbols."""
    src = """
    import stdlib.algorithms as alg

    fn main() {
        let p1 = alg.primes_up_to(10)
        assert_eq(p1, [2, 3, 5, 7])
        let p2 = primes_up_to(10)
        assert_eq(p2, [2, 3, 5, 7])
    }
    """
    r = Compiler().compile_source(src, target=Target.PYTHON)
    assert r.ok, r.errors
    exec(r.python_src, {"__name__": "__main__"})


def test_from_algorithms_selective_import():
    """from algorithms import primes_up_to selectively imports symbols into scope."""
    src = """
    from algorithms import primes_up_to, bubble_sort

    fn main() {
        let p = primes_up_to(10)
        assert_eq(p, [2, 3, 5, 7])
        let s = bubble_sort([4, 2, 3])
        assert_eq(s, [2, 3, 4])
    }
    """
    r = Compiler().compile_source(src, target=Target.PYTHON)
    assert r.ok, r.errors
    exec(r.python_src, {"__name__": "__main__"})


def test_from_stdlib_algorithms_selective_import():
    """from stdlib.algorithms import primes_up_to selectively imports symbols."""
    src = """
    from stdlib.algorithms import primes_up_to

    fn main() {
        let p = primes_up_to(10)
        assert_eq(p, [2, 3, 5, 7])
    }
    """
    r = Compiler().compile_source(src, target=Target.PYTHON)
    assert r.ok, r.errors
    exec(r.python_src, {"__name__": "__main__"})


def test_import_data_stack():
    """import data provides container operations like stack_new, stack_push."""
    src = """
    import data

    fn main() {
        let s = stack_new()
        stack_push(s, 100)
        assert_eq(s["size"], 1)
    }
    """
    r = Compiler().compile_source(src, target=Target.PYTHON)
    assert r.ok, r.errors
    exec(r.python_src, {"__name__": "__main__"})
