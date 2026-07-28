#!/usr/bin/env python3
"""
Aegis Self-Improvement Script
==============================

Runs Aegis on its own source code, reads the JSON report, identifies
automatically fixable issues, applies fixes, then re-runs to show improvement.

This is an example of AI-assisted code quality automation — a tool using
its own output to improve itself.

Usage:
    python scripts/self_improve.py
    python scripts/self_improve.py --dry-run      # show what would be fixed
    python scripts/self_improve.py --target-score 70  # stop when score >= 70
    python scripts/self_improve.py --fix security  # fix only security issues
"""

import ast
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aegis.self_improve")

# ── Constants ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_DIR = PROJECT_ROOT / "synexian"
REPORT_DIR = PROJECT_ROOT / "synexian-reports"
SELF_IMPROVE_REPORT = REPORT_DIR / "self_improve_report.json"
BACKUP_DIR = PROJECT_ROOT / ".self_improve_backup"

FIXABLE_CATEGORIES = {
    "docstrings": "Add missing docstrings to public functions and classes",
    "type_hints": "Add basic type hints to function signatures",
    "bare_except": "Replace bare except: with except Exception:",
    "debug_flags": "Disable DEBUG=True flags",
    "unused_imports": "Remove unused import statements",
    "trailing_whitespace": "Fix trailing whitespace in all files",
}


# ── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class AnalysisDelta:
    """Tracks score improvement between two runs."""
    before_score: float
    after_score: float
    before_grade: str
    after_grade: str
    fixes_applied: int
    files_modified: int

    @property
    def improvement(self) -> float:
        return self.after_score - self.before_score

    @property
    def improved(self) -> bool:
        return self.after_score > self.before_score


@dataclass
class Fix:
    """A single automated fix to apply."""
    file_path: Path
    line_number: Optional[int]
    category: str
    description: str
    original: str
    replacement: str


