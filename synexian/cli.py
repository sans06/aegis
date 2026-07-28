"""CLI application for Aegis Agent using Typer and Rich"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import asyncio
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

from synexian.config import Config, load_config
from synexian.core.analyzer_engine import AnalyzerEngine
from synexian.utils.logger import configure_logging
from synexian.exceptions import ConfigurationError, SynexianError
from synexian.ai.client import AIClient
from synexian.core.cache_manager import CacheManager
from synexian.reports.json_reporter import JSONReporter
from synexian.reports.html_reporter import HTMLReporter
from synexian.reports.cli_reporter import CLIReporter
from synexian.input.local_directory import LocalDirectoryHandler
from synexian.input.single_file import SingleFileHandler
from synexian.input.github_repo import GitHubRepoHandler
from synexian.utils.validators import is_github_url

# Import all analyzers
from synexian.analyzers.complexity.analyzer import ComplexityAnalyzer
from synexian.analyzers.security.analyzer import SecurityAnalyzer
from synexian.analyzers.style.analyzer import StyleAnalyzer
from synexian.analyzers.architecture.analyzer import ArchitectureAnalyzer
from synexian.analyzers.edge_cases.analyzer import EdgeCaseAnalyzer
from synexian.analyzers.test_quality.analyzer import TestQualityAnalyzer
from synexian.analyzers.cognitive_load.analyzer import CognitiveLoadAnalyzer
from synexian.analyzers.custom_rules.analyzer import CustomRulesAnalyzer


app = typer.Typer(
    name="synexian",
    help="AI-powered software quality analysis CLI tool",
    add_completion=False,
)
console = Console()


@app.command()
def analyze(
    path: str = typer.Argument(
        ...,
        help="Path to analyze (local directory, file, or GitHub URL)",
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output formats (comma-separated: cli,json,html)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output",
    ),
):
    """Analyze a codebase for quality issues.

    Supports:
    - Local directories: ./my-project
    - Individual files: ./my-project/main.py
    - GitHub repositories: https://github.com/user/repo
    """
    try:
        # Configure logging
        verbosity = 2 if verbose else 1
        configure_logging(verbosity=verbosity)

        # Load configuration
        console.print("[bold blue]Loading configuration...[/bold blue]")
        config = load_config(config_file)

        # Override output formats if provided
        if output:
            config.output_formats = [fmt.strip() for fmt in output.split(",")]

        # Validate configuration
        errors = config.validate()
        if errors:
            console.print("[bold red]Configuration errors:[/bold red]")
            for error in errors:
                console.print(f"  - {error}")
            raise typer.Exit(1)

        # Determine input type and get files
        input_path = Path(path)
        files = []
        project_root = None
        input_handler = None

        if is_github_url(path):
            console.print("[bold blue]Cloning GitHub repository...[/bold blue]")
            input_handler = GitHubRepoHandler(
                url=path,
                file_patterns=config.file_patterns,
                ignore_patterns=config.ignore_patterns,
                max_file_size_kb=config.max_file_size_kb,
                github_token=config.github_token,
            )
            project_root = input_handler.prepare()
            files = input_handler.get_files()
        elif input_path.is_file():
            input_handler = SingleFileHandler(input_path)
            project_root = input_handler.prepare()
            files = input_handler.get_files()
        elif input_path.is_dir():
            input_handler = LocalDirectoryHandler(
                directory=input_path,
                file_patterns=config.file_patterns,
                ignore_patterns=config.ignore_patterns,
                max_file_size_kb=config.max_file_size_kb,
            )
            project_root = input_handler.prepare()
            files = input_handler.get_files()
        else:
            console.print(f"[bold red]Error:[/bold red] Path not found: {path}")
            raise typer.Exit(1)

        if not files:
            console.print("[bold yellow]No files found to analyze[/bold yellow]")
            if input_handler:
                input_handler.cleanup()
            raise typer.Exit(0)

        # Display analysis info
        console.print(f"\n[bold green]Analyzing {len(files)} files in {project_root}[/bold green]\n")

        # Initialize AI client if API key is available
        ai_client = None
        if config.openrouter_api_key:
            try:
                ai_client = AIClient(
                    api_key=config.openrouter_api_key,
                    base_url=config.openrouter_base_url,
                    model=config.model,
                )
            except Exception:
                console.print("[yellow]Warning: AI client initialization failed. AI-powered analyzers will be skipped.[/yellow]")

        # Initialize cache
        cache_manager = CacheManager(
            cache_dir=config.cache_dir,
            ttl_hours=config.cache_ttl_hours,
            enabled=config.cache_enabled,
        )

        # Create all analyzers
        analyzers = []

        # Add complexity analyzer
        if config.analyzers.get("complexity", {}).enabled:
            analyzers.append(ComplexityAnalyzer(config.analyzers["complexity"]))

        # Add security analyzer
        if config.analyzers.get("security", {}).enabled:
            analyzers.append(SecurityAnalyzer(config.analyzers["security"]))

        # Add style analyzer
        if config.analyzers.get("style", {}).enabled:
            analyzers.append(StyleAnalyzer(config.analyzers["style"]))

        # Add architecture analyzer (AI-powered)
        if config.analyzers.get("architecture", {}).enabled:
            analyzers.append(ArchitectureAnalyzer(config.analyzers["architecture"], ai_client))

        # Add edge cases analyzer (AI-powered)
        if config.analyzers.get("edge_cases", {}).enabled:
            analyzers.append(EdgeCaseAnalyzer(config.analyzers["edge_cases"], ai_client))

        # Add test quality analyzer
        if config.analyzers.get("test_quality", {}).enabled:
            analyzers.append(TestQualityAnalyzer(config.analyzers["test_quality"]))

        # Add cognitive load analyzer
        if config.analyzers.get("cognitive_load", {}).enabled:
            analyzers.append(CognitiveLoadAnalyzer(config.analyzers["cognitive_load"]))

        # Add custom rules analyzer
        if config.analyzers.get("custom_rules", {}).enabled:
            analyzers.append(CustomRulesAnalyzer(config.analyzers["custom_rules"]))

        # Create analyzer engine
        engine = AnalyzerEngine(config=config, analyzers=analyzers)

        # Run analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(description="Running analysis...", total=None)

            # Run async analysis
            report = asyncio.run(engine.run_analysis(project_root, files))

        # Display results (always show CLI output)
        if "cli" in config.output_formats or not config.output_formats:
            cli_reporter = CLIReporter()
            cli_reporter.display(report)

        # Generate reports
        if "json" in config.output_formats:
            json_reporter = JSONReporter(config.output_dir)
            json_path = json_reporter.generate(report)
            console.print(f"\n[green] JSON report saved to:[/green] {json_path}")

        if "html" in config.output_formats:
            html_reporter = HTMLReporter(config.output_dir)
            html_path = html_reporter.generate(report)
            console.print(f"[green] HTML report saved to:[/green] {html_path}")

        # Cleanup input handler
        if input_handler:
            input_handler.cleanup()

        # Exit with error code if critical issues found
        if report.has_critical_issues():
            raise typer.Exit(1)

    except ConfigurationError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        raise typer.Exit(1)
    except SynexianError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        if verbose:
            raise
        raise typer.Exit(1)


@app.command()
def config_show(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
    ),
):
    """Show current configuration."""
    try:
        config = load_config(config_file)
        console.print(Panel("[bold]Current Configuration[/bold]"))

        # Display configuration
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Value")

        config_dict = config.to_dict()
        for key, value in config_dict.items():
            if isinstance(value, dict):
                value = f"{len(value)} items"
            elif isinstance(value, list):
                value = f"{len(value)} items"
            table.add_row(key, str(value))

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    rprint("[bold blue]Synexian Agent[/bold blue] version [green]0.1.0[/green]")
    rprint("AI-powered software quality analysis tool")
    rprint("\nFor more information, visit: https://github.com/synexian/synexian-agent")


def _get_files_from_directory(directory: Path, config: Config) -> List[Path]:
    """Get all files from a directory matching configured patterns.

    Args:
        directory: Directory to scan
        config: Configuration with file patterns

    Returns:
        List of file paths
    """
    import pathspec

    files = []

    # Create pathspec for ignore patterns
    spec = pathspec.PathSpec.from_lines("gitwildmatch", config.ignore_patterns)

    # Find all Python files (simplified for now)
    for pattern in config.file_patterns:
        for file_path in directory.rglob(pattern.replace("**/", "")):
            if file_path.is_file():
                # Check if file should be ignored
                relative_path = file_path.relative_to(directory)
                if not spec.match_file(str(relative_path)):
                    # Check file size
                    size_kb = file_path.stat().st_size / 1024
                    if size_kb <= config.max_file_size_kb:
                        files.append(file_path)

    return files


def _display_report(report, config: Config):
    """Display analysis report to console.

    Args:
        report: Analysis report
        config: Configuration
    """
    # Display summary
    console.print("\n" + "=" * 80)
    console.print(Panel(
        f"[bold]Analysis Complete[/bold]\n\n"
        f"Grade: [bold]{_get_grade_color(report.grade)}{report.grade.value}[/bold] "
        f"({report.overall_score:.1f}/100)\n"
        f"Files: {report.summary_stats.total_files}\n"
        f"Lines: {report.summary_stats.total_lines:,}\n"
        f"Issues: {report.summary_stats.total_issues}\n"
        f"Time: {report.execution_time_seconds:.2f}s",
        title="Summary",
        border_style="green"
    ))

    # Display issues by severity
    if report.summary_stats.total_issues > 0:
        console.print("\n[bold]Issues by Severity:[/bold]")
        issues_table = Table(show_header=True, header_style="bold magenta")
        issues_table.add_column("Severity", style="cyan")
        issues_table.add_column("Count", justify="right")

        if report.summary_stats.critical_issues > 0:
            issues_table.add_row("CRITICAL", f"[red]{report.summary_stats.critical_issues}[/red]")
        if report.summary_stats.high_issues > 0:
            issues_table.add_row("HIGH", f"[orange_red1]{report.summary_stats.high_issues}[/orange_red1]")
        if report.summary_stats.medium_issues > 0:
            issues_table.add_row("MEDIUM", f"[yellow]{report.summary_stats.medium_issues}[/yellow]")
        if report.summary_stats.low_issues > 0:
            issues_table.add_row("LOW", f"[blue]{report.summary_stats.low_issues}[/blue]")
        if report.summary_stats.info_issues > 0:
            issues_table.add_row("INFO", f"[cyan]{report.summary_stats.info_issues}[/cyan]")

        console.print(issues_table)
    else:
        console.print("\n[bold green]No issues found![/bold green]")

    # Display analyzer results
    console.print("\n[bold]Analyzer Results:[/bold]")
    analyzers_table = Table(show_header=True, header_style="bold magenta")
    analyzers_table.add_column("Analyzer")
    analyzers_table.add_column("Status")
    analyzers_table.add_column("Issues", justify="right")
    analyzers_table.add_column("Time", justify="right")

    for result in report.results:
        status_color = "green" if result.status.value == "success" else "red"
        analyzers_table.add_row(
            result.analyzer_name,
            f"[{status_color}]{result.status.value}[/{status_color}]",
            str(len(result.issues)),
            f"{result.execution_time_seconds:.2f}s",
        )

    console.print(analyzers_table)
    console.print("=" * 80 + "\n")


def _get_grade_color(grade) -> str:
    """Get color for grade.

    Args:
        grade: Grade enum

    Returns:
        Rich color string
    """
    from synexian.constants import Grade

    if grade in [Grade.A_PLUS, Grade.A]:
        return "green"
    elif grade in [Grade.B_PLUS, Grade.B]:
        return "blue"
    elif grade in [Grade.C_PLUS, Grade.C]:
        return "yellow"
    else:
        return "red"


if __name__ == "__main__":
    app()
