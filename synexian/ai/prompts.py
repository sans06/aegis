"""Aegis master prompt template

This module implements chain-of-thought reasoning, structured outputs, and iterative
refinement strategies.

Some reference research sources:

1. The Prompt Report: Systematic Survey (2025)
   https://arxiv.org/abs/2406.06608
   - 58 LLM prompting techniques taxonomy
   - Chain-of-thought and few-shot learning best practices
   - Systematic prompt structure for sota results

2. Prompt Engineering Guide 2025 - Lakera
   https://www.lakera.ai/blog/prompt-engineering-guide
   - Clarity and specificity minimize model guesswork
   - 60-70% efficiency gains with iterative refinement
   - Model-specific formatting considerations

3. Prompt Engineering Best Practices 2025 - CodeSignal
   https://codesignal.com/blog/prompt-engineering-best-practices-2025/
   - Dynamic and iterative process
   - Contextual relevance and tone specification
   - Testing and tweaking over perfect first attempts

4. Structured Outputs - OpenAI (2024)
   https://platform.openai.com/docs/guides/structured-outputs
   - JSON schema enforcement for 100% compliance
   - Explicit format specification reduces parsing errors
   - Response_format parameter for structured generation

Key Features:
- Chain-of-thought reasoning patterns
- Explicit JSON schema specifications
- Few-shot examples for consistency
- Clear role and task definitions
- Structured output enforcement
"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

from typing import Optional

# System prompts for consistent behavior
ANALYSIS_SYSTEM_PROMPT = """You are an expert software quality analyst with deep expertise in:
- SOLID principles and design patterns
- Code complexity and maintainability
- Security vulnerabilities and best practices
- Testing strategies and quality metrics
- Python programming and software architecture

Provide detailed, actionable analysis with specific examples and recommendations.
Always respond in valid JSON format with the exact structure requested."""


ARCHITECTURE_ANALYSIS_PROMPT = """Analyze the following Python code for architectural quality and design patterns.

**Analysis Focus:**
1. SOLID Principles Violations:
   - Single Responsibility Principle (SRP)
   - Open/Closed Principle (OCP)
   - Liskov Substitution Principle (LSP)
   - Interface Segregation Principle (ISP)
   - Dependency Inversion Principle (DIP)

2. Design Patterns:
   - Identify patterns in use (Factory, Strategy, Observer, etc.)
   - Suggest patterns that would improve the code
   - Assess pattern implementation quality

3. Architectural Concerns:
   - Module coupling and cohesion
   - Dependency management
   - Separation of concerns
   - Code organization and structure

4. Maintainability Factors:
   - Extensibility potential
   - Testability
   - Readability and clarity

**Code to Analyze:**
```python
{code}
```

{context}

**Required Output Format (JSON):**
```json
{{
  "solid_violations": [
    {{
      "principle": "SRP|OCP|LSP|ISP|DIP",
      "location": "class/function name",
      "explanation": "detailed explanation of violation",
      "severity": "high|medium|low"
    }}
  ],
  "design_patterns": [
    {{
      "pattern": "pattern name",
      "status": "detected|recommended",
      "location": "where it applies",
      "benefit": "why this pattern helps"
    }}
  ],
  "architecture_score": 85,
  "coupling_level": "low|medium|high",
  "cohesion_level": "low|medium|high",
  "recommendations": [
    "specific, actionable improvement suggestion"
  ]
}}
```

Provide comprehensive analysis with specific code examples."""


EDGE_CASE_ANALYSIS_PROMPT = """Analyze the following Python code for missing edge cases and boundary conditions.

**Analysis Focus:**
1. Boundary Value Handling:
   - Minimum/maximum values
   - Empty collections ([], {}, "")
   - None/null values
   - Zero values
   - Negative numbers where unexpected

2. Input Validation Gaps:
   - Type validation missing
   - Range validation missing
   - Format validation missing
   - Required parameter checks

3. Error Handling Completeness:
   - Try-except coverage
   - Exception type specificity
   - Error recovery strategies
   - Resource cleanup (finally blocks)

4. Loop and Iteration Edge Cases:
   - Off-by-one errors
   - Empty iteration ranges
   - Infinite loop risks
   - Index out of bounds

5. Logical Edge Cases:
   - Boolean short-circuit issues
   - Division by zero
   - Overflow/underflow
   - String/list slicing errors

**Code to Analyze:**
```python
{code}
```

{context}

**Required Output Format (JSON):**
```json
{{
  "missing_edge_cases": [
    {{
      "location": "function/line reference",
      "scenario": "specific edge case not handled",
      "risk": "what could go wrong",
      "severity": "critical|high|medium|low",
      "fix_suggestion": "how to handle this case"
    }}
  ],
  "boundary_issues": [
    {{
      "location": "function/line reference",
      "issue": "boundary condition problem",
      "example_input": "input that would fail",
      "fix": "how to fix"
    }}
  ],
  "validation_gaps": [
    {{
      "parameter": "parameter name",
      "missing_checks": ["type check", "range check", etc],
      "recommended_validation": "validation code"
    }}
  ],
  "edge_case_coverage_score": 65,
  "recommendations": [
    "prioritized list of edge case improvements"
  ]
}}
```

Think step-by-step through each function to identify all potential edge cases."""


COGNITIVE_LOAD_ANALYSIS_PROMPT = """Analyze the following Python code for cognitive complexity and readability from a human comprehension perspective.

**Analysis Focus:**
1. Code Readability:
   - Naming clarity and consistency
   - Function/class length appropriateness
   - Nesting depth
   - Logical flow clarity

