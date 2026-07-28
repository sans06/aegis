"""Tests for analyzers."""

#=====================================
#  2026 Synexian Labs Private Limited
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
        assert "average_complexity" in result.metrics

    @pytest.mark.asyncio
    async def test_analyzer_complex_file(self, complex_python_file, test_config):
        analyzer = ComplexityAnalyzer(test_config.analyzers["complexity"])

        context = AnalysisContext(
            project_root=complex_python_file.parent,
            files=[complex_python_file],
            config=test_config.analyzers["complexity"],
        )

        result = await analyzer.analyze(context)

        # Should detect high complexity
        assert len(result.issues) > 0
        assert result.metrics["average_complexity"].value > 1

    def test_analyzer_properties(self, test_config):
        analyzer = ComplexityAnalyzer(test_config.analyzers["complexity"])
        assert analyzer.name == "complexity"
        assert analyzer.version == "1.0.0"
        assert analyzer.requires_ai is False
