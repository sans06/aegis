"""Script to generate demo reports with sample data."""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import asyncio
from datetime import datetime
from pathlib import Path

from rich.console import Console

from synexian.config import Config
from synexian.constants import Grade, Severity, IssueCategory, ResultStatus
from synexian.models import (
    AnalysisReport,
    AnalysisResult,
    Issue,
    MetricValue,
    SummaryStats,
)
from synexian.reports.json_reporter import JSONReporter
from synexian.reports.html_reporter import HTMLReporter


console = Console()


def create_sample_report():
    """Create a sample analysis report with demo data."""

    # Create sample issues
    issues1 = [
        Issue(
            severity=Severity.HIGH,
            category=IssueCategory.SECURITY,
            title="Potential SQL Injection",
            description="User input is directly concatenated into SQL query",
            file_path=Path("src/database.py"),
            line_number=42,
            suggestion="Use parameterized queries instead",
            rule_id="SEC001",
        ),
        Issue(
            severity=Severity.MEDIUM,
            category=IssueCategory.COMPLEXITY,
            title="High Cyclomatic Complexity",
            description="Function has cyclomatic complexity of 15",
            file_path=Path("src/utils.py"),
            line_number=102,
            suggestion="Break down into smaller functions",
            rule_id="COMP001",
        ),
    ]

    issues2 = [
        Issue(
            severity=Severity.LOW,
            category=IssueCategory.STYLE,
            title="PEP8 Violation: Line too long",
            description="Line exceeds 100 characters",
            file_path=Path("src/main.py"),
            line_number=25,
            rule_id="E501",
        ),
    ]

    # Create analysis results
    result1 = AnalysisResult(
        analyzer_name="security",
        analyzer_version="1.0.0",
        status=ResultStatus.SUCCESS,
        metrics={
            "total_issues": MetricValue("total_issues", 2),
            "high_severity": MetricValue("high_severity", 1, threshold=5),
        },
        issues=issues1,
        execution_time_seconds=2.5,
    )

    result2 = AnalysisResult(
        analyzer_name="style",
        analyzer_version="1.0.0",
        status=ResultStatus.SUCCESS,
        metrics={
            "violations_per_kloc": MetricValue("violations_per_kloc", 8.5, threshold=10),
        },
        issues=issues2,
        execution_time_seconds=1.2,
    )

    result3 = AnalysisResult(
        analyzer_name="complexity",
        analyzer_version="1.0.0",
        status=ResultStatus.SUCCESS,
        metrics={
            "average_complexity": MetricValue("average_complexity", 6.2, threshold=10),
            "max_complexity": MetricValue("max_complexity", 15),
        },
        issues=[],
        execution_time_seconds=1.8,
    )

    # Create summary stats
    summary = SummaryStats(
        total_files=15,
        total_lines=2543,
        total_issues=3,
        critical_issues=0,
        high_issues=1,
        medium_issues=1,
        low_issues=1,
        info_issues=0,
        execution_time_seconds=5.5,
        analyzers_run=3,
        analyzers_failed=0,
    )

    # Create full report
    report = AnalysisReport(
        project_path=Path("/demo/project"),
        timestamp=datetime.now(),
        results=[result1, result2, result3],
        overall_score=87.5,
        grade=Grade.B,
        summary_stats=summary,
        execution_time_seconds=5.5,
    )

    return report


async def main():
    """Generate demo reports."""
    console.print("\n[bold blue]Generating Demo Reports[/bold blue]\n")

    # Create sample report
    report = create_sample_report()

    # Create output directory
    output_dir = Path.cwd() / "demo-reports"
    output_dir.mkdir(exist_ok=True)

    # Generate JSON report
    console.print("[yellow]Generating JSON report...[/yellow]")
    json_reporter = JSONReporter(output_dir)
    json_path = json_reporter.generate(report)
    console.print(f"[green] JSON report: {json_path}[/green]")

    # Generate HTML report
    console.print("[yellow]Generating HTML report...[/yellow]")
    html_reporter = HTMLReporter(output_dir)
    html_path = html_reporter.generate(report)
    console.print(f"[green] HTML report: {html_path}[/green]")

    console.print(f"\n[bold green]Demo reports generated in: {output_dir}[/bold green]\n")


if __name__ == "__main__":
    asyncio.run(main())
