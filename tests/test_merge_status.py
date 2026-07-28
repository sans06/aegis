"""
Tests for AnalysisResult.merge_with() status logic.
Documents BUG CR-22 / LV-05: 5 of 16 status combinations return wrong results.

Tests marked xfail document CORRECT behaviour — they will pass after the fix.
"""

import pytest
from synexian.constants import ResultStatus
from synexian.models.analysis_result import AnalysisResult


def make_result(name, status):
    return AnalysisResult(
        analyzer_name=name,
        analyzer_version="1.0",
        status=status,
    )


def merge_status(a_status, b_status):
    a = make_result("test", a_status)
    b = make_result("test", b_status)
    return a.merge_with(b).status


class TestMergeWithCurrentBehaviour:
    """Document current merge_with() behaviour — including bugs."""

    # Correct combinations (11 of 16)
    def test_success_success_returns_success(self):
        assert merge_status(ResultStatus.SUCCESS, ResultStatus.SUCCESS) == ResultStatus.SUCCESS

    def test_success_partial_returns_partial(self):
        assert merge_status(ResultStatus.SUCCESS, ResultStatus.PARTIAL) == ResultStatus.PARTIAL

    def test_success_failed_returns_failed(self):
        assert merge_status(ResultStatus.SUCCESS, ResultStatus.FAILED) == ResultStatus.FAILED

    def test_partial_success_returns_partial(self):
        assert merge_status(ResultStatus.PARTIAL, ResultStatus.SUCCESS) == ResultStatus.PARTIAL

    def test_partial_partial_returns_partial(self):
        assert merge_status(ResultStatus.PARTIAL, ResultStatus.PARTIAL) == ResultStatus.PARTIAL

    def test_failed_success_returns_failed(self):
        assert merge_status(ResultStatus.FAILED, ResultStatus.SUCCESS) == ResultStatus.FAILED

    def test_failed_partial_returns_failed(self):
        assert merge_status(ResultStatus.FAILED, ResultStatus.PARTIAL) == ResultStatus.FAILED

    def test_failed_failed_returns_failed(self):
        assert merge_status(ResultStatus.FAILED, ResultStatus.FAILED) == ResultStatus.FAILED

    def test_failed_skipped_returns_failed(self):
        assert merge_status(ResultStatus.FAILED, ResultStatus.SKIPPED) == ResultStatus.FAILED

    def test_partial_skipped_returns_partial(self):
        # Current: partial stays partial (coincidentally correct)
        assert merge_status(ResultStatus.PARTIAL, ResultStatus.SKIPPED) == ResultStatus.PARTIAL

    def test_skipped_skipped_returns_skipped(self):
        assert merge_status(ResultStatus.SKIPPED, ResultStatus.SKIPPED) == ResultStatus.SKIPPED

    # BUG: 5 wrong combinations
    def test_bug_success_skipped_returns_skipped_not_success(self):
        """BUG: SUCCESS + SKIPPED should return SUCCESS, but returns SKIPPED."""
        # FIX VERIFIED: bug is fixed — SUCCESS + SKIPPED now correctly returns SUCCESS
        result = merge_status(ResultStatus.SUCCESS, ResultStatus.SKIPPED)
        assert result == ResultStatus.SUCCESS  # FIXED
        # Correct behaviour should be SUCCESS (skip doesn't override success)

    def test_bug_partial_failed_returns_partial_not_failed(self):
        """BUG: PARTIAL + FAILED should return FAILED, but returns PARTIAL."""
        # FIX VERIFIED: bug is fixed — PARTIAL + FAILED now correctly returns FAILED
        result = merge_status(ResultStatus.PARTIAL, ResultStatus.FAILED)
        assert result == ResultStatus.FAILED  # FIXED
        # Should be FAILED — a failure is worse than partial

    def test_bug_skipped_success_returns_skipped_not_success(self):
        """BUG: SKIPPED + SUCCESS should return SUCCESS, but returns SKIPPED."""
        result = merge_status(ResultStatus.SKIPPED, ResultStatus.SUCCESS)
        assert result == ResultStatus.SUCCESS  # FIXED

    def test_bug_skipped_partial_returns_skipped_not_partial(self):
        """BUG: SKIPPED + PARTIAL should return PARTIAL, but returns SKIPPED."""
        result = merge_status(ResultStatus.SKIPPED, ResultStatus.PARTIAL)
        assert result == ResultStatus.PARTIAL  # FIXED

    def test_bug_skipped_failed_returns_skipped_not_failed(self):
        """BUG: SKIPPED + FAILED should return FAILED, but returns SKIPPED."""
        result = merge_status(ResultStatus.SKIPPED, ResultStatus.FAILED)
        assert result == ResultStatus.FAILED  # FIXED


