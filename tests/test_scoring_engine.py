"""
Tests for ScoringEngine  the correct but currently unused scoring implementation.
These tests document the CORRECT scoring behaviour and will guide the fix
when ScoringEngine replaces the duplicate logic in AnalyzerEngine.
"""

import pytest
from synexian.core.scoring_engine import ScoringEngine
from synexian.constants import (
    DEFAULT_ANALYZER_WEIGHTS, AnalyzerType, Grade, ResultStatus, Severity
)
from synexian.models import AnalysisResult, MetricValue
from synexian.models.issue import Issue
from synexian.constants import IssueCategory


@pytest.fixture
def engine():
    return ScoringEngine(analyzer_weights=DEFAULT_ANALYZER_WEIGHTS)


@pytest.fixture
def perfect_security_result():
    return AnalysisResult(
        analyzer_name="security",
        analyzer_version="1.0",
        status=ResultStatus.SUCCESS,
        metrics={
            "critical_vulns": MetricValue("critical_vulns", 0, threshold=0.0),
            "high_vulns": MetricValue("high_vulns", 0, threshold=5.0),
        },
        issues=[],
    )


@pytest.fixture
def failing_security_result():
    return AnalysisResult(
        analyzer_name="security",
        analyzer_version="1.0",
        status=ResultStatus.SUCCESS,
        metrics={
            "critical_vulns": MetricValue("critical_vulns", 0, threshold=0.0),
            "high_vulns": MetricValue("high_vulns", 2, threshold=5.0),
        },
        issues=[
            Issue(Severity.HIGH, IssueCategory.SECURITY, "SQL injection", "Use params"),
            Issue(Severity.HIGH, IssueCategory.SECURITY, "Hardcoded password", "Use env"),
        ],
    )


class TestScoringEngineGrade:
    """Test grade calculation at all score boundaries."""

    def test_grade_a_plus_at_95(self, engine):
        assert engine.calculate_grade(95.0) == Grade.A_PLUS

    def test_grade_a_plus_at_100(self, engine):
        assert engine.calculate_grade(100.0) == Grade.A_PLUS

    def test_grade_a_just_below_a_plus(self, engine):
        assert engine.calculate_grade(94.9) == Grade.A

    def test_grade_a_at_90(self, engine):
        assert engine.calculate_grade(90.0) == Grade.A

    def test_grade_b_plus_at_85(self, engine):
        assert engine.calculate_grade(85.0) == Grade.B_PLUS

    def test_grade_b_at_80(self, engine):
        assert engine.calculate_grade(80.0) == Grade.B

    def test_grade_c_plus_at_75(self, engine):
        assert engine.calculate_grade(75.0) == Grade.C_PLUS

    def test_grade_c_at_70(self, engine):
        assert engine.calculate_grade(70.0) == Grade.C

    def test_grade_d_at_60(self, engine):
        assert engine.calculate_grade(60.0) == Grade.D

    def test_grade_f_at_59_9(self, engine):
        assert engine.calculate_grade(59.9) == Grade.F

    def test_grade_f_at_zero(self, engine):
        assert engine.calculate_grade(0.0) == Grade.F

    def test_grade_f_at_negative(self, engine):
        assert engine.calculate_grade(-1.0) == Grade.F


class TestScoringEngineFormula:
    """Test the 70/30 metric/issue scoring formula  the CORRECT formula."""

    def test_perfect_score_no_issues(self, engine, perfect_security_result):
        """Perfect metrics, no issues = 1.0 analyzer score."""
        score = engine._calculate_analyzer_score(perfect_security_result)
        assert score == pytest.approx(1.0)

    def test_issues_reduce_score(self, engine, failing_security_result):
        """2 HIGH issues should reduce score via the 30% issue penalty."""
        score = engine._calculate_analyzer_score(failing_security_result)
        # 2 HIGH issues: penalty = 0.2, score = (1.0 * 0.7) + (0.8 * 0.3) = 0.94
        assert score == pytest.approx(0.94)

    def test_critical_issue_larger_penalty(self, engine):
        result = AnalysisResult(
            analyzer_name="security", analyzer_version="1.0",
            status=ResultStatus.SUCCESS,
            issues=[Issue(Severity.CRITICAL, IssueCategory.SECURITY, "CVE", "Fix it")],
        )
        score = engine._calculate_analyzer_score(result)
        # CRITICAL: penalty = 0.2, metric_score = 1.0 (no metrics = 1.0)
        # score = (1.0 * 0.7) + ((1.0 - 0.2) * 0.3) = 0.94
        assert score == pytest.approx(0.94)

    def test_issue_penalty_caps_at_one(self, engine):
        """Many issues: penalty should cap at 1.0, not exceed it."""
        result = AnalysisResult(
            analyzer_name="security", analyzer_version="1.0",
            status=ResultStatus.SUCCESS,
            issues=[
                Issue(Severity.CRITICAL, IssueCategory.SECURITY, f"Issue {i}", "desc")
                for i in range(10)
            ],
        )
        score = engine._calculate_analyzer_score(result)
        assert score >= 0.0
        assert score <= 1.0
        # 10 CRITICAL: penalty = min(1.0, 2.0) = 1.0
        # score = (1.0 * 0.7) + (0.0 * 0.3) = 0.7
        assert score == pytest.approx(0.7)

    def test_failing_metrics_reduce_score(self, engine):
        """Failed metrics reduce the 70% metrics portion."""
        result = AnalysisResult(
            analyzer_name="complexity", analyzer_version="1.0",
            status=ResultStatus.SUCCESS,
            metrics={
                "avg_cc": MetricValue("avg_cc", 15.0, threshold=10.0),   # FAILS
                "max_cc": MetricValue("max_cc", 5.0, threshold=10.0),    # passes
            },
        )
        score = engine._calculate_analyzer_score(result)
        # metric_score = 1/2 = 0.5, no issues
        # score = (0.5 * 0.7) + (1.0 * 0.3) = 0.65
        assert score == pytest.approx(0.65)


