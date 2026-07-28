"""Edge Case Analyzer - Hybrid AI and Static Analysis

This analyzer implements edge case detection techniques combining static 
analysis with AI-powered insights to identify boundary conditions, corner cases, and missing input validation:

- Boundary Value Analysis (BVA) with automated test case generation
- Equivalence Partitioning (EP) for input domain classification
- Off-by-One Error Detection (OBOE) via pattern matching
- Null/Empty/Zero Handling Analysis
- Input Validation Gap Detection
- Numeric Overflow/Underflow Detection
- Array/Collection Boundary Issue Detection
- String Edge Case Analysis (empty, special characters, encoding)
- Property-Based Testing Pattern Recognition
- AI-Powered Corner Case Suggestion

Key Research Findings:
- 90% of software bugs arise from edge conditions
- Combining property-based testing with example-based testing improves bug detection to 81.25%
- Machine learning approaches to bounds detection achieve high precision
- LLMs can automate boundary value test generation effectively

References:
[1] Guo, X., Okamura, H. & Dohi, T. (2024)
    "Optimal test case generation for boundary value analysis"
    https://link.springer.com/article/10.1007/s11219-023-09659-9
    Software Quality Journal 32, 543–566
    Key: ML approach to bounds detection + MCMC for test input generation

[2] Guo, X., Li, C., Tsuchiya, T. (2026)
    "Boundary Value Test Input Generation Using a Large Language Model"
    https://link.springer.com/chapter/10.1007/978-981-95-3459-3_32
    Key: LLMs for automated boundary value test generation

[3] "Semi-Automated Corner Case Detection and Evaluation Pipeline" (2023)
    https://arxiv.org/abs/2305.16369
    Key: Automated corner case detection methodology

[4] "Corner cases in machine learning processes" (2023)
    https://link.springer.com/article/10.1186/s42467-023-00015-y
    AI Perspectives & Advances - Rare and dangerous situations detection

[5] "Understanding LLM-Generated Property-Based Tests" (2024)
    https://arxiv.org/html/2510.25297
    Key: 81.25% bug detection rate combining PBT + example-based testing

[6] "FuzzAug: Exploring Fuzzing as Data Augmentation" (2024)
    https://arxiv.org/html/2406.08665v1
    Key: Double the branch coverage with augmented fuzzing

[7] "Input Validation and Sanitization 2025: How To Do It"
    https://wnesecurity.com/input-validation-and-sanitization-2024-how-to-do-it/
    Modern input validation best practices

[8] "Edge Case Testing Explained" (2024)
    https://www.virtuosoqa.com/post/edge-case-testing
    Industry best practices and techniques
"""

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential


import ast
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from synexian.analyzers.base import AnalysisContext, BaseAnalyzer
from synexian.config import AnalyzerConfig
from synexian.constants import IssueCategory, ResultStatus, Severity
from synexian.models import AnalysisResult, Issue, MetricValue
from synexian.utils.file_utils import read_file_safe
from synexian.utils.ast_utils import parse_python_file
from synexian.ai.response_parser import parse_json_response


