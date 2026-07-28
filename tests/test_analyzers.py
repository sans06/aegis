"""Tests for analyzers."""

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

import pytest

from synexian.analyzers.base import AnalysisContext
from synexian.analyzers.complexity.analyzer import ComplexityAnalyzer
from synexian.config import AnalyzerConfig
from synexian.constants import ResultStatus


class TestComplexityAnalyzer:
    """Tests for ComplexityAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyzer_basic(self, sample_python_file, test_config):
        analyzer = ComplexityAnalyzer(test_config.analyzers["complexity"])

        context = AnalysisContext(
            project_root=sample_python_file.parent,
            files=[sample_python_file],
            config=test_config.analyzers["complexity"],
        )

        result = await analyzer.analyze(context)

        assert result.analyzer_name == "complexity"
        assert result.status == ResultStatus.SUCCESS
        assert "average_cyclomatic_complexity" in result.metrics

    @pytest.mark.asyncio
    async def test_analyzer_complex_file(self, complex_python_file, test_config):
        analyzer = ComplexityAnalyzer(test_config.analyzers["complexity"])

        context = AnalysisContext(
            project_root=complex_python_file.parent,
            files=[complex_python_file],
            config=test_config.analyzers["complexity"],
        )

        result = await analyzer.analyze(context)

        # Should return metrics — complex file has measurable complexity
        assert "average_cyclomatic_complexity" in result.metrics
        assert result.metrics["average_cyclomatic_complexity"].value >= 1
        # Complex file has high CC — may or may not raise issues depending on thresholds

    def test_analyzer_properties(self, test_config):
        analyzer = ComplexityAnalyzer(test_config.analyzers["complexity"])
        assert analyzer.name == "complexity"
        assert isinstance(analyzer.version, str)
        assert analyzer.requires_ai is False
