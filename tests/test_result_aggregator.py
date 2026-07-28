"""
Tests for ResultAggregator  zero coverage in original suite.
API: group_issues_by_severity(report) / get_top_issues(report, limit) / 
     deduplicate_issues(issues_list) / merge_results(results_list)
"""

import pytest
from pathlib import Path
from datetime import datetime

from synexian.core.result_aggregator import ResultAggregator
from synexian.models.issue import Issue
from synexian.models.analysis_result import AnalysisResult, AnalysisReport
from synexian.constants import Severity, IssueCategory, ResultStatus


def make_issue(sev, cat, title, file_path=None, line=None):
    return Issue(severity=sev, category=cat, title=title, description="d",
                 file_path=file_path, line_number=line)


def make_result(name, status=ResultStatus.SUCCESS, issues=None):
    return AnalysisResult(analyzer_name=name, analyzer_version="1.0",
                          status=status, issues=issues or [])


def make_report(issues=None, results=None):
    report = AnalysisReport(project_path=Path("/test"), timestamp=datetime.now())
    if results:
        report.results = results
    elif issues:
        r = make_result("test", issues=issues)
        report.results = [r]
    else:
        report.results = []
    return report


class TestDeduplicateIssues:
    """deduplicate_issues takes a list directly."""

    def test_no_duplicates_unchanged(self):
        issues = [
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "SQL", Path("a.py"), 10),
            make_issue(Severity.LOW, IssueCategory.STYLE, "Name", Path("b.py"), 5),
        ]
        assert len(ResultAggregator.deduplicate_issues(issues)) == 2

    def test_exact_duplicates_reduced_to_one(self):
        issues = [
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "SQL", Path("app.py"), 42),
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "SQL", Path("app.py"), 42),
        ]
        assert len(ResultAggregator.deduplicate_issues(issues)) == 1

    def test_different_line_not_deduped(self):
        issues = [
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "SQL", Path("a.py"), 42),
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "SQL", Path("a.py"), 43),
        ]
        assert len(ResultAggregator.deduplicate_issues(issues)) == 2

    def test_different_severity_not_deduped(self):
        issues = [
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "SQL", Path("a.py"), 42),
            make_issue(Severity.MEDIUM, IssueCategory.SECURITY, "SQL", Path("a.py"), 42),
        ]
        assert len(ResultAggregator.deduplicate_issues(issues)) == 2

    def test_different_file_not_deduped(self):
        issues = [
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "SQL", Path("a.py"), 42),
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "SQL", Path("b.py"), 42),
        ]
        assert len(ResultAggregator.deduplicate_issues(issues)) == 2

    def test_three_duplicates_become_one(self):
        issues = [
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "SQL", Path("a.py"), 1)
            for _ in range(3)
        ]
        assert len(ResultAggregator.deduplicate_issues(issues)) == 1

    def test_empty_list_returns_empty(self):
        assert ResultAggregator.deduplicate_issues([]) == []

    def test_no_file_path_deduped_by_title(self):
        issues = [
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "API key exposed"),
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "API key exposed"),
        ]
        assert len(ResultAggregator.deduplicate_issues(issues)) == 1


class TestGroupIssuesBySeverity:
    """group_issues_by_severity takes an AnalysisReport."""

    def test_groups_by_severity(self):
        issues = [
            make_issue(Severity.CRITICAL, IssueCategory.SECURITY, "C"),
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "H1"),
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "H2"),
            make_issue(Severity.LOW, IssueCategory.STYLE, "L"),
        ]
        report = make_report(issues=issues)
        grouped = ResultAggregator.group_issues_by_severity(report)
        assert len(grouped[Severity.CRITICAL]) == 1
        assert len(grouped[Severity.HIGH]) == 2
        assert len(grouped[Severity.LOW]) == 1

    def test_empty_report_all_groups_empty(self):
        report = make_report()
        grouped = ResultAggregator.group_issues_by_severity(report)
        assert all(len(v) == 0 for v in grouped.values())

    def test_all_severities_present_in_result(self):
        report = make_report()
        grouped = ResultAggregator.group_issues_by_severity(report)
        assert Severity.CRITICAL in grouped
        assert Severity.HIGH in grouped
        assert Severity.MEDIUM in grouped
        assert Severity.LOW in grouped


class TestGetTopIssues:
    """get_top_issues(report, limit=10)  returns highest severity first."""

    def test_returns_at_most_limit_issues(self):
        issues = [make_issue(Severity.LOW, IssueCategory.STYLE, f"I{i}")
                  for i in range(20)]
        report = make_report(issues=issues)
        top = ResultAggregator.get_top_issues(report, limit=5)
        assert len(top) == 5

    def test_critical_first(self):
        issues = [
            make_issue(Severity.LOW, IssueCategory.STYLE, "Low"),
            make_issue(Severity.CRITICAL, IssueCategory.SECURITY, "Critical"),
            make_issue(Severity.HIGH, IssueCategory.SECURITY, "High"),
        ]
        report = make_report(issues=issues)
        top = ResultAggregator.get_top_issues(report, limit=3)
        assert top[0].severity == Severity.CRITICAL

    def test_fewer_than_limit_returns_all(self):
        issues = [make_issue(Severity.HIGH, IssueCategory.SECURITY, f"I{i}")
                  for i in range(3)]
        report = make_report(issues=issues)
        top = ResultAggregator.get_top_issues(report, limit=10)
        assert len(top) == 3

    def test_empty_report_returns_empty(self):
        report = make_report()
        top = ResultAggregator.get_top_issues(report, limit=10)
        assert top == []

    def test_default_limit(self):
        issues = [make_issue(Severity.HIGH, IssueCategory.SECURITY, f"I{i}")
                  for i in range(15)]
        report = make_report(issues=issues)
        top = ResultAggregator.get_top_issues(report)
        assert len(top) == 10  # default limit=10


class TestMergeResults:
    """merge_results(results_list)  merges multiple AnalysisResult objects."""

    def test_merge_combines_issues(self):
        r1 = make_result("security",
                         issues=[make_issue(Severity.HIGH, IssueCategory.SECURITY, "S1")])
        r2 = make_result("security",
                         issues=[make_issue(Severity.LOW, IssueCategory.SECURITY, "S2")])
        merged = ResultAggregator.merge_results([r1, r2])
        assert len(merged.issues) == 2

    def test_merge_empty_raises(self):
        with pytest.raises((ValueError, IndexError, Exception)):
            ResultAggregator.merge_results([])

    def test_merge_single_unchanged(self):
        r = make_result("security",
                        issues=[make_issue(Severity.HIGH, IssueCategory.SECURITY, "I")])
        merged = ResultAggregator.merge_results([r])
        assert len(merged.issues) == 1

    def test_merged_result_has_correct_analyzer_name(self):
        r1 = make_result("security")
        r2 = make_result("security")
        merged = ResultAggregator.merge_results([r1, r2])
        assert merged.analyzer_name == "security"
