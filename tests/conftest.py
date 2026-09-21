"""Pytest configuration and fixtures"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import tempfile
from pathlib import Path

import pytest

from synexian.config import Config, AnalyzerConfig
from synexian.constants import AnalyzerType


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file for testing."""
    file_path = temp_dir / "sample.py"
    file_path.write_text("""
def simple_function(x, y):
    '''A simple function.'''
    return x + y

class SampleClass:
    def method(self, value):
        if value > 10:
            return value * 2
        else:
            return value
""")
    return file_path


@pytest.fixture
def complex_python_file(temp_dir):
    """Create a complex Python file for testing."""
    file_path = temp_dir / "complex.py"
    file_path.write_text("""
def complex_function(a, b, c, d):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    return a + b + c + d
                else:
                    return a + b + c
            else:
                return a + b
        else:
            return a
    else:
        return 0
""")
    return file_path


@pytest.fixture
def test_config():
    """Create a test configuration."""
    config = Config()
    config.openrouter_api_key = "test_key"
    config.cache_enabled = False
    config.parallel_analyzers = False

    # Set up analyzer configs
    config.analyzers = {
        "complexity": AnalyzerConfig(enabled=True, thresholds={"cyclomatic_complexity": 10}),
        "security": AnalyzerConfig(enabled=True),
        "style": AnalyzerConfig(enabled=True),
    }

    return config


@pytest.fixture
def sample_project(temp_dir):
    """Create a sample project structure."""
    # Create directory structure
    src_dir = temp_dir / "src"
    src_dir.mkdir()
    tests_dir = temp_dir / "tests"
    tests_dir.mkdir()

    # Create some Python files
    (src_dir / "__init__.py").write_text("")
    (src_dir / "main.py").write_text("""
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")

    (src_dir / "utils.py").write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""")

    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "test_main.py").write_text("""
from src.main import main

def test_main():
    assert True
""")

    return temp_dir
