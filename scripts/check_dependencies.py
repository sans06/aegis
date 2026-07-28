""" Script to check if all required dependencies are installed."""

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

import importlib
import sys

from rich.console import Console
from rich.table import Table


console = Console()


REQUIRED_PACKAGES = {
    "Core": [
        ("typer", "Typer"),
        ("rich", "Rich"),
        ("click", "Click"),
    ],
    "AI": [
        ("openai", "OpenAI"),
        ("httpx", "HTTPX"),
        ("tenacity", "Tenacity"),
    ],
    "Code Analysis": [
        ("radon", "Radon"),
        ("bandit", "Bandit"),
        ("flake8", "Flake8"),
    ],
    "Configuration": [
        ("dotenv", "Python-dotenv"),
        ("yaml", "PyYAML"),
        ("pydantic", "Pydantic"),
    ],
    "Git": [
        ("git", "GitPython"),
    ],
    "Utilities": [
        ("jinja2", "Jinja2"),
        ("markdown", "Markdown"),
        ("pygments", "Pygments"),
        ("pathspec", "Pathspec"),
    ],
}


def check_package(module_name, display_name):
    """Check if a package is installed."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def main():
    """Check all dependencies."""
    console.print("\n[bold blue]Synexian Agent Dependency Check[/bold blue]\n")

    all_ok = True

    for category, packages in REQUIRED_PACKAGES.items():
        table = Table(title=f"\n{category} Dependencies", show_header=True)
        table.add_column("Package", style="cyan")
        table.add_column("Status", style="green")

        for module_name, display_name in packages:
            is_installed = check_package(module_name, display_name)

            if is_installed:
                status = "[green]✓ Installed[/green]"
            else:
                status = "[red]✗ Missing[/red]"
                all_ok = False

            table.add_row(display_name, status)

        console.print(table)

    if all_ok:
        console.print("\n[bold green]✓ All dependencies are installed![/bold green]\n")
        return 0
    else:
        console.print("\n[bold red]✗ Some dependencies are missing![/bold red]")
        console.print("[yellow]Run: pip install -e .[/yellow]\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
