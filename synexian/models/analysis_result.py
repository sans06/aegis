"""Analysis result models for Aegis"""


#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from synexian.constants import Grade, IssueCategory, ResultStatus, Severity
from synexian.models.issue import Issue
from synexian.models.metric import MetricValue, SummaryStats


@dataclass
class AnalysisResult:
    """Result from a single analyzer."""

    analyzer_name: str
    analyzer_version: str
    status: ResultStatus
    metrics: Dict[str, MetricValue] = field(default_factory=dict)
    issues: List[Issue] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis result to dictionary."""
        return {
            "analyzer_name": self.analyzer_name,
            "analyzer_version": self.analyzer_version,
            "status": self.status.value,
            "metrics": {name: metric.to_dict() for name, metric in self.metrics.items()},
            "issues": [issue.to_dict() for issue in self.issues],
            "insights": self.insights,
            "execution_time_seconds": self.execution_time_seconds,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisResult":
        """Create AnalysisResult from dictionary."""
        return cls(
            analyzer_name=data["analyzer_name"],
            analyzer_version=data["analyzer_version"],
            status=ResultStatus(data["status"]),
            metrics={
                name: MetricValue.from_dict(metric)
                for name, metric in data.get("metrics", {}).items()
            },
            issues=[Issue.from_dict(issue) for issue in data.get("issues", [])],
            insights=data.get("insights", []),
            execution_time_seconds=data.get("execution_time_seconds", 0.0),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )

    def merge_with(self, other: "AnalysisResult") -> "AnalysisResult":
        """Merge this result with another result from the same analyzer."""
        if self.analyzer_name != other.analyzer_name:
            raise ValueError("Cannot merge results from different analyzers")

        merged_metrics = {**self.metrics, **other.metrics}
        merged_issues = self.issues + other.issues
        merged_insights = self.insights + other.insights
        merged_metadata = {**self.metadata, **other.metadata}

        return AnalysisResult(
            analyzer_name=self.analyzer_name,
            analyzer_version=self.analyzer_version,
            status=self.status if self.status != ResultStatus.SUCCESS else other.status,
            metrics=merged_metrics,
            issues=merged_issues,
            insights=merged_insights,
            execution_time_seconds=self.execution_time_seconds + other.execution_time_seconds,
            timestamp=self.timestamp,
            metadata=merged_metadata,
        )

    def get_issues_by_severity(self, severity: Severity) -> List[Issue]:
        """Get all issues of a specific severity."""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_category(self, category: IssueCategory) -> List[Issue]:
        """Get all issues of a specific category."""
        return [issue for issue in self.issues if issue.category == category]


@dataclass
class AnalysisReport:
    """Complete analysis report containing results from all analyzers."""

    project_path: Path
    timestamp: datetime
    results: List[AnalysisResult] = field(default_factory=list)
    overall_score: float = 0.0
    grade: Grade = Grade.F
    summary_stats: SummaryStats = field(default_factory=SummaryStats)
    execution_time_seconds: float = 0.0
    config_snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis report to dictionary."""
        return {
            "project_path": str(self.project_path),
            "timestamp": self.timestamp.isoformat(),
            "results": [result.to_dict() for result in self.results],
            "overall_score": self.overall_score,
            "grade": self.grade.value,
            "summary_stats": self.summary_stats.to_dict(),
            "execution_time_seconds": self.execution_time_seconds,
            "config_snapshot": self.config_snapshot,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisReport":
        """Create AnalysisReport from dictionary."""
        return cls(
            project_path=Path(data["project_path"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            results=[AnalysisResult.from_dict(r) for r in data.get("results", [])],
            overall_score=data.get("overall_score", 0.0),
            grade=Grade(data.get("grade", Grade.F.value)),
            summary_stats=SummaryStats.from_dict(data.get("summary_stats", {})),
            execution_time_seconds=data.get("execution_time_seconds", 0.0),
            config_snapshot=data.get("config_snapshot", {}),
        )

    def get_all_issues(self) -> List[Issue]:
        """Get all issues from all analyzer results."""
        all_issues = []
        for result in self.results:
            all_issues.extend(result.issues)
        return all_issues

    def get_issues_by_severity(self, severity: Severity) -> List[Issue]:
        """Get all issues of a specific severity."""
        return [issue for issue in self.get_all_issues() if issue.severity == severity]

    def get_issues_by_category(self, category: IssueCategory) -> List[Issue]:
        """Get all issues of a specific category."""
        return [issue for issue in self.get_all_issues() if issue.category == category]

    def get_metrics_by_category(self) -> Dict[str, List[MetricValue]]:
        """Get all metrics grouped by analyzer category."""
        metrics_by_category = {}
        for result in self.results:
            category = result.analyzer_name
            metrics_by_category[category] = list(result.metrics.values())
        return metrics_by_category

    def get_successful_results(self) -> List[AnalysisResult]:
        """Get all analyzer results that completed successfully."""
        return [r for r in self.results if r.status == ResultStatus.SUCCESS]

    def get_failed_results(self) -> List[AnalysisResult]:
        """Get all analyzer results that failed."""
        return [r for r in self.results if r.status == ResultStatus.FAILED]

    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return self.summary_stats.critical_issues > 0
