"""
tests/test_optimizer.py — Tests for the LATERALUS code optimizer
"""
import pytest
from lateralus_lang.optimizer import (
    OptLevel, Optimizer,
    try_fold_binary, try_fold_unary, try_fold_call,
    find_dead_variables, find_unreachable_after_return,
    apply_strength_reduction,
    can_fuse_pipeline, describe_fusion,
    CSETracker, OptimizationReport,
    # v2.4.0 — new passes
    evaluate_constant_condition, analyze_dead_branches, simplify_branch,
    apply_algebraic_simplification, ALGEBRAIC_IDENTITIES,
    analyze_inline_candidate, InlineCandidate, SIDE_EFFECT_FUNCTIONS,
    DeadBranchResult,
)


class TestConstantFolding:
    def test_fold_int_add(self):
        r = try_fold_binary("+", 3, 5)
        assert r.folded and r.value == 8

    def test_fold_int_mul(self):
        r = try_fold_binary("*", 4, 7)
        assert r.folded and r.value == 28

    def test_fold_float_div(self):
        r = try_fold_binary("/", 10.0, 4.0)
        assert r.folded and abs(r.value - 2.5) < 1e-10

    def test_fold_div_by_zero(self):
        r = try_fold_binary("/", 10, 0)
        assert not r.folded

    def test_fold_comparison(self):
        r = try_fold_binary("<", 3, 5)
        assert r.folded and r.value is True

    def test_fold_string_concat(self):
        r = try_fold_binary("+", "hello", " world")
        assert r.folded and r.value == "hello world"

    def test_fold_boolean(self):
        r = try_fold_binary("and", True, False)
        assert r.folded and r.value is False

    def test_fold_power(self):
        r = try_fold_binary("**", 2, 10)
        assert r.folded and r.value == 1024

    def test_unfoldable_types(self):
        r = try_fold_binary("+", [1, 2], [3, 4])
        assert not r.folded

    def test_unknown_operator(self):
        r = try_fold_binary("@", 1, 2)
        assert not r.folded


class TestUnaryFolding:
    def test_fold_negate(self):
        r = try_fold_unary("-", 42)
        assert r.folded and r.value == -42

    def test_fold_not(self):
        r = try_fold_unary("not", True)
        assert r.folded and r.value is False

    def test_fold_not_false(self):
        r = try_fold_unary("not", False)
        assert r.folded and r.value is True


class TestCallFolding:
    def test_fold_abs(self):
        r = try_fold_call("abs", [-5])
        assert r.folded and r.value == 5

    def test_fold_min(self):
        r = try_fold_call("min", [3, 7])
        assert r.folded and r.value == 3

    def test_fold_max(self):
        r = try_fold_call("max", [3, 7])
        assert r.folded and r.value == 7

    def test_fold_len(self):
        r = try_fold_call("len", [[1, 2, 3, 4]])
        assert r.folded and r.value == 4

    def test_fold_str(self):
        r = try_fold_call("str", [42])
        assert r.folded and r.value == "42"

    def test_unfoldable_function(self):
        r = try_fold_call("custom_fn", [1, 2])
        assert not r.folded


class TestDeadCodeElimination:
    def test_find_dead_vars(self):
        defined = {"x", "y", "z", "temp"}
        used = {"x", "z"}
        dead = find_dead_variables(defined, used)
        assert dead == {"y", "temp"}

    def test_protected_vars(self):
        defined = {"x", "result", "main"}
        used = {"x"}
        dead = find_dead_variables(defined, used, protected={"result"})
        assert "result" not in dead
        assert "main" not in dead  # special name

    def test_special_names_preserved(self):
        defined = {"_", "self", "main", "temp"}
        used = set()
        dead = find_dead_variables(defined, used)
        assert "_" not in dead
        assert "self" not in dead
        assert "main" not in dead
        assert "temp" in dead


