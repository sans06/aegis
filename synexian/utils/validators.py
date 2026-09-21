"""Input validation utilities """

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from synexian.exceptions import ValidationError


def validate_path(path_str: str) -> Path:
    """Validate and convert path string to Path object.

    Args:
        path_str: Path string

    Returns:
        Path object

    Raises:
        ValidationError: If path is invalid
    """
    try:
        path = Path(path_str).resolve()
        return path
    except Exception as e:
        raise ValidationError(f"Invalid path '{path_str}': {e}")


def validate_file_exists(path: Path) -> Path:
    """Validate that file exists.

    Args:
        path: File path

    Returns:
        Path object

    Raises:
        ValidationError: If file doesn't exist
    """
    if not path.exists():
        raise ValidationError(f"File not found: {path}")

    if not path.is_file():
        raise ValidationError(f"Not a file: {path}")

    return path


def validate_directory_exists(path: Path) -> Path:
    """Validate that directory exists.

    Args:
        path: Directory path

    Returns:
        Path object

    Raises:
        ValidationError: If directory doesn't exist
    """
    if not path.exists():
        raise ValidationError(f"Directory not found: {path}")

    if not path.is_dir():
        raise ValidationError(f"Not a directory: {path}")

    return path


def validate_github_url(url: str) -> str:
    """Validate GitHub repository URL.

    Args:
        url: GitHub URL

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid
    """
    try:
        parsed = urlparse(url)

        # Check if it's a valid URL
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(f"Invalid URL: {url}")

        # Check if it's GitHub
        if "github.com" not in parsed.netloc.lower():
            raise ValidationError(f"Not a GitHub URL: {url}")

        # Extract owner/repo
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) < 2:
            raise ValidationError(f"Invalid GitHub repository URL: {url}")

        return url

    except Exception as e:
        raise ValidationError(f"Invalid GitHub URL '{url}': {e}")


def is_github_url(url_or_path: str) -> bool:
    """Check if string is a GitHub URL.

    Args:
        url_or_path: String to check

    Returns:
        True if GitHub URL
    """
    return url_or_path.startswith(("http://", "https://")) and "github.com" in url_or_path.lower()


def validate_api_key(api_key: Optional[str]) -> str:
    """Validate API key format.

    Args:
        api_key: API key to validate

    Returns:
        Validated API key

    Raises:
        ValidationError: If API key is invalid
    """
    if not api_key:
        raise ValidationError("API key is required")

    if len(api_key) < 10:
        raise ValidationError("API key appears to be invalid (too short)")

    return api_key


def validate_pattern(pattern: str) -> str:
    """Validate glob pattern.

    Args:
        pattern: Glob pattern

    Returns:
        Validated pattern

    Raises:
        ValidationError: If pattern is invalid
    """
    if not pattern:
        raise ValidationError("Pattern cannot be empty")

    # Basic validation - just check for obviously invalid patterns
    if pattern.startswith("/"):
        raise ValidationError(f"Pattern should not start with '/': {pattern}")

    return pattern