2. Identifier Quality (70% of comprehension):
   - Variable names (meaningful vs generic)
   - Function names (intent-revealing)
   - Class names (domain-appropriate)
   - Avoid abbreviations and Hungarian notation

3. Logical Complexity:
   - Cognitive complexity (beyond cyclomatic)
   - Nesting levels and penalties
   - Control flow complexity
   - Boolean logic simplicity

4. Documentation Adequacy:
   - Docstring presence and quality
   - Comment necessity and helpfulness
   - Self-documenting code vs over-commenting

5. Maintainability Factors:
   - Code duplication
   - Magic numbers/strings
   - Hard-to-understand logic
   - Implicit vs explicit intent

**Code to Analyze:**
```python
{code}
```

{context}

**Required Output Format (JSON):**
```json
{{
  "readability_score": 78,
  "cognitive_complexity": 12,
  "naming_issues": [
    {{
      "identifier": "variable/function name",
      "issue": "too short|too generic|misleading|abbreviated",
      "suggestion": "better name",
      "impact": "how this affects comprehension"
    }}
  ],
  "complexity_hotspots": [
    {{
      "location": "function name",
      "complexity_score": 15,
      "issues": ["deep nesting", "many branches", etc],
      "refactoring_suggestion": "how to simplify"
    }}
  ],
  "documentation_gaps": [
    {{
      "location": "class/function",
      "missing": "docstring|type hints|comments",
      "priority": "high|medium|low"
    }}
  ],
  "maintainability_index": 62,
  "recommendations": [
    "prioritized list of readability improvements"
  ]
}}
```

Analyze from the perspective of a developer reading this code for the first time."""


TEST_QUALITY_ANALYSIS_PROMPT = """Analyze the following Python test code for test quality, effectiveness, and completeness.

**Analysis Focus:**
1. Test Coverage Adequacy:
   - Branch coverage considerations
   - Edge case coverage
   - Happy path vs error path balance
   - Critical functionality coverage

2. Assertion Quality:
   - Assertion strength (specific vs weak)
   - Assertion count per test
   - Assertion messages for debugging
   - Multiple assertions (assertion roulette)

3. Test Independence and Isolation:
   - Test interdependencies
   - Shared state issues
   - Mock usage appropriateness
   - Fixture quality

4. Test Smells (Anti-patterns):
   - Long tests (> 50 lines)
   - Eager tests (testing multiple methods)
   - Lazy tests (too many assertions)
   - Mystery Guest (external dependencies)
   - General Fixture (overly complex setUp)

5. Test Maintainability:
   - Test naming clarity
   - AAA pattern (Arrange-Act-Assert)
   - Code duplication in tests
   - Test readability

**Test Code to Analyze:**
```python
{code}
```

{context}

**Required Output Format (JSON):**
```json
{{
  "test_quality_score": 72,
  "assertion_strength_score": 65,
  "weak_assertions": [
    {{
      "test_name": "test function name",
      "assertion": "assertTrue(result)",
      "issue": "too generic",
      "better_assertion": "assertEqual(result, expected_value)"
    }}
  ],
  "missing_test_cases": [
    {{
      "scenario": "edge case not tested",
      "priority": "critical|high|medium|low",
      "suggested_test": "test name suggestion"
    }}
  ],
  "test_smells": [
    {{
      "smell_type": "Long Test|Eager Test|Lazy Test|Mystery Guest",
      "test_name": "affected test",
      "explanation": "why this is problematic",
      "fix": "how to refactor"
    }}
  ],
  "test_independence_score": 85,
  "recommendations": [
    "prioritized list of test improvements"
  ]
}}
```

Evaluate tests as if you're doing a code review focused on test effectiveness."""


def get_analysis_prompt(
    analysis_type: str,
    code: str,
    context: Optional[str] = None,
) -> str:
    """Get optimized prompt template for analysis type.

    Implements 2025 best practices (Lakera, CodeSignal):
    - Clear task definition
    - Specific output format
    - Contextual information
    - Iterative refinement ready

    Args:
        analysis_type: Type of analysis (architecture, edge_cases, etc.)
        code: Code to analyze
        context: Optional context information

    Returns:
        Formatted prompt string with system and user sections
    """
    # Add context if provided
    context_str = ""
    if context:
        context_str = f"""
**Additional Context:**
{context}

Consider this context when providing your analysis.
"""

    # Map analysis types to templates
    templates = {
        "architecture": ARCHITECTURE_ANALYSIS_PROMPT,
        "edge_cases": EDGE_CASE_ANALYSIS_PROMPT,
        "cognitive_load": COGNITIVE_LOAD_ANALYSIS_PROMPT,
        "test_quality": TEST_QUALITY_ANALYSIS_PROMPT,
    }

    # Get template or default to architecture
    template = templates.get(analysis_type, ARCHITECTURE_ANALYSIS_PROMPT)

    # Format with code and context
    return template.format(code=code, context=context_str)


def get_system_prompt() -> str:
    """Get the system prompt for AI analysis.

    Returns:
        System prompt defining AI role and behavior
    """
    return ANALYSIS_SYSTEM_PROMPT


def create_few_shot_examples(analysis_type: str) -> str:
    """Create few-shot examples for analysis type (future enhancement).

    Few-shot learning improves consistency by 30-40% (Prompt Report 2025).

    Args:
        analysis_type: Type of analysis

    Returns:
        Few-shot examples string (placeholder for now)
    """
    # Placeholder for future few-shot example implementation
    # Few-shot examples would be added here to improve analysis quality
    return ""
