"""Base analyzer interface for Aegis's analyzers """

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from synexian.config import AnalyzerConfig
from synexian.models import AnalysisResult, MetricDefinition
from synexian.constants import ResultStatus


@dataclass
class AnalysisContext:
    """Context information provided to analyzers."""

    project_root: Path
    files: List[Path]
    config: AnalyzerConfig
    cache_enabled: bool = True


class BaseAnalyzer(ABC):
    """Base class for all analyzers."""

    def __init__(self, config: AnalyzerConfig, ai_client: Optional[Any] = None):
        """Initialize the analyzer.

        Args:
            config: Analyzer-specific configuration
            ai_client: Optional AI client for AI-powered analysis
        """
        self.config = config
        self.ai_client = ai_client
        self.logger = logging.getLogger(f"synexian.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique analyzer name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Analyzer version."""
        pass

    @property
    def requires_ai(self) -> bool:
        """Whether this analyzer needs AI."""
        return False

    @property
    def supported_languages(self) -> List[str]:
        """Supported programming languages."""
        return ["python"]

    @abstractmethod
    async def analyze(self, context: AnalysisContext) -> AnalysisResult:
        """Run the analysis.

        Args:
            context: Analysis context with project information

        Returns:
            AnalysisResult containing metrics, issues, and insights
        """
        pass

    def get_metric_definitions(self) -> List[MetricDefinition]:
        """Get metrics this analyzer produces.

        Returns:
            List of metric definitions
        """
        return []

    def should_analyze_file(self, file_path: Path) -> bool:
        """Whether this analyzer should process this file.

        Args:
            file_path: Path to the file

        Returns:
            True if the analyzer can process this file
        """
        return file_path.suffix == ".py"

    def is_enabled(self) -> bool:
        """Check if this analyzer is enabled in the configuration.

        Returns:
            True if the analyzer is enabled
        """
        return self.config.enabled

    async def run_safe(self, context: AnalysisContext) -> AnalysisResult:
        """Run analysis with error handling.

        Args:
            context: Analysis context

        Returns:
            AnalysisResult, potentially with FAILED status if errors occur
        """
        try:
            if not self.is_enabled():
                self.logger.info(f"Analyzer {self.name} is disabled, skipping")
                return AnalysisResult(
                    analyzer_name=self.name,
                    analyzer_version=self.version,
                    status=ResultStatus.SKIPPED,
                )

            self.logger.info(f"Starting analysis with {self.name}")
            result = await self.analyze(context)
            self.logger.info(
                f"Completed {self.name} analysis: {len(result.issues)} issues found"
            )
            return result

        except Exception as e:
            self.logger.error(f"Analysis failed for {self.name}: {str(e)}", exc_info=True)
            return AnalysisResult(
                analyzer_name=self.name,
                analyzer_version=self.version,
                status=ResultStatus.FAILED,
                metadata={"error": str(e)},
            )

    def get_threshold(self, metric_name: str) -> Optional[float]:
        """Get threshold value for a metric.

        Args:
            metric_name: Name of the metric

        Returns:
            Threshold value or None if not configured
        """
        return self.config.thresholds.get(metric_name)

    def get_option(self, option_name: str, default: Any = None) -> Any:
        """Get configuration option value.

        Args:
            option_name: Name of the option
            default: Default value if not configured

        Returns:
            Option value or default
        """
        return self.config.options.get(option_name, default)
