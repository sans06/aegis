#!/usr/bin/env python3
"""
fix_encoding.py
===============
Removes all non-ASCII characters (emoji, special Unicode) from Python
source files and fixes file open() calls to use encoding="utf-8".

Run this ONCE from inside your aegis_fixed folder:
    python fix_encoding.py

It will fix every .py file in the project automatically.
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# Characters to replace with plain-text equivalents
EMOJI_REPLACEMENTS = {
    "\u2694\ufe0f": "[AEGIS]",   # sword emoji
    "\u2694":       "[AEGIS]",
    "\U0001f50d":   "[SEARCH]",  # magnifying glass
    "\u26a0\ufe0f": "[WARN]",    # warning sign
    "\u26a0":       "[WARN]",
    "\u2705":       "[OK]",      # check mark
    "\u274c":       "[FAIL]",    # cross mark
    "\u2714":       "[OK]",      # heavy check
    "\u2716":       "[FAIL]",    # heavy cross
    "\U0001f4a1":   "[INFO]",    # lightbulb
    "\U0001f527":   "[FIX]",     # wrench
    "\U0001f4cb":   "[LIST]",    # clipboard
    "\U0001f3af":   "[TARGET]",  # target
    "\U0001f680":   "[LAUNCH]",  # rocket
    "\u2b50":       "[STAR]",    # star
    "\U0001f4c8":   "[CHART]",   # chart
    "\U0001f440":   "[LOOK]",    # eyes
    "\u2728":       "[SPARK]",   # sparkles
    "\U0001f6e0\ufe0f": "[TOOL]", # tools
    "\U0001f6e0":   "[TOOL]",
    "\U0001f4dd":   "[NOTE]",    # memo
    "\u2139\ufe0f": "[INFO]",    # info
    "\u2139":       "[INFO]",
    "\U0001f4af":   "[100]",     # 100 points
    "\u2764\ufe0f": "[HEART]",   # heart
    "\u2764":       "[HEART]",
    "\U0001f4a5":   "[BOOM]",    # collision
    "\U0001f525":   "[FIRE]",    # fire
    "\U0001f3c6":   "[TROPHY]",  # trophy
    "\U0001f4e6":   "[PKG]",     # package
}

# Fix file open() calls missing encoding parameter
OPEN_PATTERN = re.compile(
    r'open\(([^)]+),\s*["\']w["\']\s*\)',
    re.MULTILINE,
)


def fix_emoji_in_string(text: str) -> str:
    """Replace known emoji with plain-text equivalents."""
    for emoji, replacement in EMOJI_REPLACEMENTS.items():
        text = text.replace(emoji, replacement)
    return text


def fix_non_ascii(text: str) -> str:
    """Remove any remaining non-ASCII characters not in the replacement map."""
    result = []
    for char in text:
        if ord(char) <= 127:
            result.append(char)
        elif char in EMOJI_REPLACEMENTS:
            result.append(EMOJI_REPLACEMENTS[char])
        else:
            # Replace with nothing (remove the character)
            pass
    return "".join(result)


def fix_file_open_encoding(text: str) -> str:
    """Add encoding='utf-8' to open() calls that write files."""
    # Fix: open(path, "w", encoding="utf-8") -> open(path, "w", encoding="utf-8")
    text = re.sub(
        r'open\(([^,)]+),\s*"w"\s*\)',
        r'open(\1, "w", encoding="utf-8")',
        text,
    )
    text = re.sub(
        r"open\(([^,)]+),\s*'w'\s*\)",
        r"open(\1, 'w', encoding='utf-8')",
        text,
    )
    # Fix: open(path, "r", encoding="utf-8", errors="replace") -> open(path, "r", encoding="utf-8", errors="replace")
    text = re.sub(
        r'open\(([^,)]+),\s*"r"\s*\)',
        r'open(\1, "r", encoding="utf-8", errors="replace")',
        text,
    )
    text = re.sub(
        r"open\(([^,)]+),\s*'r'\s*\)",
        r"open(\1, 'r', encoding='utf-8', errors='replace')",
        text,
    )
    return text


def process_file(path: Path, dry_run: bool = False) -> bool:
    """Process a single Python file. Returns True if changes were made."""
    try:
        # Read as bytes first to handle any encoding
        raw = path.read_bytes()

        # Try to decode as UTF-8
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            # Fall back to latin-1 which can decode any byte
            text = raw.decode("latin-1")

        original = text

        # Apply fixes
        text = fix_emoji_in_string(text)
        text = fix_non_ascii(text)
        text = fix_file_open_encoding(text)

        if text == original:
            return False

        if not dry_run:
            path.write_text(text, encoding="utf-8")

        return True

    except Exception as e:
        print(f"  ERROR processing {path}: {e}")
        return False


def main() -> None:
    """Main entry point."""
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("DRY RUN - showing files that would be changed (no files modified)\n")
    else:
        print("Fixing encoding issues in all Python files...\n")

    changed = []
    skipped_dirs = {
        "__pycache__", ".git", "venv", ".venv",
        "build", "dist", "htmlcov", ".pytest_cache",
        ".self_improve_backup",
    }

    for py_file in sorted(PROJECT_ROOT.rglob("*.py")):
        # Skip unwanted directories
        parts = set(py_file.parts)
        if parts & skipped_dirs:
            continue

        was_changed = process_file(py_file, dry_run=dry_run)
        if was_changed:
            rel = py_file.relative_to(PROJECT_ROOT)
            changed.append(rel)
            status = "would fix" if dry_run else "fixed"
            print(f"  {status}: {rel}")

    print()
    if not changed:
        print("No files needed fixing.")
    elif dry_run:
        print(f"Would fix {len(changed)} files. Run without --dry-run to apply.")
    else:
        print(f"Fixed {len(changed)} files.")
        print("\nYou can now run:")
        print("  synexian analyze . --output cli,html")


if __name__ == "__main__":
    main()