# ── Analysis Runner ───────────────────────────────────────────────────────────
def run_analysis(target: str = ".", output_formats: str = "json") -> Optional[Dict]:
    """Run Aegis on target path and return the JSON report."""
    report_path = REPORT_DIR / "report.json"

    logger.info(f"Running Aegis analysis on: {target}")
    result = subprocess.run(
        [
            sys.executable, "-m", "synexian.cli", "analyze",
            target,
            "--output", output_formats,
            "--config", str(PROJECT_ROOT / "synexian.yaml"),
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    if not report_path.exists():
        # Try CLI directly
        result = subprocess.run(
            ["synexian", "analyze", target, "--output", output_formats],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )

    if report_path.exists():
        with open(report_path, encoding="utf-8") as f:
            return json.load(f)

    logger.error("Analysis failed — no report generated")
    logger.error(result.stderr[-500:] if result.stderr else "No error output")
    return None


def get_score_and_grade(report: Dict) -> Tuple[float, str]:
    """Extract score and grade from a report dict."""
    score = report.get("overall_score", 0.0)
    grade = report.get("grade", "F")
    return score, grade


# ── Fix Finders ───────────────────────────────────────────────────────────────
def find_missing_docstrings(source_dir: Path) -> List[Fix]:
    """Find public functions and classes missing docstrings."""
    fixes = []

    for py_file in source_dir.rglob("*.py"):
        if any(p in str(py_file) for p in ["__pycache__", "test_", "tests/"]):
            continue

        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (SyntaxError, OSError):
            continue

        lines = source.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue

            # Skip private functions (underscore prefix) and dunder methods
            if node.name.startswith("__") and node.name.endswith("__"):
                continue
            if node.name.startswith("_") and not node.name.startswith("__"):
                continue

            # Check if docstring exists
            has_docstring = (
                isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ) if node.body else False

            if not has_docstring:
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                fixes.append(Fix(
                    file_path=py_file,
                    line_number=node.lineno,
                    category="docstrings",
                    description=f"Missing docstring on {kind} '{node.name}'",
                    original=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                    replacement="",  # computed during apply
                ))

    return fixes


def find_bare_excepts(source_dir: Path) -> List[Fix]:
    """Find bare except: statements."""
    fixes = []
    pattern = re.compile(r"^(\s*)except\s*:\s*$")

    for py_file in source_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            lines = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for i, line in enumerate(lines, 1):
            match = pattern.match(line)
            if match:
                indent = match.group(1)
                fixes.append(Fix(
                    file_path=py_file,
                    line_number=i,
                    category="bare_except",
                    description=f"Bare except: at line {i}",
                    original=line,
                    replacement=f"{indent}except Exception:",
                ))

    return fixes


def find_debug_flags(source_dir: Path) -> List[Fix]:
    """Find DEBUG = True flags."""
    fixes = []
    patterns = [
        (re.compile(r"^(\s*)DEBUG\s*=\s*True"), "DEBUG = False"),
        (re.compile(r"^(\s*)debug\s*=\s*True"), "debug = False"),
    ]

    for py_file in source_dir.rglob("*.py"):
        if any(p in str(py_file) for p in ["__pycache__", "test_"]):
            continue

        try:
            lines = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for i, line in enumerate(lines, 1):
            for pattern, replacement_value in patterns:
                match = pattern.match(line)
                if match:
                    indent = match.group(1)
                    fixes.append(Fix(
                        file_path=py_file,
                        line_number=i,
                        category="debug_flags",
                        description=f"Debug flag enabled at line {i}",
                        original=line,
                        replacement=f"{indent}{replacement_value}",
                    ))

    return fixes


def find_trailing_whitespace(source_dir: Path) -> List[Fix]:
    """Find lines with trailing whitespace."""
    fixes = []

    for py_file in source_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            lines = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for i, line in enumerate(lines, 1):
            if line != line.rstrip():
                fixes.append(Fix(
                    file_path=py_file,
                    line_number=i,
                    category="trailing_whitespace",
                    description=f"Trailing whitespace at line {i}",
                    original=line,
                    replacement=line.rstrip(),
                ))

    return fixes


# ── Fix Appliers ──────────────────────────────────────────────────────────────
def backup_file(file_path: Path) -> None:
    """Create a backup of a file before modifying it."""
    relative = file_path.relative_to(PROJECT_ROOT)
    backup_path = BACKUP_DIR / relative
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, backup_path)


def apply_simple_replacement(fixes: List[Fix]) -> int:
    """Apply fixes that are simple line replacements."""
    # Group by file
    by_file: Dict[Path, List[Fix]] = {}
    for fix in fixes:
        by_file.setdefault(fix.file_path, []).append(fix)

    files_modified = 0

    for file_path, file_fixes in by_file.items():
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            modified = False

            # Apply in reverse order so line numbers don't shift
            for fix in sorted(file_fixes, key=lambda f: f.line_number or 0, reverse=True):
                if fix.line_number and fix.replacement:
                    idx = fix.line_number - 1
                    if 0 <= idx < len(lines) and lines[idx] == fix.original:
                        backup_file(file_path)
                        lines[idx] = fix.replacement
                        modified = True

            if modified:
                file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                files_modified += 1

        except OSError as e:
            logger.warning(f"Could not modify {file_path}: {e}")

    return files_modified


def apply_docstring_fixes(fixes: List[Fix]) -> int:
    """Add docstrings to functions/classes missing them."""
    by_file: Dict[Path, List[Fix]] = {}
    for fix in fixes:
        by_file.setdefault(fix.file_path, []).append(fix)

    files_modified = 0

    for file_path, file_fixes in by_file.items():
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
            lines = source.splitlines()
            insertions = []  # (line_index_to_insert_after, docstring_lines)

            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if node.name.startswith("_"):
                    continue

                has_docstring = (
                    isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ) if node.body else False

                if has_docstring:
                    continue

                # Find the indent of the body
                if node.body:
                    body_line = lines[node.body[0].lineno - 1] if node.body[0].lineno <= len(lines) else ""
                    indent = len(body_line) - len(body_line.lstrip())
                    indent_str = " " * indent
                else:
                    indent_str = "    "

                # Generate a simple docstring
                kind = "class" if isinstance(node, ast.ClassDef) else "method/function"
                docstring_lines = [
                    f'{indent_str}"""',
                    f'{indent_str}{node.name.replace("_", " ").strip()} {kind}.',
                    f'{indent_str}"""',
                ]

                # Insert after the def/class line (before the first body line)
                insert_after = node.body[0].lineno - 2 if node.body else node.lineno - 1
                insertions.append((insert_after, docstring_lines))

            if not insertions:
                continue

            # Apply insertions in reverse order
            backup_file(file_path)
            for insert_idx, docstring_lines in sorted(insertions, reverse=True):
                lines[insert_idx:insert_idx] = docstring_lines

            file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            files_modified += 1

        except (SyntaxError, OSError) as e:
            logger.warning(f"Could not add docstrings to {file_path}: {e}")

    return files_modified


def restore_backup() -> None:
    """Restore all files from backup (undo all changes)."""
    if not BACKUP_DIR.exists():
        logger.warning("No backup found — nothing to restore")
        return

    restored = 0
    for backup_file_path in BACKUP_DIR.rglob("*.py"):
        relative = backup_file_path.relative_to(BACKUP_DIR)
        original_path = PROJECT_ROOT / relative
        shutil.copy2(backup_file_path, original_path)
        restored += 1

    logger.info(f"Restored {restored} files from backup")


# ── Report Generation ─────────────────────────────────────────────────────────
def generate_improvement_report(
    before_report: Dict,
    after_report: Optional[Dict],
    all_fixes: List[Fix],
    applied_count: int,
    files_modified: int,
) -> None:
    """Generate a self-improvement summary report."""
    before_score, before_grade = get_score_and_grade(before_report)
    after_score, after_grade = get_score_and_grade(after_report) if after_report else (0, "F")

    improvement_report = {
        "generated_at": datetime.now().isoformat(),
        "description": "Aegis self-improvement run — tool analyzed and improved its own code",
        "before": {
            "score": before_score,
            "grade": before_grade,
            "total_issues": before_report.get("summary_stats", {}).get("total_issues", 0),
        },
        "after": {
            "score": after_score,
            "grade": after_grade,
            "total_issues": after_report.get("summary_stats", {}).get("total_issues", 0) if after_report else 0,
        },
        "improvement": {
            "score_delta": round(after_score - before_score, 2),
            "grade_changed": before_grade != after_grade,
            "fixes_found": len(all_fixes),
            "fixes_applied": applied_count,
            "files_modified": files_modified,
        },
        "fixes_by_category": {},
    }

    for fix in all_fixes:
        cat = fix.category
        if cat not in improvement_report["fixes_by_category"]:
            improvement_report["fixes_by_category"][cat] = {
                "description": FIXABLE_CATEGORIES.get(cat, cat),
                "count": 0,
                "files": [],
            }
        improvement_report["fixes_by_category"][cat]["count"] += 1
        fname = str(fix.file_path.relative_to(PROJECT_ROOT))
        if fname not in improvement_report["fixes_by_category"][cat]["files"]:
            improvement_report["fixes_by_category"][cat]["files"].append(fname)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SELF_IMPROVE_REPORT, "w", encoding="utf-8") as f:
        json.dump(improvement_report, f, indent=2)

    logger.info(f"Self-improvement report saved: {SELF_IMPROVE_REPORT}")