class TestStrengthReduction:
    def test_multiply_by_zero(self):
        r = apply_strength_reduction("*", "x", 0)
        assert r == ("const", 0, None)

    def test_multiply_by_one(self):
        r = apply_strength_reduction("*", "x", 1)
        assert r == ("identity", "x", None)

    def test_add_zero(self):
        r = apply_strength_reduction("+", "x", 0)
        assert r == ("identity", "x", None)

    def test_power_zero(self):
        r = apply_strength_reduction("**", "x", 0)
        assert r == ("const", 1, None)

    def test_power_one(self):
        r = apply_strength_reduction("**", "x", 1)
        assert r == ("identity", "x", None)

    def test_power_two(self):
        r = apply_strength_reduction("**", "x", 2)
        assert r == ("*", "x", "x")

    def test_multiply_by_power_of_2(self):
        r = apply_strength_reduction("*", "x", 8)
        assert r == ("<<", "x", 3)

    def test_no_reduction(self):
        r = apply_strength_reduction("+", "x", 3)
        assert r is None


class TestCSETracker:
    def test_first_occurrence(self):
        cse = CSETracker()
        result = cse.register("a + b")
        assert result is None  # First time, not yet reusable

    def test_second_occurrence(self):
        cse = CSETracker()
        cse.register("a + b")
        result = cse.register("a + b")
        assert result is not None  # Now it's reusable

    def test_different_expressions(self):
        cse = CSETracker()
        cse.register("a + b")
        cse.register("c * d")
        reusable = cse.get_reusable()
        assert len(reusable) == 0

    def test_reusable_extraction(self):
        cse = CSETracker()
        cse.register("x * x + y * y")
        cse.register("a + b")
        cse.register("x * x + y * y")
        reusable = cse.get_reusable()
        assert len(reusable) == 1
        assert reusable[0].expression == "x * x + y * y"


class TestPipelineFusion:
    def test_map_map_fusable(self):
        assert can_fuse_pipeline(["map", "map"])

    def test_map_filter_fusable(self):
        assert can_fuse_pipeline(["map", "filter"])

    def test_filter_map_fusable(self):
        assert can_fuse_pipeline(["filter", "map"])

    def test_filter_filter_fusable(self):
        assert can_fuse_pipeline(["filter", "filter"])

    def test_sort_not_fusable(self):
        assert not can_fuse_pipeline(["sort", "map"])

    def test_reduce_not_fusable(self):
        assert not can_fuse_pipeline(["map", "reduce"])

    def test_single_stage_not_fusable(self):
        assert not can_fuse_pipeline(["map"])

    def test_triple_map_fusable(self):
        assert can_fuse_pipeline(["map", "map", "map"])

    def test_describe_all_maps(self):
        desc = describe_fusion(["map", "map", "map"])
        assert "composed" in desc.lower() or "fuse" in desc.lower()


class TestOptimizer:
    def test_o0_no_folding(self):
        opt = Optimizer(level=OptLevel.O0)
        folded, val = opt.optimize_constant("+", 3, 5)
        assert not folded

    def test_o1_constant_folding(self):
        opt = Optimizer(level=OptLevel.O1)
        folded, val = opt.optimize_constant("+", 3, 5)
        assert folded and val == 8

    def test_o1_unary_folding(self):
        opt = Optimizer(level=OptLevel.O1)
        folded, val = opt.optimize_unary("-", 42)
        assert folded and val == -42

    def test_o2_strength_reduction(self):
        opt = Optimizer(level=OptLevel.O2)
        r = opt.optimize_strength("*", "x", 8)
        assert r == ("<<", "x", 3)

    def test_o1_no_strength(self):
        opt = Optimizer(level=OptLevel.O1)
        r = opt.optimize_strength("*", "x", 8)
        assert r is None

    def test_o3_pipeline_fusion(self):
        opt = Optimizer(level=OptLevel.O3)
        assert opt.check_pipeline_fusion(["map", "map"])

    def test_o2_no_pipeline_fusion(self):
        opt = Optimizer(level=OptLevel.O2)
        assert not opt.check_pipeline_fusion(["map", "map"])

    def test_report_generation(self):
        opt = Optimizer(level=OptLevel.O2)
        opt.optimize_constant("+", 3, 5)
        opt.optimize_constant("*", 2, 10)
        opt.optimize_strength("*", "x", 4)
        opt.track_expression("a + b")
        opt.track_expression("a + b")  # second occurrence
        report = opt.finalize()
        assert report.constants_folded == 2
        assert report.strength_reductions == 1
        assert report.cse_extractions == 1
        assert report.total_optimizations >= 4

    def test_report_summary(self):
        opt = Optimizer(level=OptLevel.O1)
        opt.optimize_constant("+", 1, 2)
        report = opt.finalize()
        summary = report.summary()
        assert "Constants folded" in summary
        assert "1" in summary


