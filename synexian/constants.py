"""Constants used throughout the Aegis """

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

from enum import Enum


class ResultStatus(str, Enum):
    """Status of an analysis result."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class Severity(str, Enum):
    """Severity levels for issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    """Categories of issues that can be detected."""
    COMPLEXITY = "complexity"
    SECURITY = "security"
    STYLE = "style"
    ARCHITECTURE = "architecture"
    EDGE_CASES = "edge_cases"
    TEST_QUALITY = "test_quality"
    COGNITIVE_LOAD = "cognitive_load"
    CUSTOM = "custom"
    GENERAL = "general"


class AnalyzerType(str, Enum):
    """Types of analyzers."""
    COMPLEXITY = "complexity"
    SECURITY = "security"
    STYLE = "style"
    ARCHITECTURE = "architecture"
    EDGE_CASES = "edge_cases"
    TEST_QUALITY = "test_quality"
    COGNITIVE_LOAD = "cognitive_load"
    CUSTOM_RULES = "custom_rules"


class Grade(str, Enum):
    """Quality grades."""
    A_PLUS = "A+"
    A = "A"
    B_PLUS = "B+"
    B = "B"
    C_PLUS = "C+"
    C = "C"
    D = "D"
    F = "F"


# Default thresholds for grading
GRADE_THRESHOLDS = {
    Grade.A_PLUS: 95,
    Grade.A: 90,
    Grade.B_PLUS: 85,
    Grade.B: 80,
    Grade.C_PLUS: 75,
    Grade.C: 70,
    Grade.D: 60,
    Grade.F: 0,
}
# FIX CR-01: Enforce that GRADE_THRESHOLDS is ordered highest-to-lowest.
# The grade calculation iterates in insertion order and returns the first match,
# so if this dict is ever reordered, grades will be wrong silently.
_thresholds = list(GRADE_THRESHOLDS.values())
assert _thresholds == sorted(_thresholds, reverse=True), (
    "GRADE_THRESHOLDS must be ordered highest threshold to lowest. "
    "Grade calculation relies on first-match insertion order."
)
del _thresholds  # clean up — not needed at module level

# Default analyzer weights for scoring
DEFAULT_ANALYZER_WEIGHTS = {
    AnalyzerType.COMPLEXITY:     0.15,
    AnalyzerType.SECURITY:       0.25,
    AnalyzerType.STYLE:          0.08,   # reduced by 0.02 to make room for custom_rules
    AnalyzerType.ARCHITECTURE:   0.15,
    AnalyzerType.EDGE_CASES:     0.10,
    AnalyzerType.TEST_QUALITY:   0.15,
    AnalyzerType.COGNITIVE_LOAD: 0.07,   # reduced by 0.03 to make room for custom_rules
    AnalyzerType.CUSTOM_RULES:   0.05,   # FIX H-02: was 0.0 — custom rules now affect score
}
# Total: 0.15+0.25+0.08+0.15+0.10+0.15+0.07+0.05 = 1.00

# Default file patterns
DEFAULT_FILE_PATTERNS = ["**/*.py"]

# Default ignore patterns
DEFAULT_IGNORE_PATTERNS = [
    "**/__pycache__/**",
    "**/venv/**",
    "**/.venv/**",
    "**/node_modules/**",
    "**/.git/**",
    "**/dist/**",
    "**/build/**",
    "**/*.egg-info/**",
    "**/.pytest_cache/**",
    "**/.mypy_cache/**",
    "**/.ruff_cache/**",
]

# OpenRouter configuration
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "mistralai/devstral-2512:free"

# Cache configuration
DEFAULT_CACHE_TTL_HOURS = 24
DEFAULT_CACHE_ENABLED = True

# Execution configuration
import os as _os
DEFAULT_MAX_WORKERS = _os.cpu_count() or 4  # FIX CR-02: scale to available CPUs
del _os
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_FILE_SIZE_KB = 1000

# Output configuration
DEFAULT_OUTPUT_DIR = "./synexian-reports"
DEFAULT_VERBOSITY = 1