class TestOverallScoreCalculation:
    """Test overall score calculation across multiple analyzers."""

    def test_empty_results_returns_zero(self, engine):
        assert engine.calculate_overall_score([]) == 0.0

    def test_all_failed_results_returns_zero(self, engine):
        failed = AnalysisResult(
            analyzer_name="security", analyzer_version="1.0",
            status=ResultStatus.FAILED,
        )
        assert engine.calculate_overall_score([failed]) == 0.0

    def test_skipped_results_excluded_from_score(self, engine):
        skipped = AnalysisResult(
            analyzer_name="security", analyzer_version="1.0",
            status=ResultStatus.SKIPPED,
        )
        assert engine.calculate_overall_score([skipped]) == 0.0

    def test_perfect_results_return_100(self, engine):
        results = [
            AnalysisResult(
                analyzer_name=name, analyzer_version="1.0",
                status=ResultStatus.SUCCESS,
            )
            for name in ["security", "complexity", "style", "architecture",
                         "edge_cases", "test_quality", "cognitive_load"]
        ]
        score = engine.calculate_overall_score(results)
        # All score 1.0 with no metrics/issues
        assert score == pytest.approx(100.0)

    def test_security_weighted_highest(self, engine):
        """Security at 0% should have more impact than style at 0%."""
        bad_security = AnalysisResult(
            analyzer_name="security", analyzer_version="1.0",
            status=ResultStatus.SUCCESS,
            issues=[Issue(Severity.CRITICAL, IssueCategory.SECURITY, "crit", "desc")
                    for _ in range(10)],
        )
        bad_style = AnalysisResult(
            analyzer_name="style", analyzer_version="1.0",
            status=ResultStatus.SUCCESS,
            issues=[Issue(Severity.CRITICAL, IssueCategory.STYLE, "crit", "desc")
                    for _ in range(10)],
        )
        sec_score = engine.calculate_overall_score([bad_security])
        style_score = engine.calculate_overall_score([bad_style])
        # Security weight (0.25) > Style weight (0.10)
        # Both have same analyzer_score, but security contributes more
        # After normalization both are equal because they're the only active analyzer
        # The difference shows when combined: security drag > style drag
        # Test: security has weight 0.25, style has 0.10  security causes more overall drag
        # Both normalized to same total_weight so we need both in same run
        both_perfect_except_security = [
            AnalysisResult(analyzer_name="security", analyzer_version="1.0",
                          status=ResultStatus.SUCCESS,
                          issues=[Issue(Severity.CRITICAL, IssueCategory.SECURITY, "c", "d")
                                  for _ in range(10)]),
            AnalysisResult(analyzer_name="style", analyzer_version="1.0",
                          status=ResultStatus.SUCCESS),
        ]
        both_perfect_except_style = [
            AnalysisResult(analyzer_name="security", analyzer_version="1.0",
                          status=ResultStatus.SUCCESS),
            AnalysisResult(analyzer_name="style", analyzer_version="1.0",
                          status=ResultStatus.SUCCESS,
                          issues=[Issue(Severity.CRITICAL, IssueCategory.STYLE, "c", "d")
                                  for _ in range(10)]),
        ]
        score_with_bad_security = engine.calculate_overall_score(both_perfect_except_security)
        score_with_bad_style = engine.calculate_overall_score(both_perfect_except_style)
        assert score_with_bad_security < score_with_bad_style

    def test_score_clamped_to_100(self, engine):
        result = AnalysisResult(
            analyzer_name="security", analyzer_version="1.0",
            status=ResultStatus.SUCCESS,
        )
        score = engine.calculate_overall_score([result])
        assert score <= 100.0

    def test_score_never_negative(self, engine):
        result = AnalysisResult(
            analyzer_name="security", analyzer_version="1.0",
            status=ResultStatus.SUCCESS,
            issues=[Issue(Severity.CRITICAL, IssueCategory.SECURITY, "c", "d")
                    for _ in range(100)],
        )
        score = engine.calculate_overall_score([result])
        assert score >= 0.0

    def test_custom_rules_weight_zero_has_no_impact(self, engine):
        """custom_rules at weight 0.0 should not affect overall score  documents the defect."""
        base_results = [
            AnalysisResult(analyzer_name="security", analyzer_version="1.0",
                          status=ResultStatus.SUCCESS)
        ]
        results_with_custom = base_results + [
            AnalysisResult(
                analyzer_name="custom_rules", analyzer_version="1.0",
                status=ResultStatus.SUCCESS,
                issues=[Issue(Severity.CRITICAL, IssueCategory.CUSTOM, "violation", "desc")
                        for _ in range(50)],
            )
        ]
        score_without = engine.calculate_overall_score(base_results)
        score_with = engine.calculate_overall_score(results_with_custom)
        # BUG: these should differ  custom_rules has violations but weight=0.0
        # This test documents the current behaviour and will need updating once fixed
        assert score_without == score_with, (
            "custom_rules with weight=0.0 should not affect score "
            "(this test documents the defect  update when weight is fixed)"
        )
