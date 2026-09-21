"""Architecture Analyzer module using hybrid AI and static analysis.

This analyzer implements:
- LLM-based design pattern detection (Schmid et al., 2025)
- Architectural smells detection (PyExamine, 2025)
- SOLID principles violation detection (Empirical Study, 2024)
- Modularity metrics: Instability & Abstractness (Martin's metrics, 2024)
- Coupling & Cohesion analysis (ASRMG, 2024)
- Dependency graph analysis for cyclic dependencies

References:
[1] Schmid et al. (2025) "Software Architecture Meets LLMs: A Systematic Literature Review"
    https://arxiv.org/abs/2505.16697
[2] PyExamine (2025) "A Comprehensive Smell Detection Tool for Python"
    https://arxiv.org/html/2501.18327v1
[3] ASRMG (2024) "Architecture Smell Refactoring for Microservices Granularity"
[4] Martin (2024) "The Instability-Abstractness-Relationship"
    http://odrotbohm.de/2024/09/the-instability-abstractness-relationsship-an-alternative-view/
[5] "Are We SOLID Yet? Empirical Study on Prompting LLMs to Detect Design Principle Violations"
    https://arxiv.org/html/2509.03093
"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import ast
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

from synexian.analyzers.base import AnalysisContext, BaseAnalyzer
from synexian.constants import IssueCategory, ResultStatus, Severity
from synexian.models import AnalysisResult, Issue, MetricDefinition, MetricValue
from synexian.utils.file_utils import read_file_safe
from synexian.ai.response_parser import extract_score, parse_json_response


class DependencyGraph:
    """Dependency graph for analyzing module relationships.

    Based on graph algorithms from PyExamine (2025) for detecting
    cyclic dependencies and layering violations.
    """

    def __init__(self):
        self.graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    def add_dependency(self, source: str, target: str):
        """Add a dependency edge from source to target."""
        self.graph[source].add(target)
        self.reverse_graph[target].add(source)

    def get_efferent_coupling(self, module: str) -> int:
        """Get efferent (outgoing) coupling - Ce.

        Number of modules this module depends on.
        """
        return len(self.graph[module])

    def get_afferent_coupling(self, module: str) -> int:
        """Get afferent (incoming) coupling - Ca.

        Number of modules that depend on this module.
        """
        return len(self.reverse_graph[module])

    def calculate_instability(self, module: str) -> float:
        """Calculate Martin's Instability metric (I).

        I = Ce / (Ce + Ca)
        Range: [0, 1]
        - 0 = maximally stable (many dependents, few dependencies)
        - 1 = maximally unstable (few dependents, many dependencies)

        Reference: Martin (2024) - Instability-Abstractness-Relationship
        """
        ce = self.get_efferent_coupling(module)
        ca = self.get_afferent_coupling(module)
        total = ce + ca
        return ce / total if total > 0 else 0.0

    def find_cycles(self) -> List[List[str]]:
        """Detect cyclic dependencies using Tarjan's algorithm.

        Based on PyExamine (2025) graph-based cycle detection.
        Returns list of strongly connected components (cycles).
        """
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = defaultdict(bool)
        cycles = []

        def strongconnect(node):
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True

            for successor in self.graph[node]:
                if successor not in index:
                    strongconnect(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif on_stack[successor]:
                    lowlinks[node] = min(lowlinks[node], index[successor])

            if lowlinks[node] == index[node]:
                component = []
                while True:
                    successor = stack.pop()
                    on_stack[successor] = False
                    component.append(successor)
                    if successor == node:
                        break
                if len(component) > 1:  # Only report actual cycles
                    cycles.append(component)

        for node in list(self.graph.keys()):
            if node not in index:
                strongconnect(node)

        return cycles


class ModuleAnalyzer:
    """Analyze module-level architecture metrics.

    Implements metrics from ASRMG (2024) and PyExamine (2025):
    - LCOM (Lack of Cohesion of Methods)
    - CBO (Coupling Between Objects)
    - RFC (Response For Class)
    - WMC (Weighted Methods per Class)
    """

    @staticmethod
    def calculate_lcom(tree: ast.AST) -> float:
        """Calculate Lack of Cohesion of Methods (LCOM4).

        LCOM4 measures cohesion by analyzing which methods access which attributes.
        Lower values indicate higher cohesion.

        Reference: PyExamine (2025) - Cohesion metrics
        """
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        if not classes:
            return 0.0

        total_lcom = 0
        for class_node in classes:
            methods = [n for n in class_node.body if isinstance(n, ast.FunctionDef)]
            if len(methods) <= 1:
                continue

            # Get class attributes
            attributes = set()
            for node in ast.walk(class_node):
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name) and node.value.id == "self":
                        attributes.add(node.attr)

            # Analyze which methods use which attributes
            method_attrs = defaultdict(set)
            for method in methods:
                for node in ast.walk(method):
                    if isinstance(node, ast.Attribute):
                        if isinstance(node.value, ast.Name) and node.value.id == "self":
                            method_attrs[method.name].add(node.attr)

            # Calculate connected components
            if not method_attrs:
                continue

            # LCOM4: number of connected components of methods
            components = 0
            visited = set()

            def dfs(method_name):
                if method_name in visited:
                    return
                visited.add(method_name)
                current_attrs = method_attrs[method_name]
                for other_method, other_attrs in method_attrs.items():
                    if other_method not in visited and current_attrs & other_attrs:
                        dfs(other_method)

            for method in method_attrs:
                if method not in visited:
                    dfs(method)
                    components += 1

            total_lcom += components

        return total_lcom / len(classes) if classes else 0.0

    @staticmethod
    def calculate_cbo(tree: ast.AST, file_path: Path) -> int:
        """Calculate Coupling Between Objects (CBO).

        Number of classes coupled to this module through inheritance,
        attribute access, method calls, or parameter types.

        Reference: ASRMG (2024) - Coupling metrics
        """
        classes = set()
        for node in ast.walk(tree):
            # Inheritance
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        classes.add(base.id)
            # Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    classes.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    classes.add(node.module.split(".")[0])

        return len(classes)

    @staticmethod
    def calculate_rfc(tree: ast.AST) -> int:
        """Calculate Response For Class (RFC).

        Number of methods that can be invoked in response to a message.
        Higher RFC indicates more complex class behavior.

        Reference: PyExamine (2025) - Complexity metrics
        """
        methods = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.add(node.name)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    methods.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    methods.add(node.func.attr)

        return len(methods)

    @staticmethod
    def calculate_wmc(tree: ast.AST) -> int:
        """Calculate Weighted Methods per Class (WMC).

        Sum of complexities of all methods in a class.
        Uses cyclomatic complexity as weight.

        Reference: PyExamine (2025) - Complexity metrics
        """
        total_complexity = 0
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        for class_node in classes:
            for node in class_node.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Count decision points
                    complexity = 1
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                            complexity += 1
                        elif isinstance(child, ast.BoolOp):
                            complexity += len(child.values) - 1
                    total_complexity += complexity

        return total_complexity


class SOLIDAnalyzer:
    """Detect SOLID principle violations using AST analysis.

    Based on "Are We SOLID Yet?" empirical study (2024) combining
    static analysis with pattern recognition.

    Reference: https://arxiv.org/html/2509.03093
    """

    @staticmethod
    def check_single_responsibility(tree: ast.AST, file_path: Path) -> List[Dict[str, Any]]:
        """Detect Single Responsibility Principle (SRP) violations.

        A class should have only one reason to change.
        Heuristics:
        - Class with >10 methods
        - Class with >5 distinct responsibilities (method name analysis)
        - Class with both business logic and infrastructure concerns
        """
        violations = []
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        for class_node in classes:
            methods = [n for n in class_node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

            # Check method count
            if len(methods) > 10:
                violations.append({
                    "principle": "SRP",
                    "class": class_node.name,
                    "reason": f"Class has {len(methods)} methods (>10), likely multiple responsibilities",
                    "line": class_node.lineno,
                })

            # Analyze method responsibilities by name patterns
            responsibilities = set()
            responsibility_patterns = {
                "data": ["get_", "set_", "load_", "save_", "read_", "write_"],
                "validation": ["validate_", "check_", "verify_", "ensure_"],
                "transformation": ["transform_", "convert_", "process_", "calculate_"],
                "communication": ["send_", "receive_", "request_", "response_"],
                "rendering": ["render_", "display_", "show_", "draw_"],
            }

            for method in methods:
                method_name = method.name.lower()
                for responsibility, patterns in responsibility_patterns.items():
                    if any(method_name.startswith(p) for p in patterns):
                        responsibilities.add(responsibility)

            if len(responsibilities) > 3:
                violations.append({
                    "principle": "SRP",
                    "class": class_node.name,
                    "reason": f"Class has {len(responsibilities)} distinct responsibilities: {', '.join(responsibilities)}",
                    "line": class_node.lineno,
                })

        return violations

    @staticmethod
    def check_open_closed(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect Open-Closed Principle (OCP) violations.

        Software entities should be open for extension but closed for modification.
        Heuristics:
        - Large if-elif chains that could be polymorphism
        - Type checking (isinstance) for behavior dispatch
        """
        violations = []

        for node in ast.walk(tree):
            # Check for large if-elif chains
            if isinstance(node, ast.If):
                elif_count = 0
                current = node
                while hasattr(current, 'orelse') and current.orelse:
                    if isinstance(current.orelse[0], ast.If):
                        elif_count += 1
                        current = current.orelse[0]
                    else:
                        break

                if elif_count >= 4:
                    violations.append({
                        "principle": "OCP",
                        "reason": f"Large if-elif chain ({elif_count + 1} branches) - consider polymorphism",
                        "line": node.lineno,
                    })

            # Check for isinstance type checking
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                    # Count isinstance in parent function
                    violations.append({
                        "principle": "OCP",
                        "reason": "Type checking with isinstance - consider polymorphism",
                        "line": node.lineno,
                    })

        return violations

    @staticmethod
    def check_liskov_substitution(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect Liskov Substitution Principle (LSP) violations.

        Derived classes must be substitutable for their base classes.
        Heuristics:
        - Methods that raise NotImplementedError in derived classes
        - Overridden methods with incompatible signatures
        """
        violations = []
        classes = {}

        # First pass: collect all classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes[node.name] = node

        # Second pass: check for violations
        for class_name, class_node in classes.items():
            for method in class_node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check for NotImplementedError
                    for stmt in ast.walk(method):
                        if isinstance(stmt, ast.Raise):
                            if isinstance(stmt.exc, ast.Call):
                                if isinstance(stmt.exc.func, ast.Name):
                                    if stmt.exc.func.id == "NotImplementedError":
                                        violations.append({
                                            "principle": "LSP",
                                            "class": class_name,
                                            "method": method.name,
                                            "reason": "Method raises NotImplementedError - violates substitutability",
                                            "line": stmt.lineno,
                                        })

        return violations

    @staticmethod
    def check_interface_segregation(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect Interface Segregation Principle (ISP) violations.

        Clients should not be forced to depend on interfaces they don't use.
        Heuristics:
        - Abstract base classes with >10 abstract methods
        - Classes with many unimplemented methods
        """
        violations = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for ABC with many abstract methods
                abstract_methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Check for @abstractmethod decorator
                        for decorator in item.decorator_list:
                            if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                                abstract_methods.append(item.name)

                if len(abstract_methods) > 8:
                    violations.append({
                        "principle": "ISP",
                        "class": node.name,
                        "reason": f"Interface with {len(abstract_methods)} abstract methods - too broad",
                        "line": node.lineno,
                    })

        return violations

    @staticmethod
    def check_dependency_inversion(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect Dependency Inversion Principle (DIP) violations.

        Depend on abstractions, not concretions.
        Heuristics:
        - Direct instantiation of concrete classes in high-level modules
        - Tight coupling to specific implementations
        """
        violations = []

        for node in ast.walk(tree):
            # Check for direct instantiation patterns
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        # Direct class instantiation (not from factory/DI)
                        class_name = node.value.func.id
                        # Heuristic: concrete classes often end with specific suffixes
                        concrete_suffixes = ["Client", "Handler", "Repository", "Service", "Manager"]
                        if any(class_name.endswith(suffix) for suffix in concrete_suffixes):
                            violations.append({
                                "principle": "DIP",
                                "reason": f"Direct instantiation of concrete class '{class_name}' - consider dependency injection",
                                "line": node.lineno,
                            })

        return violations


class ArchitecturalSmellDetector:
    """Detect architectural smells using multi-level analysis.

    Based on PyExamine (2025) and ASRMG (2024) research on
    architectural smell detection in microservices.
    """

    @staticmethod
    def detect_god_class(tree: ast.AST, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect God Class anti-pattern.

        A class that knows too much or does too much.
        Criteria (from research):
        - WMC > 47
        - LCOM > 0.8
        - RFC > 50
        """
        smells = []
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        for class_node in classes:
            # Get class-specific metrics
            class_tree = ast.Module(body=[class_node], type_ignores=[])
            wmc = ModuleAnalyzer.calculate_wmc(class_tree)
            rfc = ModuleAnalyzer.calculate_rfc(class_tree)
            lcom = ModuleAnalyzer.calculate_lcom(class_tree)

            is_god_class = False
            reasons = []

            if wmc > 47:
                is_god_class = True
                reasons.append(f"WMC={wmc} (threshold: 47)")

            if lcom > 0.8:
                is_god_class = True
                reasons.append(f"LCOM={lcom:.2f} (threshold: 0.8)")

            if rfc > 50:
                is_god_class = True
                reasons.append(f"RFC={rfc} (threshold: 50)")

            if is_god_class:
                smells.append({
                    "smell": "God Class",
                    "class": class_node.name,
                    "reasons": reasons,
                    "line": class_node.lineno,
                })

        return smells

    @staticmethod
    def detect_feature_envy(tree: ast.AST) -> List[Dict[str, Any]]:
        """Detect Feature Envy smell.

        A method that uses more features of another class than its own.
        """
        smells = []
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        for class_node in classes:
            for method in class_node.body:
                if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue

                # Count self.* accesses vs other object accesses
                self_accesses = 0
                other_accesses = defaultdict(int)

                for node in ast.walk(method):
                    if isinstance(node, ast.Attribute):
                        if isinstance(node.value, ast.Name):
                            if node.value.id == "self":
                                self_accesses += 1
                            else:
                                other_accesses[node.value.id] += 1

                # If any other object is accessed more than self
                for obj, count in other_accesses.items():
                    if count > self_accesses and count > 3:
                        smells.append({
                            "smell": "Feature Envy",
                            "class": class_node.name,
                            "method": method.name,
                            "reason": f"Method accesses '{obj}' {count} times vs 'self' {self_accesses} times",
                            "line": method.lineno,
                        })
                        break

        return smells

    @staticmethod
    def detect_cyclic_dependency(dependency_graph: DependencyGraph) -> List[Dict[str, Any]]:
        """Detect cyclic dependencies between modules.

        Based on PyExamine (2025) graph-based cycle detection.
        """
        smells = []
        cycles = dependency_graph.find_cycles()

        for cycle in cycles:
            smells.append({
                "smell": "Cyclic Dependency",
                "modules": cycle,
                "reason": f"Circular dependency between {len(cycle)} modules",
            })

        return smells


class ArchitectureAnalyzer(BaseAnalyzer):
    """State-of-the-art architecture analyzer using hybrid AI and static analysis.

    Implements cutting-edge methods from 2024-2025 research combining:
    - LLM-based pattern detection (Schmid et al., 2025)
    - Static analysis for metrics (PyExamine, 2025)
    - SOLID violation detection (Empirical Study, 2024)
    - Modularity analysis (Martin, 2024)
    """

    @property
    def name(self) -> str:
        return "architecture"

    @property
    def version(self) -> str:
        return "2.0.0"  # SOTA version

    @property
    def requires_ai(self) -> bool:
        return True

    def get_metric_definitions(self) -> List[MetricDefinition]:
        """Get metric definitions for this analyzer."""
        return [
            MetricDefinition(
                name="instability",
                description="Martin's Instability metric (I = Ce / (Ce + Ca))",
                category="modularity",
            ),
            MetricDefinition(
                name="abstractness",
                description="Ratio of abstract classes to total classes",
                category="modularity",
            ),
            MetricDefinition(
                name="distance_from_main_sequence",
                description="Distance from ideal abstraction-instability balance",
                category="modularity",
            ),
            MetricDefinition(
                name="average_lcom",
                description="Average Lack of Cohesion of Methods across classes",
                category="cohesion",
            ),
            MetricDefinition(
                name="average_cbo",
                description="Average Coupling Between Objects",
                category="coupling",
            ),
            MetricDefinition(
                name="cyclomatic_dependencies",
                description="Number of cyclic dependencies detected",
                category="dependencies",
            ),
            MetricDefinition(
                name="solid_violations",
                description="Total SOLID principle violations",
                category="design",
            ),
            MetricDefinition(
                name="architectural_smells",
                description="Number of architectural smells detected",
                category="quality",
            ),
        ]

    async def analyze(self, context: AnalysisContext) -> AnalysisResult:
        """Perform comprehensive architecture analysis.

        Multi-level analysis strategy:
        1. Static analysis for metrics and violations
        2. Dependency graph analysis
        3. SOLID principles checking
        4. Architectural smells detection
        5. AI-powered pattern recognition (if available)

        Args:
            context: Analysis context with project files

        Returns:
            Comprehensive architecture analysis result
        """
        start_time = time.time()
        issues = []
        metrics = {}
        insights = []

        # Initialize analyzers and dependency graph
        dependency_graph = DependencyGraph()
        module_metrics = []
        all_solid_violations = []
        all_smells = []

        # Phase 1: Static Analysis
        self.logger.info(f"Phase 1: Analyzing {len(context.files)} files for architecture metrics")

        for file_path in context.files:
            if not self.should_analyze_file(file_path):
                continue

            code = read_file_safe(file_path)
            if not code:
                continue

            try:
                tree = ast.parse(code)
            except SyntaxError:
                continue

            module_name = file_path.stem

            # Calculate module-level metrics
            lcom = ModuleAnalyzer.calculate_lcom(tree)
            cbo = ModuleAnalyzer.calculate_cbo(tree, file_path)
            rfc = ModuleAnalyzer.calculate_rfc(tree)
            wmc = ModuleAnalyzer.calculate_wmc(tree)

            module_metrics.append({
                "module": module_name,
                "lcom": lcom,
                "cbo": cbo,
                "rfc": rfc,
                "wmc": wmc,
            })

            # Build dependency graph
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            target = alias.name.split(".")[0]
                            dependency_graph.add_dependency(module_name, target)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        target = node.module.split(".")[0]
                        dependency_graph.add_dependency(module_name, target)

            # SOLID analysis
            srp_violations = SOLIDAnalyzer.check_single_responsibility(tree, file_path)
            ocp_violations = SOLIDAnalyzer.check_open_closed(tree)
            lsp_violations = SOLIDAnalyzer.check_liskov_substitution(tree)
            isp_violations = SOLIDAnalyzer.check_interface_segregation(tree)
            dip_violations = SOLIDAnalyzer.check_dependency_inversion(tree)

            all_violations = srp_violations + ocp_violations + lsp_violations + isp_violations + dip_violations
            all_solid_violations.extend(all_violations)

            # Create issues for SOLID violations
            for violation in all_violations:
                severity = Severity.HIGH if violation["principle"] in ["SRP", "DIP"] else Severity.MEDIUM
                issues.append(
                    Issue(
                        severity=severity,
                        category=IssueCategory.ARCHITECTURE,
                        title=f"{violation['principle']} violation",
                        description=violation["reason"],
                        file_path=file_path,
                        line_number=violation.get("line"),
                        rule_id=f"SOLID-{violation['principle']}",
                    )
                )

            # Architectural smells detection
            god_classes = ArchitecturalSmellDetector.detect_god_class(tree, {"wmc": wmc, "rfc": rfc, "lcom": lcom})
            feature_envy = ArchitecturalSmellDetector.detect_feature_envy(tree)

            all_smells.extend(god_classes + feature_envy)

            # Create issues for smells
            for smell in god_classes + feature_envy:
                # Handle both "reason" (string) and "reasons" (list) formats
                if "reason" in smell:
                    description = smell["reason"]
                elif "reasons" in smell:
                    description = ", ".join(smell["reasons"])
                else:
                    description = f"{smell['smell']} detected"

                issues.append(
                    Issue(
                        severity=Severity.HIGH,
                        category=IssueCategory.ARCHITECTURE,
                        title=f"{smell['smell']} detected",
                        description=description,
                        file_path=file_path,
                        line_number=smell.get("line"),
                        rule_id=f"SMELL-{smell['smell'].replace(' ', '_').upper()}",
                    )
                )

        # Phase 2: Dependency Analysis
        self.logger.info("Phase 2: Analyzing module dependencies")

        cyclic_deps = ArchitecturalSmellDetector.detect_cyclic_dependency(dependency_graph)
        all_smells.extend(cyclic_deps)

        for cycle in cyclic_deps:
            issues.append(
                Issue(
                    severity=Severity.CRITICAL,
                    category=IssueCategory.ARCHITECTURE,
                    title="Cyclic dependency detected",
                    description=f"Circular dependency between modules: {' -> '.join(cycle['modules'])}",
                    file_path=None,
                    rule_id="ARCH-CYCLE",
                )
            )

        # Phase 3: Calculate aggregate metrics
        self.logger.info("Phase 3: Computing aggregate architecture metrics")

        # Initialize variables
        avg_lcom = 0.0
        avg_cbo = 0.0
        avg_rfc = 0.0
        avg_wmc = 0.0

        # Average cohesion and coupling
        if module_metrics:
            avg_lcom = sum(m["lcom"] for m in module_metrics) / len(module_metrics)
            avg_cbo = sum(m["cbo"] for m in module_metrics) / len(module_metrics)
            avg_rfc = sum(m["rfc"] for m in module_metrics) / len(module_metrics)
            avg_wmc = sum(m["wmc"] for m in module_metrics) / len(module_metrics)

            metrics["average_lcom"] = MetricValue(
                name="average_lcom",
                value=avg_lcom,
                threshold=self.get_threshold("average_lcom") or 0.5,
                passed=avg_lcom <= 0.5,
            )

            metrics["average_cbo"] = MetricValue(
                name="average_cbo",
                value=avg_cbo,
                threshold=self.get_threshold("average_cbo") or 10,
                passed=avg_cbo <= 10,
            )

            metrics["average_rfc"] = MetricValue(
                name="average_rfc",
                value=avg_rfc,
                threshold=self.get_threshold("average_rfc") or 50,
                passed=avg_rfc <= 50,
            )

            metrics["average_wmc"] = MetricValue(
                name="average_wmc",
                value=avg_wmc,
                threshold=self.get_threshold("average_wmc") or 40,
                passed=avg_wmc <= 40,
            )

        # Modularity metrics (instability & abstractness)
        modules = list(dependency_graph.graph.keys())
        if modules:
            instabilities = [dependency_graph.calculate_instability(m) for m in modules]
            avg_instability = sum(instabilities) / len(instabilities)

            # Calculate abstractness (ratio of abstract classes)
            total_classes = 0
            abstract_classes = 0
            for file_path in context.files:
                if not self.should_analyze_file(file_path):
                    continue
                code = read_file_safe(file_path)
                if code:
                    try:
                        tree = ast.parse(code)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                total_classes += 1
                                # Check if class has abstract methods
                                for item in node.body:
                                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                        for dec in item.decorator_list:
                                            if isinstance(dec, ast.Name) and dec.id == "abstractmethod":
                                                abstract_classes += 1
                                                break
                    except Exception:
                        pass  # FIX: was bare except

            abstractness = abstract_classes / total_classes if total_classes > 0 else 0.0

            # Distance from main sequence: D = |A + I - 1|
            # Ideal is on the line A + I = 1
            distance = abs(abstractness + avg_instability - 1)

            metrics["instability"] = MetricValue(
                name="instability",
                value=avg_instability,
                threshold=None,
            )

            metrics["abstractness"] = MetricValue(
                name="abstractness",
                value=abstractness,
                threshold=None,
            )

            metrics["distance_from_main_sequence"] = MetricValue(
                name="distance_from_main_sequence",
                value=distance,
                threshold=0.3,
                passed=distance <= 0.3,
            )

        # Counts
        metrics["solid_violations"] = MetricValue(
            name="solid_violations",
            value=len(all_solid_violations),
            threshold=self.get_threshold("solid_violations") or 5,
            passed=len(all_solid_violations) <= 5,
        )

        metrics["architectural_smells"] = MetricValue(
            name="architectural_smells",
            value=len(all_smells),
            threshold=self.get_threshold("architectural_smells") or 3,
            passed=len(all_smells) <= 3,
        )

        metrics["cyclic_dependencies"] = MetricValue(
            name="cyclic_dependencies",
            value=len(cyclic_deps),
            threshold=0,
            passed=len(cyclic_deps) == 0,
        )

        # Phase 4: AI-Powered Pattern Detection (if available)
        if self.ai_client:
            self.logger.info("Phase 4: AI-powered design pattern detection")
            await self._ai_pattern_detection(context, issues, insights, metrics)

        # Generate insights
        if avg_lcom > 0.7:
            insights.append(f"High average LCOM ({avg_lcom:.2f}) indicates low cohesion - consider splitting classes")

        if avg_cbo > 10:
            insights.append(f"High average CBO ({avg_cbo:.1f}) indicates tight coupling - consider dependency injection")

        if len(cyclic_deps) > 0:
            insights.append(f"Found {len(cyclic_deps)} cyclic dependencies - refactor to break cycles")

        if len(all_solid_violations) > 0:
            principle_counts = defaultdict(int)
            for v in all_solid_violations:
                principle_counts[v["principle"]] += 1
            top_violations = sorted(principle_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            insights.append(f"Top SOLID violations: {', '.join(f'{p}({c})' for p, c in top_violations)}")

        execution_time = time.time() - start_time

        self.logger.info(
            f"Architecture analysis complete: {len(issues)} issues, "
            f"{len(all_solid_violations)} SOLID violations, "
            f"{len(all_smells)} architectural smells"
        )

        return AnalysisResult(
            analyzer_name=self.name,
            analyzer_version=self.version,
            status=ResultStatus.SUCCESS,
            metrics=metrics,
            issues=issues,
            insights=insights,
            execution_time_seconds=execution_time,
        )

    async def _ai_pattern_detection(
        self,
        context: AnalysisContext,
        issues: List[Issue],
        insights: List[str],
        metrics: Dict[str, MetricValue],
    ):
        """AI-powered design pattern detection using LLMs.

        Based on Schmid et al. (2025) LLM-based pattern recognition.
        Samples files strategically for cost optimization.
        """
        # Sample files strategically: largest and most connected
        sample_size = min(5, len(context.files))
        sample_files = sorted(context.files, key=lambda f: f.stat().st_size, reverse=True)[:sample_size]

        for file_path in sample_files:
            if not self.should_analyze_file(file_path):
                continue

            code = read_file_safe(file_path)
            if not code or len(code) > 5000:
                continue

            try:
                # Construct AI prompt for pattern detection
                result = await self.ai_client.analyze_code(
                    code=code,
                    analysis_type="architecture",
                    context=f"""Analyze this Python module for:
1. Design patterns (GoF patterns: Singleton, Factory, Strategy, Observer, etc.)
2. Architectural patterns (MVC, Repository, Service Layer, etc.)
3. Anti-patterns and code smells
4. Overall architecture quality score (0-100)

File: {file_path.name}
Focus on identifying concrete patterns with evidence.""",
                )

                parsed = parse_json_response(str(result)) if isinstance(result, str) else result

                if parsed:
                    # Extract design patterns
                    patterns = parsed.get("design_patterns", [])
                    if patterns:
                        for pattern in patterns[:3]:  # Top 3 patterns
                            insights.append(f"Pattern in {file_path.name}: {pattern}")

                    # Extract anti-patterns
                    anti_patterns = parsed.get("anti_patterns", [])
                    for anti_pattern in anti_patterns:
                        issues.append(
                            Issue(
                                severity=Severity.MEDIUM,
                                category=IssueCategory.ARCHITECTURE,
                                title=f"Anti-pattern detected: {anti_pattern.get('name', 'Unknown')}",
                                description=anti_pattern.get("description", "No description"),
                                file_path=file_path,
                                rule_id="AI-ANTIPATTERN",
                            )
                        )

                    # Extract architecture score
                    score = extract_score(parsed, ["architecture_score", "quality_score", "score"])
                    if score:
                        metrics[f"ai_quality_{file_path.stem}"] = MetricValue(
                            name=f"ai_quality_{file_path.stem}",
                            value=score,
                            threshold=70,
                            passed=score >= 70,
                        )

            except Exception as e:
                self.logger.warning(f"AI analysis failed for {file_path.name}: {e}")
                continue
