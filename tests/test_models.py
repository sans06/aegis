"""Tests for data models"""

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

from datetime import datetime
from pathlib import Path

import pytest

from synexian.constants import Grade, IssueCategory, ResultStatus, Severity
from synexian.models import AnalysisReport, AnalysisResult, Issue, MetricValue, SummaryStats


class TestMetricValue:
    """Tests for MetricValue model."""

    def test_metric_value_creation(self):
        metric = MetricValue(name="test_metric", value=50.0, threshold=100.0)
        assert metric.name == "test_metric"
        assert metric.value == 50.0
        assert metric.threshold == 100.0
        assert metric.passed is True

    def test_metric_value_failing_threshold(self):
        metric = MetricValue(name="test_metric", value=150.0, threshold=100.0)
        assert metric.passed is False

    def test_metric_value_to_dict(self):
        metric = MetricValue(name="test_metric", value=50.0, unit="%")
        data = metric.to_dict()
        assert data["name"] == "test_metric"
        assert data["value"] == 50.0
        assert data["unit"] == "%"


class TestIssue:
    """Tests for Issue model."""

    def test_issue_creation(self):
        issue = Issue(
            severity=Severity.HIGH,
            category=IssueCategory.SECURITY,
            title="Test Issue",
            description="Test description",
            file_path=Path("/test/file.py"),
            line_number=10,
        )
        assert issue.severity == Severity.HIGH
        assert issue.category == IssueCategory.SECURITY
        assert issue.title == "Test Issue"

    def test_issue_to_dict(self):
        issue = Issue(
            severity=Severity.MEDIUM,
            category=IssueCategory.COMPLEXITY,
            title="Test",
            description="Desc",
        )
        data = issue.to_dict()
        assert data["severity"] == "medium"
        assert data["category"] == "complexity"

    def test_issue_location_string(self):
        issue = Issue(
            severity=Severity.LOW,
            category=IssueCategory.STYLE,
            title="Test",
            description="Desc",
            file_path=Path("test.py"),
            line_number=5,
            column_number=10,
        )
        location = issue.get_location_string()
        assert "test.py:5:10" in location


class TestAnalysisResult:
    """Tests for AnalysisResult model."""

    def test_analysis_result_creation(self):
        result = AnalysisResult(
            analyzer_name="test_analyzer",
            analyzer_version="1.0.0",
            status=ResultStatus.SUCCESS,
        )
        assert result.analyzer_name == "test_analyzer"
        assert result.status == ResultStatus.SUCCESS

    def test_get_issues_by_severity(self):
        issues = [
            Issue(Severity.HIGH, IssueCategory.SECURITY, "Test1", "Desc1"),
            Issue(Severity.LOW, IssueCategory.STYLE, "Test2", "Desc2"),
            Issue(Severity.HIGH, IssueCategory.COMPLEXITY, "Test3", "Desc3"),
        ]

        result = AnalysisResult(
            analyzer_name="test",
            analyzer_version="1.0.0",
            status=ResultStatus.SUCCESS,
            issues=issues,
        )

        high_issues = result.get_issues_by_severity(Severity.HIGH)
        assert len(high_issues) == 2


class TestAnalysisReport:
    """Tests for AnalysisReport model."""

    def test_report_creation(self):
        report = AnalysisReport(
            project_path=Path("/test/project"),
            timestamp=datetime.now(),
            overall_score=85.0,
            grade=Grade.B,
        )
        assert report.overall_score == 85.0
        assert report.grade == Grade.B

    def test_get_all_issues(self):
        result1 = AnalysisResult(
            analyzer_name="test1",
            analyzer_version="1.0.0",
            status=ResultStatus.SUCCESS,
            issues=[Issue(Severity.HIGH, IssueCategory.SECURITY, "Issue1", "Desc1")],
        )

        result2 = AnalysisResult(
            analyzer_name="test2",
            analyzer_version="1.0.0",
            status=ResultStatus.SUCCESS,
            issues=[Issue(Severity.LOW, IssueCategory.STYLE, "Issue2", "Desc2")],
        )

        report = AnalysisReport(
            project_path=Path("/test"),
            timestamp=datetime.now(),
            results=[result1, result2],
        )

        all_issues = report.get_all_issues()
        assert len(all_issues) == 2

    def test_has_critical_issues(self):
        report = AnalysisReport(
            project_path=Path("/test"),
            timestamp=datetime.now(),
        )
        report.summary_stats = SummaryStats(critical_issues=1)

        assert report.has_critical_issues() is True
