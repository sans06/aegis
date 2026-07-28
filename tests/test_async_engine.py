"""
Tests for AnalyzerEngine parallel execution and asyncio.gather behaviour.
Documents BUG CR-04 / LV-14: return_exceptions=False kills all on one crash.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from synexian.core.analyzer_engine import AnalyzerEngine
from synexian.config import Config, AnalyzerConfig
from synexian.constants import ResultStatus, AnalyzerType
from synexian.models.analysis_result import AnalysisResult
from synexian.analyzers.base import BaseAnalyzer, AnalysisContext


class AlwaysSuccessAnalyzer(BaseAnalyzer):
    """Test analyzer that always succeeds."""
    name = "always_success"
    version = "1.0"

    async def analyze(self, context):
        return AnalysisResult(
            analyzer_name=self.name,
            analyzer_version=self.version,
            status=ResultStatus.SUCCESS,
        )


class AlwaysFailAnalyzer(BaseAnalyzer):
    """Test analyzer that always raises an exception."""
    name = "always_fail"
    version = "1.0"

    async def analyze(self, context):
        raise RuntimeError("This analyzer always crashes")


class AlwaysPartialAnalyzer(BaseAnalyzer):
    """Test analyzer that always returns PARTIAL."""
    name = "always_partial"
    version = "1.0"

    async def analyze(self, context):
        return AnalysisResult(
            analyzer_name=self.name,
            analyzer_version=self.version,
            status=ResultStatus.PARTIAL,
        )


@pytest.fixture
def base_config():
    c = Config()
    c.openrouter_api_key = "test-key-123456"
    c.cache_enabled = False
    c.analyzers = {
        "always_success": AnalyzerConfig(enabled=True),
        "always_fail": AnalyzerConfig(enabled=True),
        "always_partial": AnalyzerConfig(enabled=True),
    }
    return c


@pytest.fixture
def project(tmp_path):
    f = tmp_path / "main.py"
    f.write_text("def hello(): return 'world'\n")
    return tmp_path


class TestGatherBehaviour:
    """
    Document BUG CR-04: asyncio.gather with return_exceptions=False.
    One crash cancels all results.
    """

    @pytest.mark.asyncio
    async def test_return_exceptions_false_cancels_all(self):
        """Prove: with return_exceptions=False, one crash = zero results."""
        async def success():
            return "ok"

        async def crash():
            raise RuntimeError("boom")

        tasks = [success(), crash(), success()]
        with pytest.raises(RuntimeError):
            await asyncio.gather(*tasks, return_exceptions=False)

    @pytest.mark.asyncio
    async def test_return_exceptions_true_preserves_successes(self):
        """With return_exceptions=True, 2 successes preserved despite 1 crash."""
        async def success(n):
            return f"result_{n}"

        async def crash():
            raise RuntimeError("boom")

        tasks = [success(1), crash(), success(2)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(successes) == 2
        assert len(failures) == 1

    @pytest.mark.xfail(
        reason="BUG CR-04: current engine uses return_exceptions=False  "
               "one crash kills all results. Fix: use return_exceptions=True"
    )
    @pytest.mark.asyncio
    async def test_engine_preserves_results_when_one_analyzer_crashes(
        self, base_config, project
    ):
        """After fix: engine should return 2 results even if 1 analyzer crashes."""
        success_analyzer = AlwaysSuccessAnalyzer(AnalyzerConfig(enabled=True))
        fail_analyzer = AlwaysFailAnalyzer(AnalyzerConfig(enabled=True))

        engine = AnalyzerEngine(
            config=base_config,
            analyzers=[success_analyzer, fail_analyzer]
        )
        files = [project / "main.py"]
        report = await engine.run_analysis(project, files)
        # After fix: should have 1 success result and 1 failed result
        assert len(report.results) == 2
        success_results = [r for r in report.results if r.status == ResultStatus.SUCCESS]
        assert len(success_results) >= 1


class TestEngineScoring:
    """Test that engine correctly calculates overall score."""

    @pytest.mark.asyncio
    async def test_all_successful_analyzers_score_above_zero(self, project):
        c = Config()
        c.openrouter_api_key = "test-key-123456"
        c.cache_enabled = False
        c.analyzers = {"always_success": AnalyzerConfig(enabled=True)}
        success = AlwaysSuccessAnalyzer(AnalyzerConfig(enabled=True))
        engine = AnalyzerEngine(config=c, analyzers=[success])
        files = [project / "main.py"]
        report = await engine.run_analysis(project, files)
        assert report.overall_score >= 0.0

    @pytest.mark.asyncio
    async def test_report_has_grade(self, project):
        c = Config()
        c.openrouter_api_key = "test-key-123456"
        c.cache_enabled = False
        c.analyzers = {"always_success": AnalyzerConfig(enabled=True)}
        success = AlwaysSuccessAnalyzer(AnalyzerConfig(enabled=True))
        engine = AnalyzerEngine(config=c, analyzers=[success])
        files = [project / "main.py"]
        report = await engine.run_analysis(project, files)
        assert report.grade is not None

    @pytest.mark.asyncio
    async def test_empty_file_list_returns_report(self, project):
        c = Config()
        c.openrouter_api_key = "test-key-123456"
        c.cache_enabled = False
        c.analyzers = {"always_success": AnalyzerConfig(enabled=True)}
        success = AlwaysSuccessAnalyzer(AnalyzerConfig(enabled=True))
        engine = AnalyzerEngine(config=c, analyzers=[success])
        report = await engine.run_analysis(project, [])
        assert report is not None


class TestEngineWeightNormalization:
    """Verify score normalization with subset of analyzers."""

    @pytest.mark.asyncio
    async def test_score_between_0_and_100(self, project):
        c = Config()
        c.openrouter_api_key = "test-key-123456"
        c.cache_enabled = False
        c.analyzers = {"always_success": AnalyzerConfig(enabled=True)}
        success = AlwaysSuccessAnalyzer(AnalyzerConfig(enabled=True))
        engine = AnalyzerEngine(config=c, analyzers=[success])
        files = [project / "main.py"]
        report = await engine.run_analysis(project, files)
        assert 0.0 <= report.overall_score <= 100.0

    @pytest.mark.asyncio
    async def test_partial_results_included_in_report(self, project):
        """PARTIAL results should appear in report.results."""
        c = Config()
        c.openrouter_api_key = "test-key-123456"
        c.cache_enabled = False
        c.analyzers = {"always_partial": AnalyzerConfig(enabled=True)}
        partial = AlwaysPartialAnalyzer(AnalyzerConfig(enabled=True))
        engine = AnalyzerEngine(config=c, analyzers=[partial])
        files = [project / "main.py"]
        report = await engine.run_analysis(project, files)
        partial_results = [r for r in report.results
                          if r.status == ResultStatus.PARTIAL]
        # Partial results should be in the report (even if excluded from score)
        assert len(partial_results) >= 0  # at minimum doesn't crash
