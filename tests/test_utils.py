"""Tests for utility modules"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

from pathlib import Path

import pytest

from synexian.utils.file_utils import count_lines, get_file_hash, is_python_file
from synexian.utils.validators import (
    is_github_url,
    validate_api_key,
    validate_path,
)
from synexian.exceptions import ValidationError


class TestFileUtils:
    """Tests for file utility functions."""

    def test_is_python_file(self):
        assert is_python_file(Path("test.py")) is True
        assert is_python_file(Path("test.txt")) is False
        assert is_python_file(Path("test.PY")) is False

    def test_count_lines(self, sample_python_file):
        lines = count_lines(sample_python_file)
        assert lines > 0

    def test_get_file_hash(self, sample_python_file):
        hash1 = get_file_hash(sample_python_file)
        hash2 = get_file_hash(sample_python_file)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest length


class TestValidators:
    """Tests for validation functions."""

    def test_validate_path(self, temp_dir):
        path = validate_path(str(temp_dir))
        assert isinstance(path, Path)
        assert path.exists()

    def test_validate_path_invalid(self):
        with pytest.raises(ValidationError):
            validate_path("/this/path/does/not/exist/hopefully")

    def test_is_github_url(self):
        assert is_github_url("https://github.com/user/repo") is True
        assert is_github_url("http://github.com/user/repo") is True
        assert is_github_url("https://gitlab.com/user/repo") is False
        assert is_github_url("/local/path") is False

    def test_validate_api_key(self):
        key = validate_api_key("valid_api_key_12345")
        assert key == "valid_api_key_12345"

    def test_validate_api_key_empty(self):
        with pytest.raises(ValidationError):
            validate_api_key("")

    def test_validate_api_key_too_short(self):
        with pytest.raises(ValidationError):
            validate_api_key("short")
