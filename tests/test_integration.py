"""Integration tests for the full analysis pipeline"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import pytest

from synexian.analyzers.complexity.analyzer import ComplexityAnalyzer
from synexian.analyzers.style.analyzer import StyleAnalyzer
from synexian.core.analyzer_engine import AnalyzerEngine
from synexian.input.local_directory import LocalDirectoryHandler


class TestFullAnalysisPipeline:
    """Test the complete analysis pipeline."""

    @pytest.mark.asyncio
    async def test_full_analysis(self, sample_project, test_config):
        """Test complete analysis of a sample project."""

        # Create input handler
        handler = LocalDirectoryHandler(
            directory=sample_project,
            file_patterns=["**/*.py"],
            ignore_patterns=["**/__pycache__/**"],
            max_file_size_kb=1000,
        )

        project_root = handler.prepare()
        files = handler.get_files()

        assert len(files) > 0

        # Create analyzers
        analyzers = [
            ComplexityAnalyzer(test_config.analyzers["complexity"]),
        ]

        # Create engine
        engine = AnalyzerEngine(config=test_config, analyzers=analyzers)

        # Run analysis
        report = await engine.run_analysis(project_root, files)

        assert report is not None
        assert report.overall_score >= 0
        assert report.overall_score <= 100
        assert len(report.results) == len(analyzers)
        assert report.summary_stats.total_files == len(files)

        handler.cleanup()

    @pytest.mark.asyncio
    async def test_parallel_analysis(self, sample_project, test_config):
        """Test parallel analyzer execution."""

        test_config.parallel_analyzers = True

        handler = LocalDirectoryHandler(
            directory=sample_project,
            file_patterns=["**/*.py"],
            ignore_patterns=[],
        )

        files = handler.get_files()

        analyzers = [
            ComplexityAnalyzer(test_config.analyzers["complexity"]),
        ]

        engine = AnalyzerEngine(config=test_config, analyzers=analyzers)
        report = await engine.run_analysis(sample_project, files)

        assert len(report.results) > 0

        handler.cleanup()
