"""Metric models for the Synexian application """


#=====================================
#  2026 Synexian Labs Private Limited
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
    """A measured metric value."""

    name: str
    value: Union[int, float, str]
    unit: Optional[str] = None
    threshold: Optional[float] = None
    passed: Optional[bool] = None

    def __post_init__(self):
        """Calculate passed status if threshold is set and value is numeric."""
        if self.threshold is not None and isinstance(self.value, (int, float)):
            self.passed = self.is_within_threshold()

    def is_within_threshold(self) -> bool:
        """Check if the metric value meets its threshold (direction-aware)."""
        if self.threshold is None:
            return True
        if not isinstance(self.value, (int, float)):
            return True
        if getattr(self, 'higher_is_better', False):
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
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricValue":
        """Create MetricValue from dictionary."""
        return cls(
            name=data["name"],
            value=data["value"],
            unit=data.get("unit"),
            threshold=data.get("threshold"),
            passed=data.get("passed"),
        )


@dataclass
class SummaryStats:
    """Summary statistics for an analysis report."""

    # File-level statistics
    total_files: int = 0
    total_lines: int = 0
    total_python_files: int = 0
    total_test_files: int = 0

    # Code structure statistics
    total_functions: int = 0
    total_classes: int = 0
    total_methods: int = 0

    # Complexity statistics
    avg_cyclomatic_complexity: float = 0.0
    max_cyclomatic_complexity: int = 0
    avg_cognitive_complexity: float = 0.0

    # Issue statistics
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    info_issues: int = 0

    # Quality metrics
    code_coverage: float = 0.0
    test_to_code_ratio: float = 0.0
    avg_maintainability_index: float = 0.0

    # Execution statistics
    execution_time_seconds: float = 0.0
    analyzers_run: int = 0
    analyzers_failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert summary stats to dictionary."""
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_python_files": self.total_python_files,
            "total_test_files": self.total_test_files,
            "total_functions": self.total_functions,
            "total_classes": self.total_classes,
            "total_methods": self.total_methods,
            "avg_cyclomatic_complexity": self.avg_cyclomatic_complexity,
            "max_cyclomatic_complexity": self.max_cyclomatic_complexity,
            "avg_cognitive_complexity": self.avg_cognitive_complexity,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "medium_issues": self.medium_issues,
            "low_issues": self.low_issues,
            "info_issues": self.info_issues,
            "code_coverage": self.code_coverage,
            "test_to_code_ratio": self.test_to_code_ratio,
            "avg_maintainability_index": self.avg_maintainability_index,
            "execution_time_seconds": self.execution_time_seconds,
            "analyzers_run": self.analyzers_run,
            "analyzers_failed": self.analyzers_failed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SummaryStats":
        """Create SummaryStats from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