class TestMergeWithCorrectBehaviour:
    """
    Tests for CORRECT merge_with() behaviour.
    All marked xfail — will pass after fix.
    Priority: FAILED > PARTIAL > SUCCESS > SKIPPED
    """

    @pytest.mark.xfail(reason="BUG CR-22: SKIPPED contaminates merges incorrectly")
    def test_success_skipped_should_return_success(self):
        assert merge_status(ResultStatus.SUCCESS, ResultStatus.SKIPPED) == ResultStatus.SUCCESS

    @pytest.mark.xfail(reason="BUG CR-22: PARTIAL + FAILED should return FAILED")
    def test_partial_failed_should_return_failed(self):
        assert merge_status(ResultStatus.PARTIAL, ResultStatus.FAILED) == ResultStatus.FAILED

    @pytest.mark.xfail(reason="BUG CR-22: SKIPPED + SUCCESS should return SUCCESS")
    def test_skipped_success_should_return_success(self):
        assert merge_status(ResultStatus.SKIPPED, ResultStatus.SUCCESS) == ResultStatus.SUCCESS

    @pytest.mark.xfail(reason="BUG CR-22: SKIPPED + PARTIAL should return PARTIAL")
    def test_skipped_partial_should_return_partial(self):
        assert merge_status(ResultStatus.SKIPPED, ResultStatus.PARTIAL) == ResultStatus.PARTIAL

    @pytest.mark.xfail(reason="BUG CR-22: SKIPPED + FAILED should return FAILED")
    def test_skipped_failed_should_return_failed(self):
        assert merge_status(ResultStatus.SKIPPED, ResultStatus.FAILED) == ResultStatus.FAILED


class TestMergeWithOtherFields:
    """Test that merge_with() correctly combines non-status fields."""

    def test_metrics_are_merged(self):
        from synexian.models.metric import MetricValue
        a = make_result("test", ResultStatus.SUCCESS)
        a.metrics = {"m1": MetricValue("m1", 5)}
        b = make_result("test", ResultStatus.SUCCESS)
        b.metrics = {"m2": MetricValue("m2", 10)}
        merged = a.merge_with(b)
        assert "m1" in merged.metrics
        assert "m2" in merged.metrics

    def test_issues_are_concatenated(self):
        from synexian.models.issue import Issue
        from synexian.constants import Severity, IssueCategory
        a = make_result("test", ResultStatus.SUCCESS)
        a.issues = [Issue(Severity.HIGH, IssueCategory.SECURITY, "I1", "d")]
        b = make_result("test", ResultStatus.SUCCESS)
        b.issues = [Issue(Severity.LOW, IssueCategory.STYLE, "I2", "d")]
        merged = a.merge_with(b)
        assert len(merged.issues) == 2

    def test_execution_time_is_summed(self):
        a = make_result("test", ResultStatus.SUCCESS)
        a.execution_time_seconds = 1.5
        b = make_result("test", ResultStatus.SUCCESS)
        b.execution_time_seconds = 2.5
        merged = a.merge_with(b)
        assert merged.execution_time_seconds == pytest.approx(4.0)

    def test_cannot_merge_different_analyzers(self):
        a = make_result("security", ResultStatus.SUCCESS)
        b = make_result("complexity", ResultStatus.SUCCESS)
        with pytest.raises(ValueError, match="Cannot merge"):
            a.merge_with(b)

    def test_insights_are_concatenated(self):
        a = make_result("test", ResultStatus.SUCCESS)
        a.insights = ["insight 1"]
        b = make_result("test", ResultStatus.SUCCESS)
        b.insights = ["insight 2"]
        merged = a.merge_with(b)
        assert len(merged.insights) == 2
        assert "insight 1" in merged.insights
        assert "insight 2" in merged.insights
