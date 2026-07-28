"""CLI application for Aegis Agent using Typer and Rich"""

#=====================================
# © 2026 Synexian Labs Private Limited
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
        # FIX CR-06 / H-06: Separate hard errors from API-key-only warnings.
        # Previously, a missing API key produced a hard error that prevented
        # even static-only analysis (which needs no API key).
        all_errors = config.validate()
        # Separate API key "errors" (should be warnings) from real errors
        api_key_messages = [e for e in all_errors if "api key" in e.lower() or "openrouter" in e.lower()]
        hard_errors = [e for e in all_errors if e not in api_key_messages]

        # API key missing → warning only (static analyzers still run)
        if api_key_messages:
            console.print("[yellow]⚠ Warning: No OpenRouter API key — AI-powered analyzers will be skipped.[/yellow]")

        errors = hard_errors
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
        if (lambda cfg=config.analyzers.get("complexity"): cfg is not None and cfg.enabled)():  # FIX CR-07
            analyzers.append(ComplexityAnalyzer(config.analyzers["complexity"]))

        # Add security analyzer
        if (lambda cfg=config.analyzers.get("security"): cfg is not None and cfg.enabled)():  # FIX CR-07
            analyzers.append(SecurityAnalyzer(config.analyzers["security"]))

        # Add style analyzer
        if (lambda cfg=config.analyzers.get("style"): cfg is not None and cfg.enabled)():  # FIX CR-07
            analyzers.append(StyleAnalyzer(config.analyzers["style"]))

        # Add architecture analyzer (AI-powered)
        if (lambda cfg=config.analyzers.get("architecture"): cfg is not None and cfg.enabled)():  # FIX CR-07
            analyzers.append(ArchitectureAnalyzer(config.analyzers["architecture"], ai_client))

        # Add edge cases analyzer (AI-powered)
        if (lambda cfg=config.analyzers.get("edge_cases"): cfg is not None and cfg.enabled)():  # FIX CR-07
            analyzers.append(EdgeCaseAnalyzer(config.analyzers["edge_cases"], ai_client))

        # Add test quality analyzer
        if (lambda cfg=config.analyzers.get("test_quality"): cfg is not None and cfg.enabled)():  # FIX CR-07
            analyzers.append(TestQualityAnalyzer(config.analyzers["test_quality"]))

        # Add cognitive load analyzer
        if (lambda cfg=config.analyzers.get("cognitive_load"): cfg is not None and cfg.enabled)():  # FIX CR-07
            analyzers.append(CognitiveLoadAnalyzer(config.analyzers["cognitive_load"]))

        # Add custom rules analyzer
        if (lambda cfg=config.analyzers.get("custom_rules"): cfg is not None and cfg.enabled)():  # FIX CR-07
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
            console.print(f"\n[green]✓ JSON report saved to:[/green] {json_path}")

        if "html" in config.output_formats:
            html_reporter = HTMLReporter(config.output_dir)
            html_path = html_reporter.generate(report)
            console.print(f"[green]✓ HTML report saved to:[/green] {html_path}")

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


if __name__ == "__main__":
    app()
