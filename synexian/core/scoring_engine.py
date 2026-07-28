"""Calculate quality scores and grades """

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

from typing import Dict, List

from synexian.constants import (
    GRADE_THRESHOLDS,
    AnalyzerType,
    Grade,
    ResultStatus,
    Severity,
)
from synexian.models import AnalysisResult


class ScoringEngine:
    """Calculate quality scores from analysis results."""

    def __init__(self, analyzer_weights: Dict[AnalyzerType, float]):
        """Initialize scoring engine.

        Args:
            analyzer_weights: Weights for each analyzer type
        """
        self.analyzer_weights = analyzer_weights

    def calculate_overall_score(self, results: List[AnalysisResult]) -> float:
        """Calculate overall quality score (0-100).

        Args:
            results: List of analysis results

        Returns:
            Overall score
        """
        if not results:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for result in results:
            if result.status != ResultStatus.SUCCESS:
                continue

            # Get weight for this analyzer
            try:
                analyzer_type = AnalyzerType(result.analyzer_name)
                weight = self.analyzer_weights.get(analyzer_type, 0.0)
            except ValueError:
                weight = 0.0

            # Calculate score for this analyzer
            analyzer_score = self._calculate_analyzer_score(result)

            total_score += analyzer_score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        # Normalize to 0-100
        return min(100.0, max(0.0, (total_score / total_weight) * 100))

    def _calculate_analyzer_score(self, result: AnalysisResult) -> float:
        """Calculate score for a single analyzer (0-1).

        Args:
            result: Analysis result

        Returns:
            Analyzer score between 0 and 1
        """
        # Check if metrics exist and calculate based on passing thresholds
        if result.metrics:
            passing_metrics = len([m for m in result.metrics.values() if m.passed is True])
            total_metrics = len([m for m in result.metrics.values() if m.passed is not None])

            if total_metrics > 0:
                metric_score = passing_metrics / total_metrics
            else:
                metric_score = 1.0
        else:
            metric_score = 1.0

        # Calculate issue penalty
        issue_penalty = self._calculate_issue_penalty(result)

        # Combine scores (70% metrics, 30% issues)
        return (metric_score * 0.7) + ((1.0 - issue_penalty) * 0.3)

    def _calculate_issue_penalty(self, result: AnalysisResult) -> float:
        """Calculate penalty based on issues (0-1).

        Args:
            result: Analysis result

        Returns:
            Penalty value (0 = no penalty, 1 = maximum penalty)
        """
        if not result.issues:
            return 0.0

        penalty = 0.0

        for issue in result.issues:
            if issue.severity == Severity.CRITICAL:
                penalty += 0.2
            elif issue.severity == Severity.HIGH:
                penalty += 0.1
            elif issue.severity == Severity.MEDIUM:
                penalty += 0.05
            elif issue.severity == Severity.LOW:
                penalty += 0.02
            elif issue.severity == Severity.INFO:
                penalty += 0.01

        return min(1.0, penalty)

    def calculate_grade(self, score: float) -> Grade:
        """Calculate letter grade from score.

        Args:
            score: Overall score (0-100)

        Returns:
            Letter grade
        """
        for grade, threshold in GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade

        return Grade.F
