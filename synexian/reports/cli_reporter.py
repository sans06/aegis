"""CLI reporter with comprehensive metrics display """

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

from pathlib import Path
from typing import Dict, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.layout import Layout
from rich.text import Text
from rich.rule import Rule
from rich.tree import Tree
from rich import box

from synexian.models import AnalysisReport, AnalysisResult, MetricValue
from synexian.constants import Grade, Severity
from synexian.reports.base import BaseReporter


class CLIReporter(BaseReporter):
    """State-of-the-art CLI reporter with rich formatting.

    Displays comprehensive analysis results with:
    - Beautiful tables with borders and colors
    - ALL metrics from each analyzer
    - Issue breakdowns
    - Insights and recommendations
    - Visual progress indicators
    """

    def __init__(self):
        """Initialize CLI reporter."""
        self.console = Console()

    def generate(self, report: AnalysisReport) -> Path:
        """Display report to console (returns dummy path).

        Args:
            report: Analysis report

        Returns:
            Dummy path (CLI output goes to console)
        """
        self.display(report)
        return Path("-")  # Dummy path for CLI output

    def display(self, report: AnalysisReport):
        """Display comprehensive report to console.

        Args:
            report: Analysis report
        """
        self.console.print()  # Blank line

        # Header
        self._display_header(report)

        # Summary dashboard
        self._display_summary_dashboard(report)

        # Issues by severity
        if report.summary_stats.total_issues > 0:
            self._display_issues_breakdown(report)

        # Analyzer results with metrics
        self._display_analyzer_results(report)

        # Top issues
        if report.summary_stats.total_issues > 0:
            self._display_top_issues(report)

        # Insights summary
        self._display_insights(report)

        # Footer
        self._display_footer(report)

    def _display_header(self, report: AnalysisReport):
        """Display report header with logo and title."""
        header_text = Text()
        header_text.append("\n", style="bold cyan")
        header_text.append("  ", style="bold cyan")
        header_text.append(" SYNEXIAN AGENT", style="bold white")
        header_text.append(" - Software Quality Analysis Report", style="bold cyan")
        header_text.append("                 \n", style="bold cyan")
        header_text.append("", style="bold cyan")

        self.console.print(header_text)
        self.console.print()

    def _display_summary_dashboard(self, report: AnalysisReport):
        """Display comprehensive summary dashboard with detailed metrics."""
        stats = report.summary_stats

        # === Row 1: Main Quality Indicators ===
        grade_color = self._get_grade_color(report.grade)
        grade_style = f"bold {grade_color}"

        grade_panel = Panel(
            f"[{grade_style}]{report.grade.value}[/{grade_style}]",
            title="[bold]Grade[/bold]",
            border_style=grade_color,
            padding=(1, 2),
        )

        score_color = "green" if report.overall_score >= 80 else "yellow" if report.overall_score >= 60 else "red"
        score_panel = Panel(
            f"[bold {score_color}]{report.overall_score:.1f}/100[/bold {score_color}]",
            title="[bold]Overall Score[/bold]",
            border_style=score_color,
            padding=(1, 2),
        )

        # Files panel with breakdown
        files_content = f"[bold cyan]{stats.total_files:,}[/bold cyan]"
        if stats.total_python_files > 0:
            files_content += f"\n[dim]{stats.total_python_files} Python[/dim]"
        if stats.total_test_files > 0:
            files_content += f"\n[dim]{stats.total_test_files} Tests[/dim]"

        files_panel = Panel(
            files_content,
            title="[bold]Files Analyzed[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )

        # Lines panel
        lines_panel = Panel(
            f"[bold magenta]{stats.total_lines:,}[/bold magenta]",
            title="[bold]Total Lines[/bold]",
            border_style="magenta",
            padding=(1, 2),
        )

        # Issues panel
        issues_color = "red" if stats.critical_issues > 0 else "yellow" if stats.high_issues > 0 else "green"
        issues_panel = Panel(
            f"[bold {issues_color}]{stats.total_issues}[/bold {issues_color}]",
            title="[bold]Total Issues[/bold]",
            border_style=issues_color,
            padding=(1, 2),
        )

        # Time panel
        time_panel = Panel(
            f"[bold blue]{report.execution_time_seconds:.2f}s[/bold blue]",
            title="[bold]Execution Time[/bold]",
            border_style="blue",
            padding=(1, 2),
        )

        self.console.print(
            Columns([grade_panel, score_panel, files_panel, lines_panel, issues_panel, time_panel])
        )
        self.console.print()

        # === Row 2: Code Structure Metrics ===
        if stats.total_functions > 0 or stats.total_classes > 0:
            # Functions panel
            functions_panel = Panel(
                f"[bold green]{stats.total_functions:,}[/bold green]",
                title="[bold]Functions[/bold]",
                border_style="green",
                padding=(1, 2),
            )

            # Classes panel
            classes_panel = Panel(
                f"[bold yellow]{stats.total_classes:,}[/bold yellow]",
                title="[bold]Classes[/bold]",
                border_style="yellow",
                padding=(1, 2),
            )

            # Methods panel
            methods_panel = Panel(
                f"[bold blue]{stats.total_methods:,}[/bold blue]",
                title="[bold]Methods[/bold]",
                border_style="blue",
                padding=(1, 2),
            )

            # Avg Complexity panel
            complexity_color = "green" if stats.avg_cyclomatic_complexity < 5 else "yellow" if stats.avg_cyclomatic_complexity < 10 else "red"
            complexity_content = f"[bold {complexity_color}]{stats.avg_cyclomatic_complexity:.1f}[/bold {complexity_color}]"
            if stats.max_cyclomatic_complexity > 0:
                complexity_content += f"\n[dim]Max: {stats.max_cyclomatic_complexity}[/dim]"

            complexity_panel = Panel(
                complexity_content,
                title="[bold]Avg Complexity[/bold]",
                border_style=complexity_color,
                padding=(1, 2),
            )

            # Maintainability panel
            mi_color = "green" if stats.avg_maintainability_index >= 65 else "yellow" if stats.avg_maintainability_index >= 20 else "red"
            maintainability_panel = Panel(
                f"[bold {mi_color}]{stats.avg_maintainability_index:.1f}[/bold {mi_color}]",
                title="[bold]Maintainability[/bold]",
                border_style=mi_color,
                padding=(1, 2),
            )

            # Coverage panel (if available)
            if stats.code_coverage > 0:
                cov_color = "green" if stats.code_coverage >= 80 else "yellow" if stats.code_coverage >= 60 else "red"
                coverage_panel = Panel(
                    f"[bold {cov_color}]{stats.code_coverage:.1f}%[/bold {cov_color}]",
                    title="[bold]Test Coverage[/bold]",
                    border_style=cov_color,
                    padding=(1, 2),
                )
                self.console.print(
                    Columns([functions_panel, classes_panel, methods_panel, complexity_panel, maintainability_panel, coverage_panel])
                )
            else:
                self.console.print(
                    Columns([functions_panel, classes_panel, methods_panel, complexity_panel, maintainability_panel])
                )

            self.console.print()

    def _display_issues_breakdown(self, report: AnalysisReport):
        """Display issues breakdown by severity."""
        self.console.print(Rule("[bold]Issues by Severity", style="cyan"))
        self.console.print()

        issues_table = Table(
            show_header=True,
            header_style="bold white on blue",
            border_style="blue",
            box=box.ROUNDED,
            title="[bold cyan]Issue Severity Distribution[/bold cyan]",
            title_style="bold cyan",
        )

        issues_table.add_column("Severity", style="bold", width=12)
        issues_table.add_column("Count", justify="right", width=10)
        issues_table.add_column("Percentage", justify="right", width=12)
        issues_table.add_column("Visual", width=40)

        total = report.summary_stats.total_issues
        severities = [
            ("CRITICAL", report.summary_stats.critical_issues, "red"),
            ("HIGH", report.summary_stats.high_issues, "orange_red1"),
            ("MEDIUM", report.summary_stats.medium_issues, "yellow"),
            ("LOW", report.summary_stats.low_issues, "blue"),
            ("INFO", report.summary_stats.info_issues, "cyan"),
        ]

        for severity, count, color in severities:
            if count > 0:
                percentage = (count / total * 100) if total > 0 else 0
                bar_length = int(percentage / 2.5)  # Scale to 40 chars max
                bar = "" * bar_length

                issues_table.add_row(
                    f"[{color}]{severity}[/{color}]",
                    f"[{color}]{count}[/{color}]",
                    f"[{color}]{percentage:.1f}%[/{color}]",
                    f"[{color}]{bar}[/{color}]"
                )

        self.console.print(issues_table)
        self.console.print()

    def _display_analyzer_results(self, report: AnalysisReport):
        """Display detailed analyzer results with ALL metrics."""
        self.console.print(Rule("[bold]Analyzer Results & Metrics", style="green"))
        self.console.print()

        for result in report.results:
            self._display_single_analyzer(result)
            self.console.print()

    def _display_single_analyzer(self, result: AnalysisResult):
        """Display single analyzer result with all metrics.

        Args:
            result: Analyzer result
        """
        # Analyzer header
        status_icon = "" if result.status.value == "success" else ""
        status_color = "green" if result.status.value == "success" else "red"

        title = f"[bold white]{result.analyzer_name.upper()}[/bold white] [{status_color}]{status_icon} {result.status.value}[/{status_color}]"

        # Create main table
        table = Table(
            show_header=True,
            header_style="bold white on dark_blue",
            border_style="blue",
            box=box.DOUBLE_EDGE,
            title=title,
            title_style="bold cyan",
            expand=True,
        )

        table.add_column("Metric", style="cyan", width=35)
        table.add_column("Value", justify="right", width=15)
        table.add_column("Threshold", justify="right", width=15)
        table.add_column("Status", justify="center", width=10)

        # Add metrics
        if result.metrics:
            for metric_name, metric in result.metrics.items():
                value_str = self._format_metric_value(metric)
                threshold_str = self._format_threshold(metric)
                status_str = self._get_metric_status(metric)

                table.add_row(
                    metric.name.replace("_", " ").title(),
                    value_str,
                    threshold_str,
                    status_str,
                )
        else:
            table.add_row("[dim]No metrics available[/dim]", "-", "-", "-")

        self.console.print(table)

        # Display insights if available
        if result.insights:
            insights_text = Text()
            insights_text.append(" Insights: ", style="bold yellow")
            insights_text.append(" | ".join(result.insights), style="dim")
            self.console.print(insights_text)

        # Display issues count
        if result.issues:
            issues_by_severity = {}
            for issue in result.issues:
                severity = issue.severity.value
                issues_by_severity[severity] = issues_by_severity.get(severity, 0) + 1

            issues_summary = []
            for severity, count in sorted(issues_by_severity.items(), key=lambda x: {
                "CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4
            }.get(x[0], 5)):
                color = self._get_severity_color(severity)
                issues_summary.append(f"[{color}]{severity}: {count}[/{color}]")

            self.console.print(f"   Issues Found: {' | '.join(issues_summary)}")

    def _display_top_issues(self, report: AnalysisReport):
        """Display top critical and high severity issues."""
        self.console.print(Rule("[bold]Top Critical & High Severity Issues", style="red"))
        self.console.print()

        # Collect critical and high severity issues
        critical_high_issues = []
        for result in report.results:
            for issue in result.issues:
                if issue.severity in [Severity.CRITICAL, Severity.HIGH]:
                    critical_high_issues.append((result.analyzer_name, issue))

        if not critical_high_issues:
            self.console.print("[green] No critical or high severity issues found![/green]")
            self.console.print()
            return

        # Display ALL critical and high severity issues
        issues_table = Table(
            show_header=True,
            header_style="bold white on red",
            border_style="red",
            box=box.ROUNDED,
            expand=True,
        )

        issues_table.add_column("Severity", width=10)
        issues_table.add_column("Analyzer", width=15)
        issues_table.add_column("Issue", width=50)
        issues_table.add_column("Location", width=30)

        for analyzer_name, issue in critical_high_issues:
            severity_color = self._get_severity_color(issue.severity.value)
            location = f"{issue.file_path.name}:{issue.line_number}" if issue.file_path and issue.line_number else "-"

            issues_table.add_row(
                f"[{severity_color}]{issue.severity.value}[/{severity_color}]",
                analyzer_name,
                issue.title[:50],
                location,
            )

        self.console.print(issues_table)
        self.console.print()

    def _display_insights(self, report: AnalysisReport):
        """Display key insights from all analyzers."""
        self.console.print(Rule("[bold]Key Insights & Recommendations", style="yellow"))
        self.console.print()

        all_insights = []
        for result in report.results:
            if result.insights:
                for insight in result.insights:
                    all_insights.append((result.analyzer_name, insight))

        if not all_insights:
            self.console.print("[dim]No insights available[/dim]")
            self.console.print()
            return

        # Create tree of insights
        tree = Tree("[bold yellow] Analysis Insights[/bold yellow]")

        # Group by analyzer
        insights_by_analyzer = {}
        for analyzer, insight in all_insights:
            if analyzer not in insights_by_analyzer:
                insights_by_analyzer[analyzer] = []
            insights_by_analyzer[analyzer].append(insight)

        for analyzer, insights in insights_by_analyzer.items():
            analyzer_branch = tree.add(f"[bold cyan]{analyzer}[/bold cyan]")
            for insight in insights[:3]:  # Limit to 3 per analyzer
                analyzer_branch.add(f"[dim]{insight}[/dim]")

        self.console.print(tree)
        self.console.print()

    def _display_footer(self, report: AnalysisReport):
        """Display report footer."""
        version = report.results[0].analyzer_version if report.results else "0.1.0"
        footer = Panel(
            f"[dim]Report generated on {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n"
            f"[dim]Project: {report.project_path}[/dim]\n"
            f"[bold cyan] Generated by Synexian Agent v{version}[/bold cyan]",
            border_style="dim blue",
            padding=(1, 2),
        )

        self.console.print(footer)

    # Helper methods

    def _get_grade_color(self, grade: Grade) -> str:
        """Get color for grade."""
        if grade in [Grade.A_PLUS, Grade.A]:
            return "green"
        elif grade in [Grade.B_PLUS, Grade.B]:
            return "blue"
        elif grade in [Grade.C_PLUS, Grade.C]:
            return "yellow"
        elif grade == Grade.D:
            return "orange_red1"
        else:
            return "red"

    def _get_severity_color(self, severity: str) -> str:
        """Get color for severity."""
        severity_colors = {
            "CRITICAL": "red",
            "HIGH": "orange_red1",
            "MEDIUM": "yellow",
            "LOW": "blue",
            "INFO": "cyan",
        }
        return severity_colors.get(severity.upper(), "white")

    def _format_metric_value(self, metric: MetricValue) -> str:
        """Format metric value for display."""
        value = metric.value
        unit = metric.unit if hasattr(metric, 'unit') and metric.unit else ""

        if isinstance(value, float):
            return f"[bold white]{value:.2f}{unit}[/bold white]"
        else:
            return f"[bold white]{value}{unit}[/bold white]"

    def _format_threshold(self, metric: MetricValue) -> str:
        """Format threshold for display."""
        if metric.threshold is not None:
            return f"[dim] {metric.threshold}[/dim]"
        return "[dim]-[/dim]"

    def _get_metric_status(self, metric: MetricValue) -> str:
        """Get status indicator for metric."""
        if metric.passed is None:
            return "[dim]-[/dim]"
        elif metric.passed:
            return "[green][/green]"
        else:
            return "[red][/red]"