def print_summary(
    before_score: float, before_grade: str,
    after_score: float, after_grade: str,
    applied_count: int, files_modified: int,
) -> None:
    """Print a coloured summary to the terminal."""
    delta = after_score - before_score
    arrow = "▲" if delta > 0 else "▼" if delta < 0 else "→"
    delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"

    print()
    print("=" * 60)
    print("  AEGIS SELF-IMPROVEMENT SUMMARY")
    print("=" * 60)
    print(f"  Before:  {before_score:.1f}/100  Grade {before_grade}")
    print(f"  After:   {after_score:.1f}/100  Grade {after_grade}  {arrow} {delta_str} pts")
    print(f"  Fixes applied:   {applied_count}")
    print(f"  Files modified:  {files_modified}")
    print("=" * 60)

    if delta > 0:
        print(f"\n  ✅ Score improved by {delta_str} points!")
    elif delta == 0:
        print("\n  → Score unchanged. Manual fixes needed for further improvement.")
    else:
        print(f"\n  ⚠ Score decreased by {abs(delta):.1f} pts — review changes.")

    print(f"\n  Full report: {SELF_IMPROVE_REPORT}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    """Main entry point for the self-improvement script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Aegis Self-Improvement — analyze and auto-fix the Aegis codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without applying changes",
    )
    parser.add_argument(
        "--target-score",
        type=float,
        default=None,
        help="Stop improving once this score is reached",
    )
    parser.add_argument(
        "--fix",
        choices=list(FIXABLE_CATEGORIES.keys()),
        nargs="+",
        default=None,
        help="Apply only specific fix categories",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore all files to their state before self-improvement",
    )
    parser.add_argument(
        "--no-rerun",
        action="store_true",
        help="Apply fixes without re-running analysis afterwards",
    )
    args = parser.parse_args()

    # Handle restore
    if args.restore:
        restore_backup()
        return

    print()
    print("⚔️  AEGIS SELF-IMPROVEMENT")
    print("   Analyzing own codebase and applying automated fixes")
    print()

    # ── Step 1: Run initial analysis ──────────────────────────────────────────
    print("Step 1/4: Running initial analysis...")
    before_report = run_analysis(target=".", output_formats="json,cli")
    if not before_report:
        print("ERROR: Initial analysis failed. Make sure synexian is installed.")
        sys.exit(1)

    before_score, before_grade = get_score_and_grade(before_report)
    print(f"         Initial score: {before_score:.1f}/100  Grade: {before_grade}\n")

    if args.target_score and before_score >= args.target_score:
        print(f"✅ Already at target score ({args.target_score}). Nothing to do.")
        return

    # ── Step 2: Find all fixable issues ──────────────────────────────────────
    print("Step 2/4: Scanning for automatically fixable issues...")

    all_fixes: List[Fix] = []

    active_categories = args.fix or list(FIXABLE_CATEGORIES.keys())

    if "docstrings" in active_categories:
        docstring_fixes = find_missing_docstrings(SOURCE_DIR)
        logger.info(f"  Found {len(docstring_fixes)} missing docstrings")
        all_fixes.extend(docstring_fixes)

    if "bare_except" in active_categories:
        except_fixes = find_bare_excepts(SOURCE_DIR)
        logger.info(f"  Found {len(except_fixes)} bare except: statements")
        all_fixes.extend(except_fixes)

    if "debug_flags" in active_categories:
        debug_fixes = find_debug_flags(SOURCE_DIR)
        logger.info(f"  Found {len(debug_fixes)} debug flags")
        all_fixes.extend(debug_fixes)

    if "trailing_whitespace" in active_categories:
        ws_fixes = find_trailing_whitespace(SOURCE_DIR)
        logger.info(f"  Found {len(ws_fixes)} trailing whitespace issues")
        all_fixes.extend(ws_fixes)

    print(f"         Total fixable issues found: {len(all_fixes)}\n")

    if not all_fixes:
        print("✅ No automatically fixable issues found. Manual review needed.")
        return

    # ── Step 3: Apply fixes ───────────────────────────────────────────────────
    if args.dry_run:
        print("Step 3/4: DRY RUN — showing what would be fixed:\n")
        by_category: Dict[str, List] = {}
        for fix in all_fixes:
            by_category.setdefault(fix.category, []).append(fix)
        for cat, cat_fixes in by_category.items():
            print(f"  [{cat}] {len(cat_fixes)} fixes")
            for fix in cat_fixes[:3]:  # show first 3 per category
                rel = str(fix.file_path.relative_to(PROJECT_ROOT))
                print(f"    - {rel}:{fix.line_number} — {fix.description}")
            if len(cat_fixes) > 3:
                print(f"    ... and {len(cat_fixes) - 3} more")
        print(f"\n  Run without --dry-run to apply {len(all_fixes)} fixes.")
        return

    print("Step 3/4: Applying fixes...")

    # Create backup directory
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Backup directory: {BACKUP_DIR}")

    applied_count = 0
    files_modified = 0

    # Apply bare except fixes
    bare_fixes = [f for f in all_fixes if f.category == "bare_except"]
    if bare_fixes:
        n = apply_simple_replacement(bare_fixes)
        files_modified += n
        applied_count += len(bare_fixes)
        logger.info(f"  Applied {len(bare_fixes)} bare except fixes across {n} files")

    # Apply debug flag fixes
    debug_fixes = [f for f in all_fixes if f.category == "debug_flags"]
    if debug_fixes:
        n = apply_simple_replacement(debug_fixes)
        files_modified += n
        applied_count += len(debug_fixes)
        logger.info(f"  Applied {len(debug_fixes)} debug flag fixes across {n} files")

    # Apply trailing whitespace fixes
    ws_fixes = [f for f in all_fixes if f.category == "trailing_whitespace"]
    if ws_fixes:
        n = apply_simple_replacement(ws_fixes)
        files_modified += n
        applied_count += len(ws_fixes)
        logger.info(f"  Applied {len(ws_fixes)} trailing whitespace fixes across {n} files")

    # Apply docstring fixes last (they insert lines which shifts line numbers)
    doc_fixes = [f for f in all_fixes if f.category == "docstrings"]
    if doc_fixes and "docstrings" in active_categories:
        n = apply_docstring_fixes(doc_fixes)
        files_modified += n
        applied_count += len(doc_fixes)
        logger.info(f"  Applied {len(doc_fixes)} docstring fixes across {n} files")

    print(f"         Applied {applied_count} fixes across {files_modified} files\n")

    # ── Step 4: Re-run analysis ───────────────────────────────────────────────
    if args.no_rerun:
        print("Step 4/4: Skipped (--no-rerun)")
        generate_improvement_report(before_report, None, all_fixes, applied_count, files_modified)
        return

    print("Step 4/4: Re-running analysis to measure improvement...")
    after_report = run_analysis(target=".", output_formats="json,cli,html")

    if after_report:
        after_score, after_grade = get_score_and_grade(after_report)
    else:
        after_score, after_grade = before_score, before_grade
        logger.warning("Re-analysis failed — showing before score")

    generate_improvement_report(
        before_report, after_report, all_fixes, applied_count, files_modified
    )

    print_summary(
        before_score, before_grade,
        after_score, after_grade,
        applied_count, files_modified,
    )

    if after_score > before_score:
        print("  Open ./synexian-reports/report.html to see the full improved report.")
        print("  Backup of original files saved to: .self_improve_backup/")
        print("  To undo all changes: python scripts/self_improve.py --restore")

    print()


if __name__ == "__main__":
    main()
