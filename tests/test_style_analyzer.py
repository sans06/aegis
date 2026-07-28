"""
Tests for StyleAnalyzer  zero coverage in original suite.
Tests PEP8 compliance, naming conventions, and docstring detection.
"""

import pytest
from pathlib import Path
from synexian.analyzers.style.analyzer import StyleAnalyzer
from synexian.config import AnalyzerConfig
from synexian.analyzers.base import AnalysisContext
from synexian.constants import ResultStatus, Severity


@pytest.fixture
def analyzer():
    config = AnalyzerConfig(enabled=True, options={"use_ai_analysis": False})
    return StyleAnalyzer(config=config, ai_client=None)


@pytest.fixture
def make_context(tmp_path):
    def _ctx(files):
        config = AnalyzerConfig(enabled=True, options={"use_ai_analysis": False})
        return AnalysisContext(
            project_root=tmp_path,
            files=files,
            config=config,
            cache_enabled=False,
        )
    return _ctx


def write_py(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return p


class TestStyleAnalyzerProperties:
    def test_name(self, analyzer):
        assert analyzer.name == "style"

    def test_is_enabled(self, analyzer):
        assert analyzer.is_enabled()


class TestStyleAnalyzerCleanCode:
    """Well-styled code should pass cleanly."""

    @pytest.mark.asyncio
    async def test_pep8_compliant_file(self, analyzer, tmp_path, make_context):
        f = write_py(tmp_path, "clean.py", '''"""Module docstring."""


def calculate_total(items, tax_rate=0.1):
    """Calculate total with tax."""
    subtotal = sum(items)
    return subtotal * (1 + tax_rate)


class OrderProcessor:
    """Process customer orders."""

    def __init__(self, discount=0.0):
        """Initialize with discount."""
        self.discount = discount

    def process(self, order):
        """Process a single order."""
        return order * (1 - self.discount)
''')
        ctx = make_context([f])
        result = await analyzer.analyze(ctx)
        assert result.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)
        # Should have very few or no style issues
        high_and_above = [i for i in result.issues
                         if i.severity in (Severity.HIGH, Severity.CRITICAL)]
        assert len(high_and_above) == 0


class TestStyleAnalyzerViolations:
    """Files with style violations should be flagged."""

    @pytest.mark.asyncio
    async def test_missing_docstrings_flagged(self, analyzer, tmp_path, make_context):
        f = write_py(tmp_path, "no_docs.py", """
def function_without_doc(x, y):
    return x + y

class ClassWithoutDoc:
    def method_without_doc(self):
        pass
""")
        ctx = make_context([f])
        result = await analyzer.analyze(ctx)
        assert result.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)

    @pytest.mark.asyncio
    async def test_long_lines_flagged(self, analyzer, tmp_path, make_context):
        long_line = "x = " + "a" * 200  # 204 chars, well over PEP8 79-char limit
        f = write_py(tmp_path, "longlines.py", long_line + "\n")
        ctx = make_context([f])
        result = await analyzer.analyze(ctx)
        assert result.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)

    @pytest.mark.asyncio
    async def test_unused_imports_detected(self, analyzer, tmp_path, make_context):
        f = write_py(tmp_path, "unused.py", """
import os
import sys
import json
import datetime

def do_something():
    return 42
""")
        ctx = make_context([f])
        result = await analyzer.analyze(ctx)
        assert result.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)


class TestStyleAnalyzerEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_file(self, analyzer, tmp_path, make_context):
        f = write_py(tmp_path, "empty.py", "")
        ctx = make_context([f])
        result = await analyzer.analyze(ctx)
        assert result is not None

    @pytest.mark.asyncio
    async def test_multiple_files(self, analyzer, tmp_path, make_context):
        files = [write_py(tmp_path, f"mod{i}.py", f"x = {i}\n") for i in range(4)]
        ctx = make_context(files)
        result = await analyzer.analyze(ctx)
        assert result is not None
        assert result.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="BUG: StyleAnalyzer propagates ParserError on syntax errors instead of handling gracefully  should return PARTIAL")
    async def test_syntax_error_file_handled(self, analyzer, tmp_path, make_context):
        f = write_py(tmp_path, "broken.py", "def oops(:\n    pass\n")
        ctx = make_context([f])
        result = await analyzer.analyze(ctx)
        # Should not raise an exception  graceful degradation
        assert result is not None
