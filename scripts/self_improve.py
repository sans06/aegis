#!/usr/bin/env python3
"""
Aegis Self-Improvement Script
==============================
Runs Aegis on its own source code, reads the JSON report, identifies
automatically fixable issues, applies fixes, then re-runs to show improvement.

Usage:
    python scripts/self_improve.py
    python scripts/self_improve.py --dry-run
    python scripts/self_improve.py --target-score 70
    python scripts/self_improve.py --restore
"""

import ast
import json
import logging
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aegis.self_improve")

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_DIR = PROJECT_ROOT / "synexian"
REPORT_DIR = PROJECT_ROOT / "synexian-reports"
SELF_IMPROVE_REPORT = REPORT_DIR / "self_improve_report.json"
BACKUP_DIR = PROJECT_ROOT / ".self_improve_backup"

FIXABLE_CATEGORIES = {
    "docstrings": "Add missing docstrings to public functions and classes",
    "bare_except": "Replace bare except: with except Exception:",
    "debug_flags": "Disable DEBUG=True flags",
    "trailing_whitespace": "Fix trailing whitespace in all files",
}


@dataclass
class Fix:
    """A single automated fix to apply."""
    file_path: Path
    line_number: Optional[int]
    category: str
    description: str
    original: str
    replacement: str


def run_analysis(target: str = ".") -> Optional[Dict]:
    """Run Aegis on target path and return the JSON report."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "report.json"

    if report_path.exists():
        report_path.unlink()

    logger.info(f"Running Aegis analysis on: {target}")

    cmd = ["synexian", "analyze", target, "--output", "json"]
    config_path = PROJECT_ROOT / "synexian.yaml"
    if config_path.exists():
        cmd.extend(["--config", str(config_path)])

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except FileNotFoundError:
        cmd = [sys.executable, "-m", "synexian.cli", "analyze", target, "--output", "json"]
        if config_path.exists():
            cmd.extend(["--config", str(config_path)])
        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
        except Exception as e:
            logger.error(f"Could not run synexian: {e}")
            return None
    except subprocess.TimeoutExpired:
        logger.error("Analysis timed out after 300 seconds")
        return None

    if report_path.exists():
        try:
            with open(report_path, encoding="utf-8", errors="replace") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Could not parse report: {e}")
            return None

    logger.error("Analysis failed - no report generated")
    return None


def get_score_and_grade(report: Dict) -> Tuple[float, str]:
    """Extract score and grade from a report dict."""
    return float(report.get("overall_score", 0.0)), str(report.get("grade", "F"))


def find_missing_docstrings(source_dir: Path) -> List[Fix]:
    """Find public functions and classes missing docstrings."""
    fixes = []
    skip = ["__pycache__", "test_", "tests/", "tests\\"]

    for py_file in source_dir.rglob("*.py"):
        if any(p in str(py_file) for p in skip):
            continue
        try:
            source = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
            lines = source.splitlines()
        except (SyntaxError, OSError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if node.name.startswith("_"):
                continue
            has_doc = (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )
            if not has_doc:
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                fixes.append(Fix(
                    file_path=py_file,
                    line_number=node.lineno,
                    category="docstrings",
                    description=f"Missing docstring on {kind} '{node.name}'",
                    original=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                    replacement="",
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
            m = pattern.match(line)
            if m:
                fixes.append(Fix(
                    file_path=py_file, line_number=i, category="bare_except",
                    description=f"Bare except: at line {i}",
                    original=line, replacement=f"{m.group(1)}except Exception:",
                ))
    return fixes


def find_debug_flags(source_dir: Path) -> List[Fix]:
    """Find DEBUG = True flags."""
    fixes = []
    patterns = [
        (re.compile(r"^(\s*)DEBUG\s*=\s*True\s*$"), "DEBUG = False"),
        (re.compile(r"^(\s*)debug\s*=\s*True\s*$"), "debug = False"),
    ]
    skip = ["__pycache__", "test_", "tests/", "tests\\"]
    for py_file in source_dir.rglob("*.py"):
        if any(p in str(py_file) for p in skip):
            continue
        try:
            lines = py_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for pat, rep in patterns:
                m = pat.match(line)
                if m:
                    fixes.append(Fix(
                        file_path=py_file, line_number=i, category="debug_flags",
                        description=f"Debug flag at line {i}",
                        original=line, replacement=f"{m.group(1)}{rep}",
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
            stripped = line.rstrip()
            if line != stripped:
                fixes.append(Fix(
                    file_path=py_file, line_number=i, category="trailing_whitespace",
                    description=f"Trailing whitespace at line {i}",
                    original=line, replacement=stripped,
                ))
    return fixes


def backup_file(file_path: Path) -> None:
    """Back up a file before modifying it."""
    try:
        rel = file_path.relative_to(PROJECT_ROOT)
        bp = BACKUP_DIR / rel
        bp.parent.mkdir(parents=True, exist_ok=True)
        if not bp.exists():
            shutil.copy2(file_path, bp)
    except Exception as e:
        logger.warning(f"Could not backup {file_path}: {e}")


def apply_simple_replacement(fixes: List[Fix]) -> Tuple[int, int]:
    """Apply simple line replacement fixes. Returns (files_modified, fixes_applied)."""
    by_file: Dict[Path, List[Fix]] = {}
    for fix in fixes:
        by_file.setdefault(fix.file_path, []).append(fix)

    files_modified = fixes_applied = 0
    for file_path, file_fixes in by_file.items():
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            modified = False
            for fix in sorted(file_fixes, key=lambda f: f.line_number or 0, reverse=True):
                if fix.line_number and fix.replacement is not None:
                    idx = fix.line_number - 1
                    if 0 <= idx < len(lines) and lines[idx] == fix.original:
                        backup_file(file_path)
                        lines[idx] = fix.replacement
                        modified = True
                        fixes_applied += 1
            if modified:
                file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                files_modified += 1
        except OSError as e:
            logger.warning(f"Could not modify {file_path}: {e}")
    return files_modified, fixes_applied


def apply_docstring_fixes(fixes: List[Fix]) -> Tuple[int, int]:
    """Insert docstrings into undocumented public functions and classes."""
    by_file: Dict[Path, List[Fix]] = {}
    for fix in fixes:
        by_file.setdefault(fix.file_path, []).append(fix)

    files_modified = fixes_applied = 0
    for file_path in by_file:
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
            lines = source.splitlines()
            insertions = []

            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if node.name.startswith("_") or not node.body:
                    continue
                has_doc = (
                    isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )
                if has_doc:
                    continue
                body_idx = node.body[0].lineno - 1
                body_line = lines[body_idx] if body_idx < len(lines) else "    "
                indent = " " * (len(body_line) - len(body_line.lstrip()))
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                name = node.name.replace("_", " ").strip().capitalize()
                doc = [f'{indent}"""', f'{indent}{name} {kind}.', f'{indent}"""']
                insertions.append((body_idx, doc))

            if not insertions:
                continue
            backup_file(file_path)
            for idx, doc_lines in sorted(insertions, reverse=True):
                lines[idx:idx] = doc_lines
                fixes_applied += 1
            file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            files_modified += 1
        except (SyntaxError, OSError) as e:
            logger.warning(f"Could not add docstrings to {file_path}: {e}")
    return files_modified, fixes_applied


def restore_backup() -> None:
    """Restore all files from backup."""
    if not BACKUP_DIR.exists():
        print("No backup found - nothing to restore")
        return
    restored = 0
    for bp in BACKUP_DIR.rglob("*.py"):
        orig = PROJECT_ROOT / bp.relative_to(BACKUP_DIR)
        try:
            shutil.copy2(bp, orig)
            restored += 1
        except OSError as e:
            logger.warning(f"Could not restore {orig}: {e}")
    print(f"Restored {restored} files from backup")


def save_report(before: Dict, after: Optional[Dict], fixes: List[Fix], applied: int, files: int) -> None:
    """Save self-improvement JSON report."""
    bs, bg = get_score_and_grade(before)
    as_, ag = get_score_and_grade(after) if after else (bs, bg)
    by_cat: Dict = {}
    for fix in fixes:
        c = fix.category
        if c not in by_cat:
            by_cat[c] = {"description": FIXABLE_CATEGORIES.get(c, c), "count": 0, "files": []}
        by_cat[c]["count"] += 1
        fname = str(fix.file_path.relative_to(PROJECT_ROOT))
        if fname not in by_cat[c]["files"]:
            by_cat[c]["files"].append(fname)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SELF_IMPROVE_REPORT, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "before": {"score": bs, "grade": bg},
            "after": {"score": as_, "grade": ag},
            "improvement": {"score_delta": round(as_ - bs, 2), "fixes_applied": applied, "files_modified": files},
            "fixes_by_category": by_cat,
        }, f, indent=2)


def print_summary(bs: float, bg: str, as_: float, ag: str, applied: int, files: int) -> None:
    """Print score comparison without emoji."""
    delta = as_ - bs
    arrow = "^" if delta > 0 else "v" if delta < 0 else "="
    delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
    print()
    print("=" * 55)
    print("  AEGIS SELF-IMPROVEMENT SUMMARY")
    print("=" * 55)
    print(f"  Before : {bs:.1f}/100  Grade {bg}")
    print(f"  After  : {as_:.1f}/100  Grade {ag}  [{arrow}] {delta_str} pts")
    print(f"  Fixes  : {applied} applied across {files} files")
    print("=" * 55)
    if delta > 0:
        print(f"\n  IMPROVED by {delta_str} points")
    else:
        print("\n  Score unchanged - manual fixes needed for further improvement")
    print(f"\n  Report  : {SELF_IMPROVE_REPORT}")
    print(f"  To undo : python scripts/self_improve.py --restore\n")


def main() -> None:
    """Main entry point."""
    import argparse
    p = argparse.ArgumentParser(description="Aegis Self-Improvement")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--target-score", type=float)
    p.add_argument("--fix", choices=list(FIXABLE_CATEGORIES.keys()), nargs="+")
    p.add_argument("--restore", action="store_true")
    p.add_argument("--no-rerun", action="store_true")
    args = p.parse_args()

    if args.restore:
        restore_backup()
        return

    print("\nAEGIS SELF-IMPROVEMENT")
    print("Analyzing own codebase and applying automated fixes\n")

    print("Step 1/4: Running initial analysis...")
    before = run_analysis(".")
    if not before:
        print("ERROR: Analysis failed. Make sure synexian is installed: pip install -e .")
        sys.exit(1)
    bs, bg = get_score_and_grade(before)
    print(f"         Score: {bs:.1f}/100  Grade: {bg}\n")

    if args.target_score and bs >= args.target_score:
        print(f"Already at target score ({args.target_score}).")
        return

    print("Step 2/4: Scanning for fixable issues...")
    active = args.fix or list(FIXABLE_CATEGORIES.keys())
    all_fixes: List[Fix] = []

    if "docstrings" in active:
        f = find_missing_docstrings(SOURCE_DIR)
        print(f"         Missing docstrings    : {len(f)}")
        all_fixes.extend(f)
    if "bare_except" in active:
        f = find_bare_excepts(SOURCE_DIR)
        print(f"         Bare except:           : {len(f)}")
        all_fixes.extend(f)
    if "debug_flags" in active:
        f = find_debug_flags(SOURCE_DIR)
        print(f"         Debug flags            : {len(f)}")
        all_fixes.extend(f)
    if "trailing_whitespace" in active:
        f = find_trailing_whitespace(SOURCE_DIR)
        print(f"         Trailing whitespace    : {len(f)}")
        all_fixes.extend(f)

    print(f"\n         Total fixable: {len(all_fixes)}\n")

    if not all_fixes:
        print("No automatically fixable issues found.")
        return

    if args.dry_run:
        print("Step 3/4: DRY RUN - showing what would be fixed:\n")
        by_cat: Dict[str, List[Fix]] = {}
        for fix in all_fixes:
            by_cat.setdefault(fix.category, []).append(fix)
        for cat, cat_fixes in by_cat.items():
            print(f"  [{cat}] {len(cat_fixes)} fixes")
            for fix in cat_fixes[:3]:
                rel = str(fix.file_path.relative_to(PROJECT_ROOT))
                print(f"    Line {str(fix.line_number or '?'):>5} : {rel}")
            if len(cat_fixes) > 3:
                print(f"           ... and {len(cat_fixes) - 3} more")
        print(f"\n  Run without --dry-run to apply {len(all_fixes)} fixes.")
        return

    print("Step 3/4: Applying fixes...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    total_applied = total_files = 0

    for cat, finder_result in [
        ("bare_except",        [f for f in all_fixes if f.category == "bare_except"]),
        ("debug_flags",        [f for f in all_fixes if f.category == "debug_flags"]),
        ("trailing_whitespace",[f for f in all_fixes if f.category == "trailing_whitespace"]),
    ]:
        if finder_result:
            nf, na = apply_simple_replacement(finder_result)
            total_files += nf; total_applied += na
            print(f"         {cat:<22} : {na} fixes across {nf} files")

    doc_fixes = [f for f in all_fixes if f.category == "docstrings"]
    if doc_fixes and "docstrings" in active:
        nf, na = apply_docstring_fixes(doc_fixes)
        total_files += nf; total_applied += na
        print(f"         {'docstrings':<22} : {na} fixes across {nf} files")

    print(f"\n         Total: {total_applied} fixes across {total_files} files\n")

    if args.no_rerun:
        print("Step 4/4: Skipped (--no-rerun)")
        save_report(before, None, all_fixes, total_applied, total_files)
        return

    print("Step 4/4: Re-running analysis to measure improvement...")
    after = run_analysis(".")
    if after:
        as_, ag = get_score_and_grade(after)
    else:
        as_, ag = bs, bg
        print("WARNING: Re-analysis failed")

    save_report(before, after, all_fixes, total_applied, total_files)
    print_summary(bs, bg, as_, ag, total_applied, total_files)


if __name__ == "__main__":
    main()
