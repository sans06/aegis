"""Aggregate results from multiple analyzers."""

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

from typing import Dict, List

from synexian.constants import IssueCategory, Severity
from synexian.models import AnalysisReport, AnalysisResult, Issue


class ResultAggregator:
    """Aggregate and deduplicate analysis results."""

    @staticmethod
    def deduplicate_issues(issues: List[Issue]) -> List[Issue]:
        """Remove duplicate issues.

        Args:
            issues: List of issues

        Returns:
            Deduplicated list
        """
        seen = set()
        unique_issues = []

        for issue in issues:
            # Create signature for deduplication
            signature = (
                issue.severity,
                issue.category,
                issue.title,
                issue.file_path,
                issue.line_number,
            )

            if signature not in seen:
                seen.add(signature)
                unique_issues.append(issue)

        return unique_issues

    @staticmethod
    def merge_results(results: List[AnalysisResult]) -> AnalysisResult:
        """Merge multiple results from the same analyzer.

        Args:
            results: List of results to merge

        Returns:
            Merged result
        """
        if not results:
            raise ValueError("No results to merge")

        if len(results) == 1:
            return results[0]

        # Start with first result
        merged = results[0]

        # Merge with rest
        for result in results[1:]:
            merged = merged.merge_with(result)

        return merged

    @staticmethod
    def group_issues_by_severity(report: AnalysisReport) -> Dict[Severity, List[Issue]]:
        """Group issues by severity level.

        Args:
            report: Analysis report

        Returns:
            Dictionary mapping severity to issues
        """
        groups = {severity: [] for severity in Severity}

        for issue in report.get_all_issues():
            groups[issue.severity].append(issue)

        return groups

    @staticmethod
    def group_issues_by_category(report: AnalysisReport) -> Dict[IssueCategory, List[Issue]]:
        """Group issues by category.

        Args:
            report: Analysis report

        Returns:
            Dictionary mapping category to issues
        """
        groups = {category: [] for category in IssueCategory}

        for issue in report.get_all_issues():
            groups[issue.category].append(issue)

        return groups

    @staticmethod
    def get_top_issues(report: AnalysisReport, limit: int = 10) -> List[Issue]:
        """Get top N most critical issues.

        Args:
            report: Analysis report
            limit: Number of issues to return

        Returns:
            List of top issues
        """
        all_issues = report.get_all_issues()

        # Sort by severity (CRITICAL first)
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }

        sorted_issues = sorted(
            all_issues,
            key=lambda i: severity_order.get(i.severity, 999)
        )

        return sorted_issues[:limit]
