"""Complexity Analyzer - Multi-Metric Code Complexity Analysis

This analyzer implements complexity measurement methods using a
complementarity approach that combines multiple metrics for holistic code analysis:

- Cyclomatic Complexity (McCabe) with empirically validated thresholds
- Complete Halstead Metrics Suite (Volume, Difficulty, Effort, Bugs, Time)
- Enhanced Cognitive Complexity (SonarSource methodology)
- Nesting Depth Analysis (research-backed 4-5 level threshold)
- Essential Complexity (structured programming metric)
- NPATH Complexity (acyclic execution path counting)
- Metric Complementarity Analysis (hybrid approach)

Key Research Finding (Gao et al., 2025): No single metric fully captures complexity
perceived by programmers. Combining complementary metrics through data-driven models
achieves R² of 0.87 for predicting actual cognitive load measured via EEG.

References:
[1] Gao et al. (2025) "Complementarity in Software Code Complexity Metrics"
    https://www.sciencedirect.com/science/article/abs/pii/S0164121225003486
    Journal of Systems and Software, ScienceDirect
    Key finding: Gaussian Process Regression with complementary metrics achieves R²=0.8742

[2] "Early Career Developers' Perceptions of Code Understandability" (2024)
    https://arxiv.org/html/2303.07722
    Study of 216 developers rating complexity of Java classes
    Validated cyclomatic and cognitive complexity thresholds

[3] "Code Complexity Explained: How to Measure Effectively in 2025"
    https://www.qodo.ai/blog/code-complexity/
    Modern complexity measurement techniques and thresholds

[4] "Cognitive Complexity Explained: Causes, Metrics, and How to Fix" (2024)
    https://axify.io/blog/cognitive-complexity
    SonarSource cognitive complexity methodology

[5] Alrasheed (2022) "Measuring nesting"
    https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/sfw2.12069
    IET Software - Empirical study of nesting depth impact

[6] Nejmeh (1988) "NPATH: a measure of execution path complexity"
    https://dl.acm.org/doi/abs/10.1145/42372.42379
    AT&T Bell Labs - NPATH threshold of 200 established

[7] Halstead (1977) "Elements of Software Science"
    https://en.wikipedia.org/wiki/Halstead_complexity_measures
    Original formulation and empirical validation
"""

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

import ast
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from radon.complexity import cc_visit
from radon.metrics import h_visit, mi_visit
from radon.raw import analyze as radon_analyze

from synexian.analyzers.base import AnalysisContext, BaseAnalyzer
from synexian.constants import IssueCategory, ResultStatus, Severity
from synexian.models import AnalysisResult, Issue, MetricDefinition, MetricValue
from synexian.utils.file_utils import read_file_safe
from synexian.utils.ast_utils import get_max_nesting_depth, parse_python_file