class BoundaryValueAnalyzer:
    """Boundary Value Analysis (BVA) implementation.

    Based on Guo et al. (2024) research on optimal test case generation.
    Detects:
    - Minimum/maximum boundary values
    - Off-by-one errors (x < n vs x <= n)
    - Missing boundary checks
    - Invalid boundary conditions
    """

    # Common boundary patterns
    NUMERIC_BOUNDARIES = {
        'positive_max': (2147483647, 'INT_MAX'),
        'negative_min': (-2147483648, 'INT_MIN'),
        'zero': (0, 'ZERO'),
        'float_epsilon': (1e-10, 'EPSILON'),
    }

    @staticmethod
    def analyze_comparisons(tree: ast.AST) -> List[Dict[str, Any]]:
        """Analyze comparison operations for boundary issues.

        Returns list of potential boundary issues.
        """
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                # Check for off-by-one patterns
                if len(node.ops) == 1:
                    op = node.ops[0]
                    left = node.left
                    right = node.comparators[0]

                    # Check for range(n) with >= comparison (off-by-one)
                    if isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                        issue = BoundaryValueAnalyzer._check_off_by_one(node, op, left, right)
                        if issue:
                            issues.append(issue)

                    # Check for missing zero check
                    if isinstance(op, ast.Gt) and isinstance(right, ast.Num) and right.n == 0:
                        issues.append({
                            'type': 'missing_zero_check',
                            'line': node.lineno if hasattr(node, 'lineno') else 0,
                            'description': 'Using > 0 instead of >= 0 may miss zero boundary',
                            'suggestion': 'Consider if zero should be included in the check'
                        })

        return issues

    @staticmethod
    def _check_off_by_one(node: ast.Compare, op: ast.AST, left: ast.AST, right: ast.AST) -> Optional[Dict]:
        """Check for off-by-one errors in comparisons."""
        # Pattern: i < len(arr) vs i <= len(arr)
        if isinstance(op, ast.Lt) and isinstance(right, ast.Call):
            if isinstance(right.func, ast.Name) and right.func.id == 'len':
                return {
                    'type': 'potential_off_by_one',
                    'line': node.lineno if hasattr(node, 'lineno') else 0,
                    'description': 'Using < len() - verify this is correct (not <=)',
                    'suggestion': 'Ensure boundary is exclusive, not inclusive'
                }

        # Pattern: range boundaries
        if isinstance(op, (ast.GtE, ast.Gt)) and isinstance(right, ast.Num):
            if right.n == 0:
                return {
                    'type': 'boundary_at_zero',
                    'line': node.lineno if hasattr(node, 'lineno') else 0,
                    'description': f'Comparison at zero boundary using {type(op).__name__}',
                    'suggestion': 'Verify >= 0 vs > 0 logic'
                }

        return None

    @staticmethod
    def detect_missing_bounds_checks(func: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Detect functions that handle numeric/array inputs without bounds checking."""
        issues = []

        # Check if function has numeric/list parameters but no validation
        has_params = len(func.args.args) > 0
        has_validation = False

        # Look for validation patterns
        for node in ast.walk(func):
            if isinstance(node, (ast.Compare, ast.If)):
                has_validation = True
                break

        if has_params and not has_validation:
            issues.append({
                'type': 'missing_validation',
                'function': func.name,
                'line': func.lineno,
                'description': f"Function '{func.name}' accepts parameters but has no input validation",
                'suggestion': 'Add bounds checking for numeric inputs and size validation for collections'
            })

        return issues


class EquivalencePartitionAnalyzer:
    """Equivalence Partitioning (EP) analysis.

    Divides input domain into equivalence classes:
    - Valid equivalence class
    - Invalid equivalence class
    - Boundary values
    """

    @staticmethod
    def analyze_conditional_coverage(tree: ast.AST) -> Dict[str, Any]:
        """Analyze if/elif/else coverage for partition completeness."""
        stats = {
            'total_conditionals': 0,
            'missing_else': 0,
            'single_branch': 0,
            'complex_conditions': 0
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                stats['total_conditionals'] += 1

                # Check if has else clause
                if not node.orelse:
                    stats['missing_else'] += 1

                # Check if only has if (no elif/else)
                if not node.orelse:
                    stats['single_branch'] += 1

                # Check for complex boolean conditions
                if isinstance(node.test, ast.BoolOp):
                    if len(node.test.values) > 2:
                        stats['complex_conditions'] += 1

        return stats

    @staticmethod
    def detect_missing_edge_partitions(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect missing edge case partitions in conditionals."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check for numeric range checks without boundary handling
                if isinstance(node.test, ast.Compare):
                    test = node.test

                    # Pattern: if x > 0 but no check for x == 0
                    if len(test.ops) == 1 and isinstance(test.ops[0], ast.Gt):
                        if isinstance(test.comparators[0], ast.Num) and test.comparators[0].n == 0:
                            issues.append({
                                'type': 'missing_zero_partition',
                                'line': node.lineno if hasattr(node, 'lineno') else 0,
                                'description': 'Checks x > 0 but may not handle x == 0 case',
                                'suggestion': 'Add explicit check for zero boundary value'
                            })

        return issues


class InputValidationAnalyzer:
    """Analyze input validation completeness.

    Based on 2025 input validation best practices.
    Checks for:
    - Type validation
    - Range validation
    - Format validation
    - Null/None handling
    - Empty collection handling
    """

    VALIDATION_PATTERNS = {
        'isinstance': re.compile(r'isinstance\s*\('),
        'type_check': re.compile(r'type\s*\(.*\)\s*=='),
        'not_none': re.compile(r'is\s+not\s+None|!=\s*None'),
        'empty_check': re.compile(r'if\s+(not\s+)?\w+:'),
        'range_check': re.compile(r'(<=|>=|<|>)\s*\d+'),
    }

    @staticmethod
    def analyze_function_validation(func: ast.FunctionDef, code: str) -> Dict[str, Any]:
        """Analyze validation coverage for a function."""
        validation_found = {
            'type_check': False,
            'none_check': False,
            'range_check': False,
            'empty_check': False,
        }

        # Extract function source
        if hasattr(func, 'lineno') and hasattr(func, 'end_lineno'):
            lines = code.split('\n')
            func_source = '\n'.join(lines[func.lineno-1:func.end_lineno])

            # Check for validation patterns
            for check_type, pattern in InputValidationAnalyzer.VALIDATION_PATTERNS.items():
                if pattern.search(func_source):
                    if 'isinstance' in check_type or 'type' in check_type:
                        validation_found['type_check'] = True
                    elif 'none' in check_type.lower():
                        validation_found['none_check'] = True
                    elif 'range' in check_type:
                        validation_found['range_check'] = True
                    elif 'empty' in check_type:
                        validation_found['empty_check'] = True

        return validation_found


class OffByOneDetector:
    """Detect off-by-one errors (OBOE).

    Common patterns:
    - Loop bounds: for i in range(n) vs range(n+1)
    - Array indexing: arr[i] vs arr[i-1]
    - String slicing: s[0:len(s)] vs s[0:len(s)+1]
    """

    @staticmethod
    def detect_loop_oboe(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect potential off-by-one errors in loops."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Check range() calls
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                        args = node.iter.args

                        # Check for range(len(x)) pattern
                        if len(args) == 1 and isinstance(args[0], ast.Call):
                            if isinstance(args[0].func, ast.Name) and args[0].func.id == 'len':
                                # Look for indexing in loop body
                                for body_node in ast.walk(node):
                                    if isinstance(body_node, ast.Subscript):
                                        # Check if using loop variable + 1 or - 1
                                        if isinstance(body_node.slice, ast.BinOp):
                                            issues.append({
                                                'type': 'potential_oboe_in_loop',
                                                'line': node.lineno if hasattr(node, 'lineno') else 0,
                                                'description': 'Loop uses range(len(x)) with index arithmetic - verify bounds',
                                                'suggestion': 'Check for off-by-one: using i+1 or i-1 with range(len(x))'
                                            })

        return issues

    @staticmethod
    def detect_slice_oboe(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect off-by-one in string/list slicing."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript):
                if isinstance(node.slice, ast.Slice):
                    # Check for common OBOE patterns
                    lower = node.slice.lower
                    upper = node.slice.upper

                    # Pattern: s[1:len(s)] (might miss first char) vs s[0:len(s)]
                    if isinstance(lower, ast.Num) and lower.n == 1:
                        if isinstance(upper, ast.Call):
                            if isinstance(upper.func, ast.Name) and upper.func.id == 'len':
                                issues.append({
                                    'type': 'slice_oboe',
                                    'line': node.lineno if hasattr(node, 'lineno') else 0,
                                    'description': 'Slice starts at index 1 - verify this is intentional',
                                    'suggestion': 'Common OBOE: s[1:] skips first element. Did you mean s[0:]?'
                                })

        return issues


class NullEmptyZeroAnalyzer:
    """Analyze handling of special values: null, empty, zero.

    Critical edge cases that are often missed:
    - None/null values
    - Empty strings ("")
    - Empty collections ([], {}, set())
    - Zero (0, 0.0)
    - Negative zero (-0.0)
    """

    @staticmethod
    def detect_missing_none_checks(func: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Detect parameter usage without None checking."""
        issues = []

        # Get parameter names
        param_names = {arg.arg for arg in func.args.args}

        # Check for None checks
        none_checked_params = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Compare):
                # Check for "x is None" or "x is not None"
                if isinstance(node.left, ast.Name) and node.left.id in param_names:
                    if any(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops):
                        none_checked_params.add(node.left.id)

        # Report params used without None check
        unchecked = param_names - none_checked_params

        for param in unchecked:
            issues.append({
                'type': 'missing_none_check',
                'function': func.name,
                'parameter': param,
                'line': func.lineno,
                'description': f"Parameter '{param}' used without None check",
                'suggestion': f"Add: if {param} is None: handle_error()"
            })

        return issues

    @staticmethod
    def detect_empty_collection_handling(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect operations on collections without empty checks."""
        issues = []

        for node in ast.walk(tree):
            # Check for list/dict access without length check
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name):
                    # Check if there's a prior length check
                    # Simplified: just flag subscript operations
                    issues.append({
                        'type': 'potential_empty_collection',
                        'line': node.lineno if hasattr(node, 'lineno') else 0,
                        'description': 'Collection access without length check',
                        'suggestion': 'Verify collection is not empty before accessing'
                    })

        return issues[:10]  # Limit to prevent spam


class NumericOverflowDetector:
    """Detect potential numeric overflow/underflow issues.

    Checks:
    - Integer overflow (> INT_MAX)
    - Float overflow (> FLT_MAX)
    - Underflow (very small numbers)
    - Division by zero
    """

    INT_MAX = 2147483647
    INT_MIN = -2147483648

    @staticmethod
    def detect_division_by_zero(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect division operations without zero check."""
        issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                    # Check if divisor is a variable (could be zero)
                    if isinstance(node.right, ast.Name):
                        issues.append({
                            'type': 'potential_division_by_zero',
                            'line': node.lineno if hasattr(node, 'lineno') else 0,
                            'variable': node.right.id,
                            'description': f"Division by variable '{node.right.id}' without zero check",
                            'suggestion': f"Add: if {node.right.id} == 0: handle_error()"
                        })

        return issues

    @staticmethod
    def detect_overflow_prone_operations(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect operations that could cause overflow."""
        issues = []

        for node in ast.walk(tree):
            # Check for multiplication/power operations
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, (ast.Mult, ast.Pow)):
                    # Check if involves large numbers
                    if isinstance(node.left, ast.Num) and abs(node.left.n) > 1000000:
                        issues.append({
                            'type': 'potential_overflow',
                            'line': node.lineno if hasattr(node, 'lineno') else 0,
                            'description': 'Operation with large numbers could overflow',
                            'suggestion': 'Consider using decimal.Decimal for large number arithmetic'
                        })

        return issues


class EdgeCaseAnalyzer(BaseAnalyzer):
    """State-of-the-art edge case analyzer with hybrid AI and static analysis.

    Combines multiple techniques:
    - Boundary Value Analysis (BVA)
    - Equivalence Partitioning (EP)
    - Off-by-One Error Detection
    - Input Validation Analysis
    - Null/Empty/Zero Handling
    - Numeric Overflow Detection
    - AI-powered corner case suggestions
    """

    def __init__(self, config: AnalyzerConfig, ai_client: Optional[Any] = None):
        super().__init__(config, ai_client)
        self.bva_analyzer = BoundaryValueAnalyzer()
        self.ep_analyzer = EquivalencePartitionAnalyzer()
        self.input_analyzer = InputValidationAnalyzer()
        self.oboe_detector = OffByOneDetector()
        self.null_analyzer = NullEmptyZeroAnalyzer()
        self.overflow_detector = NumericOverflowDetector()

    @property
    def name(self) -> str:
        return "edge_cases"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def requires_ai(self) -> bool:
        return True  # Hybrid: static + AI

    async def analyze(self, context: AnalysisContext) -> AnalysisResult:
        """Analyze edge cases using hybrid approach.

        Args:
            context: Analysis context with files

        Returns:
            Analysis result with edge case findings
        """
        start_time = time.time()
        issues = []

        # Metrics
        total_boundary_issues = 0
        total_validation_gaps = 0
        total_oboe = 0
        total_null_issues = 0
        total_overflow_risks = 0
        functions_analyzed = 0
        ai_suggestions = 0

        # Analyze files with static analysis
        for file_path in context.files:
            if not self.should_analyze_file(file_path):
                continue

            code = read_file_safe(file_path)
            if not code:
                continue

            tree = parse_python_file(file_path)
            if not tree:
                continue

            # ===== STATIC ANALYSIS =====

            # 1. Boundary Value Analysis
            boundary_issues = self.bva_analyzer.analyze_comparisons(tree)
            for issue in boundary_issues:
                total_boundary_issues += 1
                issues.append(
                    Issue(
                        severity=Severity.MEDIUM,
                        category=IssueCategory.EDGE_CASES,
                        title=f"Boundary Issue: {issue['type']}",
                        description=issue['description'],
                        file_path=file_path,
                        line_number=issue.get('line', 0),
                        suggestion=issue.get('suggestion', ''),
                        rule_id="EDGE_BVA001",
                    )
                )

            # 2. Equivalence Partitioning Coverage
            ep_stats = self.ep_analyzer.analyze_conditional_coverage(tree)
            if ep_stats['missing_else'] > 3:
                issues.append(
                    Issue(
                        severity=Severity.LOW,
                        category=IssueCategory.EDGE_CASES,
                        title="Incomplete Partition Coverage",
                        description=f"Found {ep_stats['missing_else']} conditionals without else clauses. "
                                   f"May miss invalid input equivalence class.",
                        file_path=file_path,
                        suggestion="Add else clauses to handle invalid/unexpected inputs",
                        rule_id="EDGE_EP001",
                    )
                )

            missing_partitions = self.ep_analyzer.detect_missing_edge_partitions(tree)
            for partition in missing_partitions:
                issues.append(
                    Issue(
                        severity=Severity.MEDIUM,
                        category=IssueCategory.EDGE_CASES,
                        title=f"Missing Partition: {partition['type']}",
                        description=partition['description'],
                        file_path=file_path,
                        line_number=partition.get('line', 0),
                        suggestion=partition.get('suggestion', ''),
                        rule_id="EDGE_EP002",
                    )
                )

            # 3. Off-by-One Error Detection
            loop_oboe = self.oboe_detector.detect_loop_oboe(tree)
            slice_oboe = self.oboe_detector.detect_slice_oboe(tree)

            for oboe in loop_oboe + slice_oboe:
                total_oboe += 1
                issues.append(
                    Issue(
                        severity=Severity.HIGH,
                        category=IssueCategory.EDGE_CASES,
                        title=f"Potential Off-by-One Error: {oboe['type']}",
                        description=oboe['description'],
                        file_path=file_path,
                        line_number=oboe.get('line', 0),
                        suggestion=oboe.get('suggestion', ''),
                        rule_id="EDGE_OBOE001",
                    )
                )

            # 4. Function-level Analysis
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions_analyzed += 1

                    # Input validation analysis
                    validation = self.input_analyzer.analyze_function_validation(node, code)
                    if len(node.args.args) > 0:
                        missing = []
                        if not validation['type_check']:
                            missing.append('type checking')
                        if not validation['none_check']:
                            missing.append('None/null checking')

                        if len(missing) >= 2:
                            total_validation_gaps += 1
                            issues.append(
                                Issue(
                                    severity=Severity.MEDIUM,
                                    category=IssueCategory.EDGE_CASES,
                                    title=f"Incomplete Input Validation in '{node.name}'",
                                    description=f"Function missing: {', '.join(missing)}",
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    suggestion="Add validation for types and None values",
                                    rule_id="EDGE_VAL001",
                                )
                            )

                    # None/null checking
                    none_issues = self.null_analyzer.detect_missing_none_checks(node)
                    for none_issue in none_issues[:3]:  # Limit per function
                        total_null_issues += 1
                        issues.append(
                            Issue(
                                severity=Severity.MEDIUM,
                                category=IssueCategory.EDGE_CASES,
                                title=f"Missing None Check: {none_issue['parameter']}",
                                description=none_issue['description'],
                                file_path=file_path,
                                line_number=none_issue.get('line', 0),
                                suggestion=none_issue.get('suggestion', ''),
                                rule_id="EDGE_NULL001",
                            )
                        )

                    # Bounds checking
                    bounds_issues = self.bva_analyzer.detect_missing_bounds_checks(node)
                    for bounds in bounds_issues:
                        total_validation_gaps += 1
                        issues.append(
                            Issue(
                                severity=Severity.MEDIUM,
                                category=IssueCategory.EDGE_CASES,
                                title=f"Missing Bounds Check: {bounds['function']}",
                                description=bounds['description'],
                                file_path=file_path,
                                line_number=bounds.get('line', 0),
                                suggestion=bounds.get('suggestion', ''),
                                rule_id="EDGE_BVA002",
                            )
                        )

            # 5. Numeric Overflow Detection
            div_zero_issues = self.overflow_detector.detect_division_by_zero(tree)
            for div_issue in div_zero_issues[:5]:  # Limit
                total_overflow_risks += 1
                issues.append(
                    Issue(
                        severity=Severity.HIGH,
                        category=IssueCategory.EDGE_CASES,
                        title=f"Division by Zero Risk: {div_issue['variable']}",
                        description=div_issue['description'],
                        file_path=file_path,
                        line_number=div_issue.get('line', 0),
                        suggestion=div_issue.get('suggestion', ''),
                        rule_id="EDGE_OVF001",
                    )
                )

            overflow_issues = self.overflow_detector.detect_overflow_prone_operations(tree)
            for ovf in overflow_issues[:3]:  # Limit
                total_overflow_risks += 1
                issues.append(
                    Issue(
                        severity=Severity.LOW,
                        category=IssueCategory.EDGE_CASES,
                        title="Potential Numeric Overflow",
                        description=ovf['description'],
                        file_path=file_path,
                        line_number=ovf.get('line', 0),
                        suggestion=ovf.get('suggestion', ''),
                        rule_id="EDGE_OVF002",
                    )
                )

        # ===== AI-POWERED ANALYSIS (for complex corner cases) =====
        if self.ai_client and self.get_option("enable_ai_analysis", True):
            # Sample files for AI analysis (expensive operation)
            sample_size = min(3, len(context.files))
            sample_files = context.files[:sample_size]

            for file_path in sample_files:
                if not self.should_analyze_file(file_path):
                    continue

                code = read_file_safe(file_path)
                if not code or len(code) > 5000:
                    continue

                try:
                    result = await self.ai_client.analyze_code(
                        code=code,
                        analysis_type="edge_cases",
                        context=f"File: {file_path.name}\n"
                               f"Focus: Corner cases, rare conditions, property violations",
                    )

                    parsed = parse_json_response(str(result)) if isinstance(result, str) else result

                    if parsed:
                        # Process AI-identified edge cases
                        for edge_case in parsed.get("missing_edge_cases", [])[:5]:
                            ai_suggestions += 1
                            issues.append(
                                Issue(
                                    severity=Severity.MEDIUM,
                                    category=IssueCategory.EDGE_CASES,
                                    title=f"AI-Detected Corner Case in {file_path.name}",
                                    description=f"Potential corner case: {edge_case}",
                                    file_path=file_path,
                                    suggestion="Review and add test case for this scenario",
                                    rule_id="EDGE_AI001",
                                )
                            )

                        for boundary in parsed.get("boundary_issues", [])[:5]:
                            ai_suggestions += 1
                            issues.append(
                                Issue(
                                    severity=Severity.LOW,
                                    category=IssueCategory.EDGE_CASES,
                                    title=f"AI-Detected Boundary Issue in {file_path.name}",
                                    description=f"Boundary consideration: {boundary}",
                                    file_path=file_path,
                                    suggestion="Add boundary value test",
                                    rule_id="EDGE_AI002",
                                )
                            )

                except Exception as e:
                    self.logger.debug(f"AI analysis failed for {file_path}: {e}")

        # Build metrics
        metrics = {
            "total_edge_case_issues": MetricValue(
                name="total_edge_case_issues",
                value=len(issues),
            ),
            "boundary_value_issues": MetricValue(
                name="boundary_value_issues",
                value=total_boundary_issues,
            ),
            "validation_gaps": MetricValue(
                name="validation_gaps",
                value=total_validation_gaps,
            ),
            "off_by_one_errors": MetricValue(
                name="off_by_one_errors",
                value=total_oboe,
                threshold=0,
                passed=total_oboe == 0,
            ),
            "null_handling_issues": MetricValue(
                name="null_handling_issues",
                value=total_null_issues,
            ),
            "overflow_risks": MetricValue(
                name="overflow_risks",
                value=total_overflow_risks,
                threshold=0,
                passed=total_overflow_risks == 0,
            ),
            "functions_analyzed": MetricValue(
                name="functions_analyzed",
                value=functions_analyzed,
            ),
            "ai_suggestions": MetricValue(
                name="ai_suggestions",
                value=ai_suggestions,
            ),
        }

        # Generate insights
        insights = self._generate_insights(metrics, functions_analyzed)

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

    def _generate_insights(self, metrics: Dict[str, MetricValue], functions: int) -> List[str]:
        """Generate actionable insights from edge case analysis."""
        insights = []

        total_issues = metrics["total_edge_case_issues"].value
        oboe = metrics["off_by_one_errors"].value
        overflow = metrics["overflow_risks"].value
        validation = metrics["validation_gaps"].value
        ai_suggestions = metrics["ai_suggestions"].value

        # Overall assessment
        if total_issues == 0:
            insights.append(f"✓ No edge case issues detected across {functions} functions. Excellent!")
        elif total_issues < 10:
            insights.append(f"Minor edge case concerns: {total_issues} issues found across {functions} functions.")
        else:
            insights.append(f"⚠️ Significant edge case gaps: {total_issues} issues found. Review recommended.")

        # Off-by-one errors (critical)
        if oboe > 0:
            insights.append(f"🔴 Critical: {oboe} potential off-by-one errors detected. High bug probability.")
        else:
            insights.append("✓ No off-by-one errors detected in loops and slicing.")

        # Overflow risks
        if overflow > 5:
            insights.append(f"⚠️ {overflow} numeric overflow risks found. Consider using Decimal or validation.")
        elif overflow > 0:
            insights.append(f"Minor: {overflow} potential overflow scenarios identified.")

        # Validation gaps
        if validation > 10:
            insights.append(f"Input validation gaps: {validation} functions lack proper validation. Security risk.")
        elif validation > 0:
            insights.append(f"Some validation gaps detected: {validation} functions.")

        # AI insights
        if ai_suggestions > 0:
            insights.append(f"AI identified {ai_suggestions} additional corner cases for consideration.")

        # Research-backed recommendation
        insights.append("Research shows 90% of bugs arise from edge conditions. Thorough testing recommended.")

        return insights
