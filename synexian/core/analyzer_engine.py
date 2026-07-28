"""Aegis's main analyzer orchestration engine."""

#=====================================
# © 2026 Synexian Labs Private Limited
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
from synexian.core.scoring_engine import ScoringEngine
from synexian.core.result_aggregator import ResultAggregator
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
        # FIX C-02: Wire ScoringEngine — previously it existed but was never used.
        # AnalyzerEngine had its own duplicate scoring methods with a different
        # (and less correct) formula. Now delegates to ScoringEngine consistently.
        self._scoring_engine = ScoringEngine(
            analyzer_weights=config.analyzer_weights
        )

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
        # FIX CR-13 / H-06: "default" key never exists in analyzers dict.
        # self.config.analyzers.get("default") always returned None,
        # making AnalysisContext.config=None (typed as AnalyzerConfig).
        # Each analyzer immediately creates its own context with the correct
        # config, so this initial context only needs a safe non-None value.
        from synexian.config import AnalyzerConfig
        context = AnalysisContext(
            project_root=project_path,
            files=files,
            config=AnalyzerConfig(),   # safe empty default — never actually used
            cache_enabled=self.config.cache_enabled,
        )

        # Run all analyzers
        results = await self._execute_analyzers(context)

        # FIX C-03: Wire ResultAggregator — previously it existed but was never used.
        # Without deduplication, the same issue found by multiple analyzers appeared
        # multiple times in the report, inflating issue counts and lowering scores.
        # Deduplicate across all results before building the report.
        all_issues_before = sum(len(r.issues) for r in results)
        for result in results:
            result.issues = ResultAggregator.deduplicate_issues(result.issues)
        all_issues_after = sum(len(r.issues) for r in results)
        if all_issues_before > all_issues_after:
            self.logger.debug(
                f"Deduplication removed {all_issues_before - all_issues_after} duplicate issues"
            )

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

        # FIX CR-04 / CR-14 / LV-14: return_exceptions=False cancelled ALL
        # analyzers when any single one crashed. Proven: 1 crash → 0 results.
        # With return_exceptions=True, exceptions are returned as values in the
        # results list and can be handled per-analyzer without cancelling others.
        raw = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert any Exception results to FAILED AnalysisResult objects
        from synexian.constants import ResultStatus
        from synexian.models.analysis_result import AnalysisResult as AR
        results = []
        for i, item in enumerate(raw):
            if isinstance(item, Exception):
                analyzer_name = self.analyzers[i].name if i < len(self.analyzers) else "unknown"
                self.logger.error(
                    f"Analyzer '{analyzer_name}' raised an unhandled exception: {item}",
                    exc_info=item,
                )
                results.append(AR(
                    analyzer_name=analyzer_name,
                    analyzer_version="unknown",
                    status=ResultStatus.FAILED,
                    metadata={"error": str(item), "error_type": type(item).__name__},
                ))
            else:
                results.append(item)
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
                # FIX CR-17: Read file ONCE with explicit encoding.
                # Previously opened twice (once for lines, once for AST),
                # and with no encoding parameter (fails on non-UTF-8 files).
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content_str = f.read()
                lines = content_str.splitlines()
                total_lines += len(lines)

                # Count Python files and test files
                if file_path.suffix == '.py':
                    total_python_files += 1
                    if 'test' in file_path.name.lower() or '/test' in str(file_path).lower():
                        total_test_files += 1

                # Parse AST for code structure (reuse already-read content)
                if True:
                    try:
                        tree = ast.parse(content_str)

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
                        pass  # Non-parseable files excluded from AST stats

            except Exception as e:
                # FIX CR-23: Log skipped files instead of silently swallowing
                self.logger.debug(f"Skipped {file_path} in summary stats: {e}")

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
            analysis_duration=report.execution_time_seconds,  # FIX: correct field name
            analyzers_run=analyzers_run,
            analyzers_failed=analyzers_failed,
        )

    def _calculate_overall_score(self, results: List[AnalysisResult]) -> float:
        """Calculate overall quality score (0-100).

        FIX C-02: Delegates to ScoringEngine instead of using the duplicate
        (and less correct) inline formula. ScoringEngine applies the correct
        70% metric / 30% issue-penalty weighted formula.
        """
        return self._scoring_engine.calculate_overall_score(results)

    def _calculate_grade(self, score: float) -> Grade:
        """Calculate letter grade from score.

        FIX C-02: Delegates to ScoringEngine instead of duplicating the logic.
        """
        return self._scoring_engine.calculate_grade(score)

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
