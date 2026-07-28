"""File utility functions """

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

import hashlib
from pathlib import Path
from typing import List, Optional

import pathspec


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_files_from_directory(
    directory: Path,
    patterns: List[str],
    ignore_patterns: List[str],
    max_size_kb: int = 1000,
) -> List[Path]:
    """Get all files from directory matching patterns.

    Args:
        directory: Directory to scan
        patterns: File patterns to include (e.g., ["**/*.py"])
        ignore_patterns: Patterns to ignore (gitignore-style)
        max_size_kb: Maximum file size in KB

    Returns:
        List of file paths
    """
    files = []

    # Create pathspec for ignore patterns
    spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)

    # Find all matching files
    for pattern in patterns:
        # Remove **/ prefix if present
        clean_pattern = pattern.replace("**/", "")

        for file_path in directory.rglob(clean_pattern):
            if not file_path.is_file():
                continue

            # Check if file should be ignored
            relative_path = file_path.relative_to(directory)
            if spec.match_file(str(relative_path)):
                continue

            # Check file size
            size_kb = file_path.stat().st_size / 1024
            if size_kb > max_size_kb:
                continue

            files.append(file_path)

    return sorted(set(files))


def count_lines(file_path: Path) -> int:
    """Count lines in a file.

    Args:
        file_path: Path to the file

    Returns:
        Number of lines
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return len(f.readlines())
    except Exception:
        return 0


def read_file_safe(file_path: Path) -> Optional[str]:
    """Safely read file content.

    Args:
        file_path: Path to the file

    Returns:
        File content or None if error
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def is_python_file(file_path: Path) -> bool:
    """Check if file is a Python file.

    Args:
        file_path: Path to check

    Returns:
        True if Python file
    """
    return file_path.suffix == ".py"


def ensure_dir(directory: Path) -> None:
    """Ensure directory exists, create if it doesn't.

    Args:
        directory: Directory path
    """
    directory.mkdir(parents=True, exist_ok=True)
