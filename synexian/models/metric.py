"""Metric models for the Synexian application."""

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union


@dataclass
class MetricDefinition:
    """Defines a metric that an analyzer can produce."""

    name: str
    description: str
    unit: Optional[str] = None
    higher_is_better: bool = True
    threshold: Optional[float] = None


@dataclass
class MetricValue:
    """A measured metric value with pass/fail threshold evaluation.

    FIX CR-10 / LV-03: Added higher_is_better flag so metrics like
    code_coverage and mutation_score (where MORE is better) are evaluated
    correctly. Previously all metrics used <= (lower is better), causing
    40% coverage to report passed=True against an 80% threshold.
    """

    name: str
    value: Union[int, float, str]
    unit: Optional[str] = None
    threshold: Optional[float] = None
    passed: Optional[bool] = None
    # NEW: whether a higher value is better (e.g. coverage) or lower (e.g. complexity)
    higher_is_better: bool = False

    def __post_init__(self):
        """Calculate passed status if threshold is set and value is numeric."""
        if self.threshold is not None and isinstance(self.value, (int, float)):
            self.passed = self.is_within_threshold()

    def is_within_threshold(self) -> bool:
        """Check if the metric value meets its threshold.

        Uses higher_is_better to determine comparison direction:
          - higher_is_better=False (default): value <= threshold (e.g. complexity)
          - higher_is_better=True:            value >= threshold (e.g. coverage)
        """
        if self.threshold is None:
            return True
        if not isinstance(self.value, (int, float)):
            return True

        # FIX: use directional comparison instead of always <=
        if self.higher_is_better:
            return self.value >= self.threshold
        return self.value <= self.threshold

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric value to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "threshold": self.threshold,
            "passed": self.passed,
            "higher_is_better": self.higher_is_better,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricValue":
        """Create MetricValue from dictionary.

        FIX: Passes higher_is_better from dict so restored metrics are
        evaluated with the correct direction rather than defaulting to False.
        """
        return cls(
            name=data["name"],
            value=data["value"],
            unit=data.get("unit"),
            threshold=data.get("threshold"),
            higher_is_better=data.get("higher_is_better", False),
            # Note: passed is recalculated by __post_init__ using the
            # restored higher_is_better value — this is now correct.
        )


@dataclass
class SummaryStats:
    """Summary statistics for an analysis run."""

    total_files: int = 0
    total_lines: int = 0
    total_python_files: int = 0
    total_test_files: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_methods: int = 0
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    info_issues: int = 0
    avg_cyclomatic_complexity: float = 0.0
    max_cyclomatic_complexity: int = 0
    avg_cognitive_complexity: float = 0.0
    code_coverage: float = 0.0
    test_to_code_ratio: float = 0.0
    avg_maintainability_index: float = 0.0
    analyzers_run: int = 0
    analyzers_failed: int = 0
    analysis_duration: float = 0.0

    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return self.critical_issues > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_python_files": self.total_python_files,
            "total_test_files": self.total_test_files,
            "total_functions": self.total_functions,
            "total_classes": self.total_classes,
            "total_methods": self.total_methods,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "medium_issues": self.medium_issues,
            "low_issues": self.low_issues,
            "info_issues": self.info_issues,
            "avg_cyclomatic_complexity": self.avg_cyclomatic_complexity,
            "max_cyclomatic_complexity": self.max_cyclomatic_complexity,
            "avg_cognitive_complexity": self.avg_cognitive_complexity,
            "code_coverage": self.code_coverage,
            "test_to_code_ratio": self.test_to_code_ratio,
            "avg_maintainability_index": self.avg_maintainability_index,
            "analyzers_run": self.analyzers_run,
            "analyzers_failed": self.analyzers_failed,
            "analysis_duration": self.analysis_duration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SummaryStats":
        """Create SummaryStats from dictionary."""
        valid_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
