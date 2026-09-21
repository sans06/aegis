"""
Tests for MetricValue threshold logic.
These tests DOCUMENT BUG CR-10 / LV-03:
  is_within_threshold() always uses <= regardless of whether higher is better.

Tests marked xfail will FAIL currently and PASS once the bug is fixed.
Tests NOT marked xfail document the current (broken) behaviour.
"""

import pytest
from synexian.models.metric import MetricValue


class TestCurrentBehaviour:
    """
    Document the CURRENT broken behaviour.
    These tests PASS NOW but represent incorrect logic.
    Once is_within_threshold() is fixed, these expectations will change.
    """

    def test_low_coverage_currently_passes(self):
        """
        BUG: 40% coverage below 80% threshold currently shows passed=True.
        This is WRONG  low coverage should FAIL the threshold.
        This test documents the broken state.
        """
        metric = MetricValue("code_coverage", value=40.0, threshold=80.0)
        # Currently returns True because 40 <= 80
        # CORRECT answer would be False (coverage BELOW target)
        assert metric.passed is True  # BUG documented

    def test_high_coverage_currently_fails(self):
        """
        BUG: 90% coverage above 80% threshold currently shows passed=False.
        This is WRONG  good coverage should PASS.
        """
        metric = MetricValue("code_coverage", value=90.0, threshold=80.0)
        # Currently returns False because 90 > 80
        # CORRECT answer would be True (coverage ABOVE target)
        assert metric.passed is False  # BUG documented

    def test_low_mutation_score_currently_passes(self):
        """BUG: 30% mutation score below 70% threshold shows passed=True."""
        metric = MetricValue("mutation_score", value=30.0, threshold=70.0)
        assert metric.passed is True  # BUG documented


class TestComplexityMetrics:
    """Complexity metrics work correctly because lower IS better."""

    def test_low_cyclomatic_passes(self):
        """CC=5 below threshold 10 correctly passes (lower is better)."""
        metric = MetricValue("cyclomatic_complexity", value=5, threshold=10)
        assert metric.passed is True

    def test_high_cyclomatic_fails(self):
        """CC=15 above threshold 10 correctly fails (lower is better)."""
        metric = MetricValue("cyclomatic_complexity", value=15, threshold=10)
        assert metric.passed is False

    def test_exact_threshold_passes(self):
        """CC=10 equal to threshold 10 correctly passes (inclusive)."""
        metric = MetricValue("cyclomatic_complexity", value=10, threshold=10)
        assert metric.passed is True

    def test_zero_issues_passes(self):
        """0 critical issues (threshold 0) passes correctly."""
        metric = MetricValue("critical_issues", value=0, threshold=0.0)
        assert metric.passed is True

    def test_one_critical_issue_fails(self):
        """1 critical issue above threshold 0 correctly fails."""
        metric = MetricValue("critical_issues", value=1, threshold=0.0)
        assert metric.passed is False


class TestNoThreshold:
    """Metrics without thresholds should have passed=None."""

    def test_no_threshold_passed_is_none(self):
        metric = MetricValue("total_functions", value=42)
        assert metric.passed is None

    def test_string_value_no_threshold(self):
        metric = MetricValue("grade", value="A+")
        assert metric.passed is None

    def test_string_value_with_threshold_skipped(self):
        """String values with threshold should not evaluate (can't compare)."""
        metric = MetricValue("grade", value="A+", threshold=80.0)
        # passed stays None  string cannot be compared numerically
        # __post_init__ checks isinstance(value, (int, float))
        assert metric.passed is None


class TestCorrectBehaviourAfterFix:
    """
    Tests that document the CORRECT expected behaviour.
    All tests in this class are currently xfail.
    Remove xfail markers after fixing is_within_threshold().
    """

    @pytest.mark.xfail(reason="BUG CR-10: is_within_threshold always uses <=, ignores higher_is_better")
    def test_coverage_40_should_fail(self):
        """After fix: 40% coverage below 80% target must return passed=False."""
        # To fix: add higher_is_better=True to MetricValue for coverage metrics
        metric = MetricValue("code_coverage", value=40.0, threshold=80.0,
                             higher_is_better=True)
        assert metric.passed is False

    @pytest.mark.xfail(reason="BUG CR-10: is_within_threshold always uses <=")
    def test_coverage_90_should_pass(self):
        """After fix: 90% coverage above 80% target must return passed=True."""
        metric = MetricValue("code_coverage", value=90.0, threshold=80.0,
                             higher_is_better=True)
        assert metric.passed is True

    @pytest.mark.xfail(reason="BUG CR-10: is_within_threshold always uses <=")
    def test_mutation_score_30_should_fail(self):
        """After fix: 30% mutation score below 70% target must fail."""
        metric = MetricValue("mutation_score", value=30.0, threshold=70.0,
                             higher_is_better=True)
        assert metric.passed is False

    @pytest.mark.xfail(reason="BUG CR-10: is_within_threshold always uses <=")
    def test_test_to_code_ratio_should_fail(self):
        """After fix: 0.1 ratio below 0.5 target must fail."""
        metric = MetricValue("test_to_code_ratio", value=0.1, threshold=0.5,
                             higher_is_better=True)
        assert metric.passed is False


class TestMetricValueEdgeCases:
    """Edge cases in MetricValue creation and comparison."""

    def test_zero_value_zero_threshold(self):
        metric = MetricValue("violations", value=0, threshold=0.0)
        assert metric.passed is True

    def test_negative_value_below_threshold(self):
        metric = MetricValue("score", value=-5, threshold=0)
        assert metric.passed is True  # -5 <= 0

    def test_float_precision(self):
        metric = MetricValue("score", value=10.0000001, threshold=10.0)
        assert metric.passed is False  # slightly above threshold

    def test_serialization_preserves_passed(self):
        metric = MetricValue("cc", value=5, threshold=10)
        d = metric.to_dict()
        assert d["passed"] is True

    @pytest.mark.xfail(reason="NEW BUG: __post_init__ recalculates passed, overwriting value loaded from dict")
    def test_from_dict_preserves_passed(self):
        """from_dict should restore passed from dict, not recalculate."""
        metric = MetricValue.from_dict({
            "name": "cc", "value": 5, "threshold": 10, "passed": False
        })
        # passed is loaded from dict, not recalculated
        assert metric.passed is False