class EnhancedCognitiveComplexityVisitor(ast.NodeVisitor):
    """Calculate cognitive complexity using SonarSource methodology.

    Based on SonarSource's Cognitive Complexity specification (2024):
    - Increments for control flow breaks (+1)
    - Additional increment for each level of nesting
    - Binary logical operators add complexity
    - Recursion detection

    This provides a better measure of human readability than cyclomatic complexity
    by heavily penalizing nesting, which research shows significantly impacts
    code comprehension (Gao et al., 2025).
    """

    def __init__(self):
        self.complexity = 0
        self.nesting_level = 0
        self.current_function = None

    def visit_FunctionDef(self, node):
        """Track function definitions for recursion detection."""
        previous_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = previous_function

    def visit_AsyncFunctionDef(self, node):
        """Track async function definitions."""
        previous_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = previous_function

    def visit_If(self, node):
        """If statements: +1 + nesting level."""
        self.complexity += 1 + self.nesting_level
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_IfExp(self, node):
        """Ternary expressions: +1 + nesting level."""
        self.complexity += 1 + self.nesting_level
        self.generic_visit(node)

    def visit_While(self, node):
        """While loops: +1 + nesting level."""
        self.complexity += 1 + self.nesting_level
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_For(self, node):
        """For loops: +1 + nesting level."""
        self.complexity += 1 + self.nesting_level
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_ExceptHandler(self, node):
        """Exception handlers: +1 + nesting level."""
        self.complexity += 1 + self.nesting_level
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_With(self, node):
        """Context managers: +1 (no nesting penalty per SonarSource)."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        """Binary logical operators (and/or): +1 per operator."""
        # Each additional operand adds complexity
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_Lambda(self, node):
        """Lambda expressions: +1."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ListComp(self, node):
        """List comprehensions: +1 per generator."""
        self.complexity += len(node.generators)
        self.generic_visit(node)

    def visit_DictComp(self, node):
        """Dict comprehensions: +1 per generator."""
        self.complexity += len(node.generators)
        self.generic_visit(node)

    def visit_SetComp(self, node):
        """Set comprehensions: +1 per generator."""
        self.complexity += len(node.generators)
        self.generic_visit(node)

    def visit_Call(self, node):
        """Detect recursive calls: +1 for recursion."""
        if isinstance(node.func, ast.Name):
            if node.func.id == self.current_function:
                self.complexity += 1  # Recursion penalty
        self.generic_visit(node)

    def visit_Break(self, node):
        """Break statements: +1 (jump)."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_Continue(self, node):
        """Continue statements: +1 (jump)."""
        self.complexity += 1
        self.generic_visit(node)


class NestingDepthAnalyzer(ast.NodeVisitor):
    """Analyze nesting depth of code structures.

    Based on Alrasheed (2022) research showing nesting depth > 4-5
    significantly impacts code comprehension and error rates.

    Threshold: 4-5 levels (Klocwork 2024, SAP guidelines)
    Maximum: 256 (technical limit, but 5 is recommended)
    """

    def __init__(self):
        self.max_depth = 0
        self.current_depth = 0
        self.depth_counts = defaultdict(int)

    def _enter_block(self):
        """Enter a nested block."""
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.depth_counts[self.current_depth] += 1

    def _exit_block(self):
        """Exit a nested block."""
        self.current_depth -= 1

    def visit_If(self, node):
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_For(self, node):
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_While(self, node):
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_With(self, node):
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_Try(self, node):
        self._enter_block()
        self.generic_visit(node)
        self._exit_block()

    def visit_FunctionDef(self, node):
        # Don't count function definition as nesting
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        # Don't count async function definition as nesting
        self.generic_visit(node)


class NPATHComplexityCalculator(ast.NodeVisitor):
    """Calculate NPATH complexity - acyclic execution path count.

    Based on Nejmeh (1988) from AT&T Bell Labs.
    NPATH counts the number of acyclic execution paths through a function.

    Threshold: 200 (established by AT&T Bell Labs empirical studies)

    Formula:
    - Sequential statements: multiply
    - If: 1 + NPATH(if_body) + NPATH(else_body)
    - While/For: 1 + NPATH(body)
    - Case: 1 + sum(NPATH(case_i))
    """

    def __init__(self):
        self.npath = 1

    def visit_If(self, node):
        """If statement: 1 + if_branch + else_branch."""
        if_visitor = NPATHComplexityCalculator()
        for stmt in node.body:
            if_visitor.visit(stmt)

        else_visitor = NPATHComplexityCalculator()
        for stmt in node.orelse:
            else_visitor.visit(stmt)

        self.npath += if_visitor.npath + else_visitor.npath

    def visit_For(self, node):
        """For loop: 1 + loop_body."""
        body_visitor = NPATHComplexityCalculator()
        for stmt in node.body:
            body_visitor.visit(stmt)

        self.npath += body_visitor.npath

    def visit_While(self, node):
        """While loop: 1 + loop_body."""
        body_visitor = NPATHComplexityCalculator()
        for stmt in node.body:
            body_visitor.visit(stmt)

        self.npath += body_visitor.npath

    def visit_Try(self, node):
        """Try block: sum of all branches."""
        # Try body
        try_visitor = NPATHComplexityCalculator()
        for stmt in node.body:
            try_visitor.visit(stmt)

        # Except handlers
        except_paths = 0
        for handler in node.handlers:
            handler_visitor = NPATHComplexityCalculator()
            for stmt in handler.body:
                handler_visitor.visit(stmt)
            except_paths += handler_visitor.npath

        # Finally (always executes)
        finally_visitor = NPATHComplexityCalculator()
        for stmt in node.finalbody:
            finally_visitor.visit(stmt)

        self.npath += try_visitor.npath + except_paths + finally_visitor.npath

    def visit_BoolOp(self, node):
        """Boolean operators create branches."""
        self.npath *= len(node.values)


class EssentialComplexityCalculator:
    """Calculate essential complexity (McCabe).

    Essential complexity measures non-structured code complexity.
    It's the cyclomatic complexity after removing all structured constructs.

    For structured programs: essential complexity = 1
    For non-structured programs: essential complexity > 1

    High essential complexity indicates goto-like behavior, deep nesting,
    or complex control flow that can't be simplified through refactoring.
    """

    @staticmethod
    def calculate(tree: ast.AST, cyclomatic: int) -> int:
        """Calculate essential complexity.

        Approximation: EC = CC - number_of_structured_constructs + 1
        For well-structured code, this should be close to 1.
        """
        # Count structured constructs
        structured_count = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                structured_count += 1

        # Essential complexity approximation
        essential = max(1, cyclomatic - structured_count + 1)
        return essential


class ComplexityAnalyzer(BaseAnalyzer):
    """State-of-the-art code complexity analyzer using complementary metrics.

    Implements 7 complementary complexity metrics based on 2024-2025 research:
    1. Cyclomatic Complexity (McCabe) - control flow paths
    2. Halstead Metrics Suite - program volume, difficulty, effort, bugs
    3. Cognitive Complexity - human readability (SonarSource)
    4. Nesting Depth - structural complexity
    5. Essential Complexity - non-structured code measure
    6. NPATH Complexity - acyclic execution paths
    7. Maintainability Index - composite metric

    Research-validated thresholds:
    - Cyclomatic: ≤ 10 (McCabe, validated 2024)
    - Cognitive: ≤ 15 (SonarSource)
    - Nesting: ≤ 4-5 levels (Alrasheed 2022, Klocwork 2024)
    - NPATH: ≤ 200 (Nejmeh 1988, AT&T)
    - Halstead Difficulty: ≤ 20
    - Halstead Volume: 20-1000 (function), 100-8000 (file)
    - Halstead Bugs: ≤ 2 (delivered bugs)
    """

    @property
    def name(self) -> str:
        return "complexity"

    @property
    def version(self) -> str:
        return "2.0.0"

    async def analyze(self, context: AnalysisContext) -> AnalysisResult:
        """Analyze code complexity using complementary metrics.

        Args:
            context: Analysis context with files to analyze

        Returns:
            Analysis result with 10+ complexity metrics
        """
        start_time = time.time()
        issues = []

        # Metric accumulators
        total_cyclomatic = 0
        total_cognitive = 0
        total_essential = 0
        total_npath = 0
        total_functions = 0

        max_cyclomatic = 0
        max_cognitive = 0
        max_nesting = 0
        max_npath = 0

        # Halstead accumulators
        total_halstead_volume = 0
        total_halstead_difficulty = 0
        total_halstead_effort = 0
        total_halstead_bugs = 0
        total_halstead_time = 0
        halstead_count = 0

        # File-level metrics
        high_complexity_files = 0
        deeply_nested_files = 0

        for file_path in context.files:
            if not self.should_analyze_file(file_path):
                continue

            code = read_file_safe(file_path)
            if not code:
                continue

            # Parse AST
            tree = parse_python_file(file_path)
            if not tree:
                continue

            # ===== 1. CYCLOMATIC COMPLEXITY (McCabe) =====
            try:
                cc_results = cc_visit(code)
                file_cyclomatic = 0

                for item in cc_results:
                    total_cyclomatic += item.complexity
                    total_functions += 1
                    file_cyclomatic += item.complexity
                    max_cyclomatic = max(max_cyclomatic, item.complexity)

                    # Threshold: 10 (McCabe, validated 2024)
                    threshold = self.get_threshold("cyclomatic_complexity") or 10

                    if item.complexity > threshold:
                        severity = Severity.HIGH if item.complexity > threshold * 2 else Severity.MEDIUM
                        issues.append(
                            Issue(
                                severity=severity,
                                category=IssueCategory.COMPLEXITY,
                                title=f"High cyclomatic complexity in '{item.name}'",
                                description=f"Cyclomatic complexity is {item.complexity} (threshold: {threshold}). "
                                            f"Research shows CC > 10 significantly increases defect probability.",
                                file_path=file_path,
                                line_number=item.lineno,
                                suggestion="Break this function into smaller, single-purpose functions. "
                                          "Reduce conditional branches and loops.",
                                rule_id="COMPLEXITY001",
                            )
                        )

                    # Calculate essential complexity
                    essential = EssentialComplexityCalculator.calculate(tree, item.complexity)
                    total_essential += essential

                    if essential > 4:
                        issues.append(
                            Issue(
                                severity=Severity.MEDIUM,
                                category=IssueCategory.COMPLEXITY,
                                title=f"High essential complexity in '{item.name}'",
                                description=f"Essential complexity is {essential}. Code has non-structured constructs.",
                                file_path=file_path,
                                line_number=item.lineno,
                                suggestion="Simplify control flow. Remove goto-like behavior and reduce nesting.",
                                rule_id="COMPLEXITY006",
                            )
                        )

            except Exception:
                pass

            # ===== 2. HALSTEAD METRICS SUITE =====
            try:
                halstead_results = h_visit(code)
                if halstead_results and len(halstead_results) > 0:
                    h = halstead_results[0]

                    total_halstead_volume += h.volume
                    total_halstead_difficulty += h.difficulty
                    total_halstead_effort += h.effort
                    total_halstead_bugs += h.bugs
                    total_halstead_time += h.time
                    halstead_count += 1

                    # Volume threshold: 20-1000 (function), 100-8000 (file)
                    if h.volume > 8000:
                        issues.append(
                            Issue(
                                severity=Severity.MEDIUM,
                                category=IssueCategory.COMPLEXITY,
                                title=f"Excessive Halstead volume in {file_path.name}",
                                description=f"Halstead volume is {h.volume:.0f} (threshold: 8000). "
                                            f"File is too large and information-dense.",
                                file_path=file_path,
                                suggestion="Split this file into smaller, focused modules. "
                                          "Current size: {h.volume:.0f} bits of information.",
                                rule_id="COMPLEXITY004",
                            )
                        )

                    # Difficulty threshold: ≤ 20
                    difficulty_threshold = self.get_threshold("halstead_difficulty") or 20
                    if h.difficulty > difficulty_threshold:
                        issues.append(
                            Issue(
                                severity=Severity.MEDIUM,
                                category=IssueCategory.COMPLEXITY,
                                title=f"High Halstead difficulty in {file_path.name}",
                                description=f"Halstead difficulty is {h.difficulty:.2f} (threshold: {difficulty_threshold}). "
                                            f"Code is error-prone and hard to maintain.",
                                file_path=file_path,
                                suggestion="Reduce unique operators and improve operand usage patterns. "
                                          "Simplify expressions and reduce operator diversity.",
                                rule_id="COMPLEXITY002",
                            )
                        )

                    # Bugs threshold: ≤ 2
                    if h.bugs > 2:
                        issues.append(
                            Issue(
                                severity=Severity.HIGH,
                                category=IssueCategory.COMPLEXITY,
                                title=f"High predicted bug count in {file_path.name}",
                                description=f"Halstead predicts {h.bugs:.2f} bugs (threshold: 2.0). "
                                            f"Effort: {h.effort:.0f}, Time: {h.time:.1f}s",
                                file_path=file_path,
                                suggestion=f"Predicted bugs based on complexity. Review and test thoroughly. "
                                          f"Consider refactoring to reduce effort from {h.effort:.0f}.",
                                rule_id="COMPLEXITY007",
                            )
                        )

                    # Effort threshold for informational
                    if h.effort > 100000:
                        issues.append(
                            Issue(
                                severity=Severity.LOW,
                                category=IssueCategory.COMPLEXITY,
                                title=f"High implementation effort in {file_path.name}",
                                description=f"Halstead effort is {h.effort:.0f} (estimated time: {h.time:.1f}s). "
                                            f"Code requires significant mental effort to understand.",
                                file_path=file_path,
                                suggestion="Consider adding comprehensive documentation and tests for this complex code.",
                                rule_id="COMPLEXITY008",
                            )
                        )

            except Exception:
                pass

            # ===== 3. COGNITIVE COMPLEXITY (SonarSource) =====
            try:
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        visitor = EnhancedCognitiveComplexityVisitor()
                        visitor.visit(node)
                        func_cognitive = visitor.complexity

                        total_cognitive += func_cognitive
                        max_cognitive = max(max_cognitive, func_cognitive)

                        # Threshold: 15 (SonarSource)
                        cognitive_threshold = self.get_threshold("cognitive_complexity") or 15

                        if func_cognitive > cognitive_threshold:
                            severity = Severity.HIGH if func_cognitive > cognitive_threshold * 2 else Severity.MEDIUM
                            issues.append(
                                Issue(
                                    severity=severity,
                                    category=IssueCategory.COMPLEXITY,
                                    title=f"High cognitive complexity in '{node.name}'",
                                    description=f"Cognitive complexity is {func_cognitive} (threshold: {cognitive_threshold}). "
                                                f"Code is hard for humans to understand (research-validated).",
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    suggestion="Reduce nesting depth and logical operators. Use early returns. "
                                              "Extract nested logic into helper functions.",
                                    rule_id="COMPLEXITY003",
                                )
                            )

                        # ===== 6. NPATH COMPLEXITY =====
                        npath_visitor = NPATHComplexityCalculator()
                        npath_visitor.visit(node)
                        func_npath = npath_visitor.npath

                        total_npath += func_npath
                        max_npath = max(max_npath, func_npath)

                        # Threshold: 200 (AT&T Bell Labs)
                        npath_threshold = self.get_threshold("npath_complexity") or 200

                        if func_npath > npath_threshold:
                            issues.append(
                                Issue(
                                    severity=Severity.HIGH,
                                    category=IssueCategory.COMPLEXITY,
                                    title=f"Excessive execution paths in '{node.name}'",
                                    description=f"NPATH complexity is {func_npath} (threshold: {npath_threshold}). "
                                                f"Function has {func_npath} possible execution paths - untestable.",
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    suggestion=f"Reduce from {func_npath} to <200 paths. Simplify conditional logic, "
                                              f"reduce nested branches, and extract complex logic.",
                                    rule_id="COMPLEXITY009",
                                )
                            )

            except Exception:
                pass

            # ===== 4. NESTING DEPTH ANALYSIS =====
            try:
                nesting_analyzer = NestingDepthAnalyzer()
                nesting_analyzer.visit(tree)
                file_max_nesting = nesting_analyzer.max_depth
                max_nesting = max(max_nesting, file_max_nesting)

                # Threshold: 4-5 levels (Alrasheed 2022, Klocwork 2024)
                nesting_threshold = self.get_threshold("max_nesting_depth") or 4

                if file_max_nesting > nesting_threshold:
                    deeply_nested_files += 1
                    severity = Severity.HIGH if file_max_nesting > 6 else Severity.MEDIUM
                    issues.append(
                        Issue(
                            severity=severity,
                            category=IssueCategory.COMPLEXITY,
                            title=f"Excessive nesting depth in {file_path.name}",
                            description=f"Maximum nesting depth is {file_max_nesting} (threshold: {nesting_threshold}). "
                                        f"Research shows nesting > 4 significantly impairs comprehension (Alrasheed 2022).",
                            file_path=file_path,
                            suggestion=f"Reduce nesting from {file_max_nesting} to ≤{nesting_threshold} levels. "
                                      f"Use early returns, guard clauses, and extract nested blocks to functions.",
                            rule_id="COMPLEXITY005",
                        )
                    )

            except Exception:
                pass

        # ===== CALCULATE AVERAGES AND METRICS =====
        avg_cyclomatic = total_cyclomatic / total_functions if total_functions > 0 else 0
        avg_cognitive = total_cognitive / total_functions if total_functions > 0 else 0
        avg_essential = total_essential / total_functions if total_functions > 0 else 0
        avg_npath = total_npath / total_functions if total_functions > 0 else 0

        avg_halstead_volume = total_halstead_volume / halstead_count if halstead_count > 0 else 0
        avg_halstead_difficulty = total_halstead_difficulty / halstead_count if halstead_count > 0 else 0
        avg_halstead_effort = total_halstead_effort / halstead_count if halstead_count > 0 else 0
        avg_halstead_bugs = total_halstead_bugs / halstead_count if halstead_count > 0 else 0
        avg_halstead_time = total_halstead_time / halstead_count if halstead_count > 0 else 0

        # Build metrics dictionary (10 core metrics)
        metrics = {
            "average_cyclomatic_complexity": MetricValue(
                name="average_cyclomatic_complexity",
                value=round(avg_cyclomatic, 2),
                threshold=self.get_threshold("cyclomatic_complexity") or 10,
                passed=avg_cyclomatic <= (self.get_threshold("cyclomatic_complexity") or 10),
            ),
            "max_cyclomatic_complexity": MetricValue(
                name="max_cyclomatic_complexity",
                value=max_cyclomatic,
                threshold=self.get_threshold("cyclomatic_complexity") or 10,
                passed=max_cyclomatic <= (self.get_threshold("cyclomatic_complexity") or 10),
            ),
            "average_cognitive_complexity": MetricValue(
                name="average_cognitive_complexity",
                value=round(avg_cognitive, 2),
                threshold=self.get_threshold("cognitive_complexity") or 15,
                passed=avg_cognitive <= (self.get_threshold("cognitive_complexity") or 15),
            ),
            "max_cognitive_complexity": MetricValue(
                name="max_cognitive_complexity",
                value=max_cognitive,
                threshold=self.get_threshold("cognitive_complexity") or 15,
                passed=max_cognitive <= (self.get_threshold("cognitive_complexity") or 15),
            ),
            "average_essential_complexity": MetricValue(
                name="average_essential_complexity",
                value=round(avg_essential, 2),
                threshold=4.0,
                passed=avg_essential <= 4.0,
            ),
            "max_nesting_depth": MetricValue(
                name="max_nesting_depth",
                value=max_nesting,
                threshold=self.get_threshold("max_nesting_depth") or 4,
                passed=max_nesting <= (self.get_threshold("max_nesting_depth") or 4),
            ),
            "average_npath_complexity": MetricValue(
                name="average_npath_complexity",
                value=round(avg_npath, 2),
                threshold=self.get_threshold("npath_complexity") or 200,
                passed=avg_npath <= (self.get_threshold("npath_complexity") or 200),
            ),
            "max_npath_complexity": MetricValue(
                name="max_npath_complexity",
                value=max_npath,
                threshold=self.get_threshold("npath_complexity") or 200,
                passed=max_npath <= (self.get_threshold("npath_complexity") or 200),
            ),
            "average_halstead_volume": MetricValue(
                name="average_halstead_volume",
                value=round(avg_halstead_volume, 2),
                threshold=8000.0,
                passed=avg_halstead_volume <= 8000.0,
            ),
            "average_halstead_difficulty": MetricValue(
                name="average_halstead_difficulty",
                value=round(avg_halstead_difficulty, 2),
                threshold=self.get_threshold("halstead_difficulty") or 20,
                passed=avg_halstead_difficulty <= (self.get_threshold("halstead_difficulty") or 20),
            ),
            "average_halstead_effort": MetricValue(
                name="average_halstead_effort",
                value=round(avg_halstead_effort, 2),
            ),
            "average_halstead_bugs": MetricValue(
                name="average_halstead_bugs",
                value=round(avg_halstead_bugs, 3),
                threshold=2.0,
                passed=avg_halstead_bugs <= 2.0,
            ),
            "average_halstead_time": MetricValue(
                name="average_halstead_time",
                value=round(avg_halstead_time, 2),
                unit="seconds",
            ),
            "total_functions": MetricValue(
                name="total_functions",
                value=total_functions,
            ),
        }

        # Generate insights based on complementary metrics (Gao et al. 2025)
        insights = self._generate_insights(metrics, total_functions, deeply_nested_files)

        execution_time = time.time() - start_time

        return AnalysisResult(
            analyzer_name=self.name,
            analyzer_version=self.version,
            status=ResultStatus.SUCCESS,
            metrics=metrics,
            issues=issues,
            insights=insights,
            execution_time_seconds=execution_time,
        )

    def _generate_insights(
        self,
        metrics: Dict[str, MetricValue],
        total_functions: int,
        deeply_nested_files: int
    ) -> List[str]:
        """Generate insights using complementary metrics analysis.

        Based on Gao et al. (2025) finding that combining metrics provides
        better complexity assessment than any single metric.
        """
        insights = []

        # Cyclomatic complexity insights
        avg_cc = metrics["average_cyclomatic_complexity"].value
        max_cc = metrics["max_cyclomatic_complexity"].value

        if avg_cc <= 5:
            insights.append(f"Excellent cyclomatic complexity (avg: {avg_cc:.1f}). Code is well-structured.")
        elif avg_cc <= 10:
            insights.append(f"Good cyclomatic complexity (avg: {avg_cc:.1f}). Within McCabe threshold.")
        else:
            insights.append(f"High cyclomatic complexity (avg: {avg_cc:.1f}). Refactoring recommended.")

        # Cognitive complexity insights
        avg_cog = metrics["average_cognitive_complexity"].value
        if avg_cog <= 10:
            insights.append(f"Low cognitive load (avg: {avg_cog:.1f}). Code is readable.")
        elif avg_cog <= 15:
            insights.append(f"Moderate cognitive complexity (avg: {avg_cog:.1f}).")
        else:
            insights.append(f"High cognitive complexity (avg: {avg_cog:.1f}). Difficult to understand.")

        # Halstead insights
        avg_bugs = metrics["average_halstead_bugs"].value
        avg_effort = metrics["average_halstead_effort"].value

        if avg_bugs < 0.5:
            insights.append(f"Low predicted defect rate ({avg_bugs:.2f} bugs per file).")
        elif avg_bugs < 2.0:
            insights.append(f"Moderate predicted defects ({avg_bugs:.2f} bugs per file).")
        else:
            insights.append(f"High predicted defect rate ({avg_bugs:.2f} bugs per file). Thorough testing needed.")

        # Nesting depth insights
        max_nesting = metrics["max_nesting_depth"].value
        if max_nesting > 5:
            insights.append(f"Excessive nesting detected (max: {max_nesting} levels). {deeply_nested_files} files affected.")
        elif max_nesting > 4:
            insights.append(f"High nesting depth (max: {max_nesting}). Consider flattening structure.")

        # NPATH insights
        max_npath = metrics["max_npath_complexity"].value
        if max_npath > 1000:
            insights.append(f"Extremely high NPATH ({max_npath} paths). Comprehensive testing is impractical.")
        elif max_npath > 200:
            insights.append(f"High NPATH complexity ({max_npath} paths). Testing will be challenging.")

        # Complementary analysis (Gao et al. 2025)
        # High CC + High Cognitive = True complexity problem
        if avg_cc > 10 and avg_cog > 15:
            insights.append("⚠️ Both cyclomatic and cognitive complexity are high. Immediate refactoring required.")

        # High Essential Complexity = Non-structured code
        avg_essential = metrics["average_essential_complexity"].value
        if avg_essential > 2:
            insights.append(f"High essential complexity ({avg_essential:.1f}). Code has non-structured patterns.")

        # Overall health assessment
        if total_functions > 0:
            insights.append(f"Analyzed {total_functions} functions across project.")

        return insights
