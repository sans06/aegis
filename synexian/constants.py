"""Constants used throughout the Aegis """

#=====================================
#  2026 Synexian Labs Private Limited
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

# Default analyzer weights for scoring
DEFAULT_ANALYZER_WEIGHTS = {
    AnalyzerType.COMPLEXITY: 0.15,
    AnalyzerType.SECURITY: 0.25,
    AnalyzerType.STYLE: 0.08,
    AnalyzerType.ARCHITECTURE: 0.15,
    AnalyzerType.EDGE_CASES: 0.10,
    AnalyzerType.TEST_QUALITY: 0.15,
    AnalyzerType.COGNITIVE_LOAD: 0.07,
    AnalyzerType.CUSTOM_RULES: 0.05,
}

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
DEFAULT_MAX_WORKERS = 4
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MAX_FILE_SIZE_KB = 1000

# Output configuration
DEFAULT_OUTPUT_DIR = "./synexian-reports"
DEFAULT_VERBOSITY = 1