# =========================================================================
# v2.4.0 — Dead Branch Elimination
# =========================================================================

class TestEvaluateConstantCondition:
    def test_true(self):
        assert evaluate_constant_condition(True) is True

    def test_false(self):
        assert evaluate_constant_condition(False) is False

    def test_zero_is_falsy(self):
        assert evaluate_constant_condition(0) is False

    def test_nonzero_is_truthy(self):
        assert evaluate_constant_condition(42) is True
        assert evaluate_constant_condition(-1) is True

    def test_empty_string_falsy(self):
        assert evaluate_constant_condition("") is False

    def test_nonempty_string_truthy(self):
        assert evaluate_constant_condition("hello") is True

    def test_none_is_falsy(self):
        assert evaluate_constant_condition(None) is False

    def test_unknown_returns_none(self):
        assert evaluate_constant_condition([1, 2, 3]) is None
        assert evaluate_constant_condition({"a": 1}) is None


class TestSimplifyBranch:
    def test_true_returns_then(self):
        then = ["a", "b"]
        els = ["c", "d"]
        assert simplify_branch(True, then, els) == ["a", "b"]

    def test_false_returns_else(self):
        then = ["a", "b"]
        els = ["c", "d"]
        assert simplify_branch(False, then, els) == ["c", "d"]

    def test_false_no_else_returns_empty(self):
        then = ["a", "b"]
        assert simplify_branch(False, then, None) == []


class TestDeadBranchResult:
    def test_default_values(self):
        r = DeadBranchResult()
        assert r.branches_eliminated == 0
        assert r.conditions_simplified == 0


# =========================================================================
# v2.4.0 — Algebraic Simplification
# =========================================================================

class TestAlgebraicSimplification:
    def test_x_minus_x(self):
        r = apply_algebraic_simplification("-", "x", "x", same_operand=True)
        assert r == ("const", 0)

    def test_x_div_x(self):
        r = apply_algebraic_simplification("/", "x", "x", same_operand=True)
        assert r == ("const", 1)

    def test_x_mod_x(self):
        r = apply_algebraic_simplification("%", "x", "x", same_operand=True)
        assert r == ("const", 0)

    def test_x_xor_x(self):
        r = apply_algebraic_simplification("^", "x", "x", same_operand=True)
        assert r == ("const", 0)

    def test_x_and_x(self):
        r = apply_algebraic_simplification("&", "x", "x", same_operand=True)
        assert r == ("identity", "x")

    def test_x_or_x(self):
        r = apply_algebraic_simplification("|", "x", "x", same_operand=True)
        assert r == ("identity", "x")

    def test_and_zero(self):
        r = apply_algebraic_simplification("&", "x", 0)
        assert r == ("const", 0)

    def test_and_zero_left(self):
        r = apply_algebraic_simplification("&", 0, "x")
        assert r == ("const", 0)

    def test_or_zero(self):
        r = apply_algebraic_simplification("|", "x", 0)
        assert r == ("identity", "x")

    def test_xor_zero(self):
        r = apply_algebraic_simplification("^", "x", 0)
        assert r == ("identity", "x")

    def test_shift_left_zero(self):
        r = apply_algebraic_simplification("<<", "x", 0)
        assert r == ("identity", "x")

    def test_shift_right_zero(self):
        r = apply_algebraic_simplification(">>", "x", 0)
        assert r == ("identity", "x")

    def test_and_true(self):
        r = apply_algebraic_simplification("and", "x", True)
        assert r == ("identity", "x")

    def test_and_false(self):
        r = apply_algebraic_simplification("and", "x", False)
        assert r == ("const", False)

    def test_or_true(self):
        r = apply_algebraic_simplification("or", "x", True)
        assert r == ("const", True)

    def test_or_false(self):
        r = apply_algebraic_simplification("or", "x", False)
        assert r == ("identity", "x")

    def test_no_simplification(self):
        r = apply_algebraic_simplification("+", "x", "y", same_operand=False)
        assert r is None

    def test_xor_self_via_xor_keyword(self):
        r = apply_algebraic_simplification("xor", "x", "x", same_operand=True)
        assert r == ("const", 0)


