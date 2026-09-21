"""Aegis's main analyzer orchestration engine."""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from synexian.analyzers.base import AnalysisContext, BaseAnalyzer
from synexian.config import Config
from synexian.constants import Grade, GRADE_THRESHOLDS, ResultStatus
from synexian.models import AnalysisReport, AnalysisResult, MetricValue, SummaryStats
from synexian.exceptions import AnalysisFailedError


class AnalyzerEngine:
    """Main engine for orchestrating code analysis."""

    def __init__(self, config: Config, analyzers: Optional[List[BaseAnalyzer]] = None):
        """Initialize the analyzer engine.

        Args:
            config: Application configuration
            analyzers: List of analyzer instances to use
        """
        self.config = config
        self.analyzers = analyzers or []
        self.logger = logging.getLogger("synexian.engine")

    async def run_analysis(
        self,
        project_path: Path,
        files: List[Path],
    ) -> AnalysisReport:
        """Run complete analysis on the project.

        Args:
            project_path: Root path of the project
            files: List of files to analyze

        Returns:
            Complete analysis report

        Raises:
            AnalysisFailedError: If analysis fails completely
        """
        start_time = time.time()
        self.logger.info(f"Starting analysis of {len(files)} files in {project_path}")

        # Create analysis context
        context = AnalysisContext(
            project_root=project_path,
            files=files,
            config=self.config.analyzers.get("default"),
            cache_enabled=self.config.cache_enabled,
        )

        # Run all analyzers
        results = await self._execute_analyzers(context)

        # Calculate execution time
        execution_time = time.time() - start_time

        # Create analysis report
        report = AnalysisReport(
            project_path=project_path,
            timestamp=datetime.now(),
            results=results,
            execution_time_seconds=execution_time,
            config_snapshot=self.config.to_dict(),
        )

        # Calculate summary statistics
        report.summary_stats = self._calculate_summary_stats(report, files)

        # Calculate overall score and grade
        report.overall_score = self._calculate_overall_score(results)
        report.grade = self._calculate_grade(report.overall_score)

        self.logger.info(
            f"Analysis complete: {report.grade.value} ({report.overall_score:.1f}/100) "
            f"in {execution_time:.2f}s"
        )

        return report

    async def _execute_analyzers(self, context: AnalysisContext) -> List[AnalysisResult]:
        """Execute all enabled analyzers.

        Args:
            context: Analysis context

        Returns:
            List of analysis results
        """
        if not self.analyzers:
            self.logger.warning("No analyzers registered")
            return []

        if self.config.parallel_analyzers:
            return await self._execute_parallel(context)
        else:
            return await self._execute_sequential(context)

    async def _execute_parallel(self, context: AnalysisContext) -> List[AnalysisResult]:
        """Execute analyzers in parallel.

        Args:
            context: Analysis context

        Returns:
            List of analysis results
        """
        self.logger.info(f"Running {len(self.analyzers)} analyzers in parallel")

        tasks = []
        for analyzer in self.analyzers:
            # Update context with analyzer-specific config
            analyzer_context = AnalysisContext(
                project_root=context.project_root,
                files=context.files,
                config=self.config.analyzers.get(analyzer.name, analyzer.config),
                cache_enabled=context.cache_enabled,
            )
            tasks.append(analyzer.run_safe(analyzer_context))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    async def _execute_sequential(self, context: AnalysisContext) -> List[AnalysisResult]:
        """Execute analyzers sequentially.

        Args:
            context: Analysis context

        Returns:
            List of analysis results
        """
        self.logger.info(f"Running {len(self.analyzers)} analyzers sequentially")

        results = []
        for analyzer in self.analyzers:
            # Update context with analyzer-specific config
            analyzer_context = AnalysisContext(
                project_root=context.project_root,
                files=context.files,
                config=self.config.analyzers.get(analyzer.name, analyzer.config),
                cache_enabled=context.cache_enabled,
            )
            result = await analyzer.run_safe(analyzer_context)
            results.append(result)

        return results

    def _calculate_summary_stats(
        self, report: AnalysisReport, files: List[Path]
    ) -> SummaryStats:
        """Calculate comprehensive summary statistics for the report.

        Args:
            report: Analysis report
            files: List of analyzed files

        Returns:
            Summary statistics with detailed project metrics
        """
        import ast

        all_issues = report.get_all_issues()

        # Count issues by severity
        from synexian.constants import Severity

        critical_issues = len([i for i in all_issues if i.severity == Severity.CRITICAL])
        high_issues = len([i for i in all_issues if i.severity == Severity.HIGH])
        medium_issues = len([i for i in all_issues if i.severity == Severity.MEDIUM])
        low_issues = len([i for i in all_issues if i.severity == Severity.LOW])
        info_issues = len([i for i in all_issues if i.severity == Severity.INFO])

        # Count files, lines, and code structures
        total_lines = 0
        total_python_files = 0
        total_test_files = 0
        total_functions = 0
        total_classes = 0
        total_methods = 0

        for file_path in files:
            try:
                # Count lines
                with open(file_path, "r") as f:
                    lines = f.readlines()
                    total_lines += len(lines)

                # Count Python files and test files
                if file_path.suffix == '.py':
                    total_python_files += 1
                    if 'test' in file_path.name.lower() or '/test' in str(file_path).lower():
                        total_test_files += 1

                # Parse AST for code structure
                with open(file_path, "r") as f:
                    try:
                        tree = ast.parse(f.read())

                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                total_functions += 1
                            elif isinstance(node, ast.AsyncFunctionDef):
                                total_functions += 1
                            elif isinstance(node, ast.ClassDef):
                                total_classes += 1
                                # Count methods in class
                                for item in node.body:
                                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                        total_methods += 1

                    except SyntaxError:
                        pass

            except Exception:
                pass

        # Extract complexity metrics from complexity analyzer
        avg_cyclomatic = 0.0
        max_cyclomatic = 0
        avg_cognitive = 0.0

        complexity_result = next((r for r in report.results if r.analyzer_name == 'complexity'), None)
        if complexity_result and complexity_result.metrics:
            avg_cyclomatic = complexity_result.metrics.get('average_cyclomatic_complexity', MetricValue(name='', value=0)).value
            max_cyclomatic = int(complexity_result.metrics.get('max_cyclomatic_complexity', MetricValue(name='', value=0)).value)
            avg_cognitive = complexity_result.metrics.get('average_cognitive_complexity', MetricValue(name='', value=0)).value

        # Extract test quality metrics
        code_coverage = 0.0
        test_to_code_ratio = 0.0

        test_quality_result = next((r for r in report.results if r.analyzer_name == 'test_quality'), None)
        if test_quality_result and test_quality_result.metrics:
            coverage_metric = test_quality_result.metrics.get('statement_coverage', MetricValue(name='', value=0))
            code_coverage = coverage_metric.value if coverage_metric else 0.0

            ratio_metric = test_quality_result.metrics.get('test_to_code_ratio', MetricValue(name='', value=0))
            test_to_code_ratio = ratio_metric.value if ratio_metric else 0.0

        # Extract maintainability index from cognitive load analyzer
        avg_maintainability = 0.0

        cognitive_result = next((r for r in report.results if r.analyzer_name == 'cognitive_load'), None)
        if cognitive_result and cognitive_result.metrics:
            mi_metric = cognitive_result.metrics.get('average_maintainability_index', MetricValue(name='', value=0))
            avg_maintainability = mi_metric.value if mi_metric else 0.0

        # Count analyzer stats
        analyzers_run = len([r for r in report.results if r.status != ResultStatus.SKIPPED])
        analyzers_failed = len([r for r in report.results if r.status == ResultStatus.FAILED])

        return SummaryStats(
            # File-level statistics
            total_files=len(files),
            total_lines=total_lines,
            total_python_files=total_python_files,
            total_test_files=total_test_files,
            # Code structure statistics
            total_functions=total_functions,
            total_classes=total_classes,
            total_methods=total_methods,
            # Complexity statistics
            avg_cyclomatic_complexity=round(avg_cyclomatic, 2),
            max_cyclomatic_complexity=max_cyclomatic,
            avg_cognitive_complexity=round(avg_cognitive, 2),
            # Issue statistics
            total_issues=len(all_issues),
            critical_issues=critical_issues,
            high_issues=high_issues,
            medium_issues=medium_issues,
            low_issues=low_issues,
            info_issues=info_issues,
            # Quality metrics
            code_coverage=round(code_coverage, 2),
            test_to_code_ratio=round(test_to_code_ratio, 2),
            avg_maintainability_index=round(avg_maintainability, 2),
            # Execution statistics
            execution_time_seconds=report.execution_time_seconds,
            analyzers_run=analyzers_run,
            analyzers_failed=analyzers_failed,
        )

    def _calculate_overall_score(self, results: List[AnalysisResult]) -> float:
        """Calculate overall quality score (0-100).

        Args:
            results: List of analysis results

        Returns:
            Overall score
        """
        if not results:
            return 0.0

        # Calculate weighted average based on analyzer weights
        total_score = 0.0
        total_weight = 0.0

        for result in results:
            if result.status != ResultStatus.SUCCESS:
                continue

            # Get weight for this analyzer
            from synexian.constants import AnalyzerType

            try:
                analyzer_type = AnalyzerType(result.analyzer_name)
                weight = self.config.analyzer_weights.get(analyzer_type, 0.0)
            except ValueError:
                weight = 0.0

            # Calculate score for this analyzer (simplified - based on metrics passing)
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
        if not result.metrics:
            # If no metrics, base on issues
            if len(result.issues) == 0:
                return 1.0
            else:
                # Penalize based on issues
                from synexian.constants import Severity

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

                return max(0.0, 1.0 - penalty)

        # Calculate based on metrics passing their thresholds
        passing_metrics = len([m for m in result.metrics.values() if m.passed is True])
        total_metrics = len([m for m in result.metrics.values() if m.passed is not None])

        if total_metrics == 0:
            return 1.0

        return passing_metrics / total_metrics

    def _calculate_grade(self, score: float) -> Grade:
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

    def add_analyzer(self, analyzer: BaseAnalyzer) -> None:
        """Add an analyzer to the engine.

        Args:
            analyzer: Analyzer instance to add
        """
        self.analyzers.append(analyzer)
        self.logger.info(f"Added analyzer: {analyzer.name}")

    def get_enabled_analyzers(self) -> List[BaseAnalyzer]:
        """Get list of enabled analyzers.

        Returns:
            List of enabled analyzer instances
        """
        return [a for a in self.analyzers if a.is_enabled()]
