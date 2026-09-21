"""Benchmark script to measure Aegis's performance."""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential


import asyncio
import time
from pathlib import Path
from statistics import mean, median

from rich.console import Console
from rich.table import Table

from synexian.analyzers.complexity.analyzer import ComplexityAnalyzer
from synexian.analyzers.security.analyzer import SecurityAnalyzer
from synexian.analyzers.style.analyzer import StyleAnalyzer
from synexian.analyzers.base import AnalysisContext
from synexian.config import AnalyzerConfig


console = Console()


async def benchmark_analyzer(analyzer, files, iterations=3):
    """Benchmark a single analyzer."""
    times = []

    context = AnalysisContext(
        project_root=files[0].parent if files else Path.cwd(),
        files=files,
        config=AnalyzerConfig(),
    )

    for i in range(iterations):
        start = time.time()
        await analyzer.analyze(context)
        elapsed = time.time() - start
        times.append(elapsed)

    return {
        "mean": mean(times),
        "median": median(times),
        "min": min(times),
        "max": max(times),
    }


async def main():
    """Run benchmarks."""
    console.print("\n[bold blue]Synexian Agent Performance Benchmark[/bold blue]\n")

    # Find Python files in current directory
    files = list(Path.cwd().rglob("*.py"))[:20]  # Limit to 20 files

    if not files:
        console.print("[red]No Python files found in current directory[/red]")
        return

    console.print(f"[green]Benchmarking with {len(files)} files[/green]\n")

    analyzers = [
        ("Complexity", ComplexityAnalyzer(AnalyzerConfig())),
        ("Security", SecurityAnalyzer(AnalyzerConfig())),
        ("Style", StyleAnalyzer(AnalyzerConfig())),
    ]

    results = {}

    for name, analyzer in analyzers:
        console.print(f"[yellow]Benchmarking {name} Analyzer...[/yellow]")
        try:
            result = await benchmark_analyzer(analyzer, files)
            results[name] = result
            console.print(f"[green] {name} completed[/green]")
        except Exception as e:
            console.print(f"[red] {name} failed: {e}[/red]")
            results[name] = None

    # Display results table
    table = Table(title="\nBenchmark Results", show_header=True, header_style="bold magenta")
    table.add_column("Analyzer", style="cyan")
    table.add_column("Mean (s)", justify="right")
    table.add_column("Median (s)", justify="right")
    table.add_column("Min (s)", justify="right")
    table.add_column("Max (s)", justify="right")

    for name, result in results.items():
        if result:
            table.add_row(
                name,
                f"{result['mean']:.3f}",
                f"{result['median']:.3f}",
                f"{result['min']:.3f}",
                f"{result['max']:.3f}",
            )
        else:
            table.add_row(name, "FAILED", "-", "-", "-")

    console.print(table)

    # Calculate total time
    total_mean = sum(r["mean"] for r in results.values() if r)
    console.print(f"\n[bold]Total mean time: {total_mean:.3f}s[/bold]")
    console.print(f"[bold]Files per second: {len(files) / total_mean:.2f}[/bold]\n")


if __name__ == "__main__":
    asyncio.run(main())