class TestAlgebraicIdentities:
    def test_identities_list_not_empty(self):
        assert len(ALGEBRAIC_IDENTITIES) > 10

    def test_all_have_description(self):
        for ai in ALGEBRAIC_IDENTITIES:
            assert ai.pattern
            assert ai.result
            assert ai.description


# =========================================================================
# v2.4.0 — Function Inlining Analysis
# =========================================================================

class TestInlineCandidate:
    def test_tiny_pure_function(self):
        c = analyze_inline_candidate("add", 2, ["ret"], 5, set())
        assert c.should_inline is True
        assert c.score > 1.0
        assert not c.has_side_effects
        assert not c.is_recursive

    def test_large_function_not_inlined(self):
        c = analyze_inline_candidate("big", 3, list(range(20)), 2, set())
        assert c.should_inline is False
        assert c.body_size == 20

    def test_recursive_never_inlined(self):
        c = analyze_inline_candidate("fib", 1, ["a", "b", "c"], 10, {"fib"})
        assert c.should_inline is False
        assert c.is_recursive is True
        assert c.score < 0

    def test_side_effect_detected(self):
        c = analyze_inline_candidate("log", 1, ["a"], 3, {"println"})
        assert c.has_side_effects is True

    def test_no_calls_still_scored(self):
        c = analyze_inline_candidate("noop", 0, ["ret"], 0, set())
        assert c.call_count == 0

    def test_many_params_penalized(self):
        c_few = analyze_inline_candidate("f", 2, ["ret"], 3, set())
        c_many = analyze_inline_candidate("g", 6, ["ret"], 3, set())
        assert c_few.score > c_many.score

    def test_medium_body(self):
        c = analyze_inline_candidate("med", 2, list(range(5)), 3, set())
        assert c.body_size == 5
        assert c.should_inline is True

    def test_side_effect_functions_set(self):
        assert "println" in SIDE_EFFECT_FUNCTIONS
        assert "read_file" in SIDE_EFFECT_FUNCTIONS
        assert "exit" in SIDE_EFFECT_FUNCTIONS


# =========================================================================
# v2.4.0 — Optimizer integration (new methods)
# =========================================================================

class TestOptimizerNewPasses:
    def test_algebraic_at_o2(self):
        opt = Optimizer(level=OptLevel.O2)
        r = opt.optimize_algebraic("-", "x", "x", same_operand=True)
        assert r == ("const", 0)
        assert opt.report.algebraic_simplifications == 1

    def test_algebraic_below_o2_disabled(self):
        opt = Optimizer(level=OptLevel.O1)
        r = opt.optimize_algebraic("-", "x", "x", same_operand=True)
        assert r is None

    def test_dead_branch_at_o1(self):
        opt = Optimizer(level=OptLevel.O1)
        r = opt.eliminate_dead_branches([])
        assert r.branches_eliminated == 0

    def test_dead_branch_below_o1_disabled(self):
        opt = Optimizer(level=OptLevel.O0)
        r = opt.eliminate_dead_branches([])
        assert r.branches_eliminated == 0

    def test_inline_at_o3(self):
        opt = Optimizer(level=OptLevel.O3)
        c = opt.analyze_inlining("add", 2, ["ret"], 5, set())
        assert c.should_inline is True
        assert "add" in opt.report.inline_candidates

    def test_inline_below_o3_disabled(self):
        opt = Optimizer(level=OptLevel.O2)
        c = opt.analyze_inlining("add", 2, ["ret"], 5, set())
        assert c.score == 0.0
        assert len(opt.report.inline_candidates) == 0

    def test_full_report_includes_new_fields(self):
        opt = Optimizer(level=OptLevel.O3)
        opt.optimize_algebraic("^", "x", "x", same_operand=True)
        opt.analyze_inlining("tiny", 1, ["ret"], 3, set())
        report = opt.finalize()
        summary = report.summary()
        assert "Algebraic simplifications" in summary
        assert "Dead branches" in summary
        assert "Inline candidates" in summary
        assert report.algebraic_simplifications == 1
        assert "tiny" in report.inline_candidates
