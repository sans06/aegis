"""Configuration management system for the Aegis """

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

from synexian.constants import (
    DEFAULT_ANALYZER_WEIGHTS,
    DEFAULT_CACHE_ENABLED,
    DEFAULT_CACHE_TTL_HOURS,
    DEFAULT_FILE_PATTERNS,
    DEFAULT_IGNORE_PATTERNS,
    DEFAULT_MAX_FILE_SIZE_KB,
    DEFAULT_MAX_WORKERS,
    DEFAULT_MODEL,
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_VERBOSITY,
    AnalyzerType,
)
from synexian.exceptions import ConfigurationError, ValidationError


@dataclass
class AnalyzerConfig:
    """Configuration for a single analyzer."""

    enabled: bool = True
    thresholds: Dict[str, float] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "thresholds": self.thresholds,
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalyzerConfig":
        """Create from dictionary."""
        return cls(
            enabled=data.get("enabled", True),
            thresholds=data.get("thresholds", {}),
            options=data.get("options", {}),
        )


@dataclass
class Config:
    """Main configuration for the Synexian application."""

    # API Configuration
    openrouter_api_key: str = ""
    openrouter_base_url: str = DEFAULT_OPENROUTER_BASE_URL
    model: str = DEFAULT_MODEL

    # Analysis Configuration
    analyzers: Dict[str, AnalyzerConfig] = field(default_factory=dict)
    file_patterns: List[str] = field(default_factory=lambda: DEFAULT_FILE_PATTERNS.copy())
    ignore_patterns: List[str] = field(default_factory=lambda: DEFAULT_IGNORE_PATTERNS.copy())
    max_file_size_kb: int = DEFAULT_MAX_FILE_SIZE_KB

    # Execution Configuration
    parallel_analyzers: bool = True
    max_workers: int = DEFAULT_MAX_WORKERS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    # Caching
    cache_enabled: bool = DEFAULT_CACHE_ENABLED
    cache_ttl_hours: int = DEFAULT_CACHE_TTL_HOURS
    cache_dir: Optional[Path] = None

    # Output Configuration
    output_formats: List[str] = field(default_factory=lambda: ["cli"])
    output_dir: Path = field(default_factory=lambda: Path(DEFAULT_OUTPUT_DIR))
    verbosity: int = DEFAULT_VERBOSITY

    # Scoring
    analyzer_weights: Dict[AnalyzerType, float] = field(
        default_factory=lambda: DEFAULT_ANALYZER_WEIGHTS.copy()
    )

    # GitHub Configuration
    github_token: Optional[str] = None

    def __post_init__(self):
        """Initialize default analyzer configs if not provided."""
        if not self.analyzers:
            self.analyzers = self._get_default_analyzer_configs()

        # Convert string keys to AnalyzerType for analyzer_weights
        if self.analyzer_weights and not isinstance(
            list(self.analyzer_weights.keys())[0], AnalyzerType
        ):
            self.analyzer_weights = {
                AnalyzerType(k) if isinstance(k, str) else k: v
                for k, v in self.analyzer_weights.items()
            }

    def _get_default_analyzer_configs(self) -> Dict[str, AnalyzerConfig]:
        """Get default analyzer configurations."""
        return {
            "complexity": AnalyzerConfig(
                enabled=True,
                thresholds={
                    "cyclomatic_complexity": 10.0,
                    "cognitive_complexity": 15.0,
                    "halstead_difficulty": 20.0,
                },
            ),
            "security": AnalyzerConfig(
                enabled=True,
                thresholds={"critical_issues": 0.0, "high_issues": 5.0},
            ),
            "style": AnalyzerConfig(
                enabled=True,
                thresholds={"pep8_violations_per_kloc": 10.0},
                options={"max_line_length": 100, "enforce_naming": True},
            ),
            "architecture": AnalyzerConfig(
                enabled=True,
                options={
                    "check_solid": True,
                    "detect_patterns": True,
                    "analyze_dependencies": True,
                },
            ),
            "edge_cases": AnalyzerConfig(enabled=True),
            "test_quality": AnalyzerConfig(
                enabled=True,
                thresholds={"code_coverage": 80.0, "mutation_score": 70.0},
            ),
            "cognitive_load": AnalyzerConfig(
                enabled=True,
                thresholds={"maintainability_index": 65.0, "readability_score": 70.0},
            ),
            "custom_rules": AnalyzerConfig(enabled=False),
        }

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        load_dotenv()

        config = cls()

        # API Configuration
        config.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        config.openrouter_base_url = os.getenv(
            "OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL
        )
        config.model = os.getenv("SYNEXIAN_MODEL", DEFAULT_MODEL)

        # Cache Configuration
        config.cache_enabled = os.getenv("SYNEXIAN_CACHE_ENABLED", "true").lower() == "true"
        cache_dir_str = os.getenv("SYNEXIAN_CACHE_DIR")
        if cache_dir_str:
            config.cache_dir = Path(cache_dir_str).expanduser()

        # Execution Configuration
        config.max_workers = int(os.getenv("SYNEXIAN_MAX_WORKERS", DEFAULT_MAX_WORKERS))
        config.timeout_seconds = int(
            os.getenv("SYNEXIAN_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
        )

        # Output Configuration
        output_dir_str = os.getenv("SYNEXIAN_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
        config.output_dir = Path(output_dir_str)
        config.verbosity = int(os.getenv("SYNEXIAN_VERBOSITY", DEFAULT_VERBOSITY))

        # GitHub Token
        config.github_token = os.getenv("GITHUB_TOKEN")

        return config

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "Config":
        """Create configuration from YAML file."""
        if not yaml_path.exists():
            raise ConfigurationError(f"Configuration file not found: {yaml_path}")

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f) or {}

        config = cls.from_env()

        # Analysis Configuration
        if "analysis" in data:
            analysis = data["analysis"]
            config.file_patterns = analysis.get("file_patterns", config.file_patterns)
            config.ignore_patterns = analysis.get("ignore_patterns", config.ignore_patterns)
            config.max_file_size_kb = analysis.get("max_file_size_kb", config.max_file_size_kb)

        # Analyzer Configuration
        if "analyzers" in data:
            for analyzer_name, analyzer_data in data["analyzers"].items():
                config.analyzers[analyzer_name] = AnalyzerConfig.from_dict(analyzer_data)

        # Scoring Configuration
        if "scoring" in data:
            scoring = data["scoring"]
            if "weights" in scoring:
                config.analyzer_weights = {
                    AnalyzerType(k): v for k, v in scoring["weights"].items()
                }

        # Output Configuration
        if "output" in data:
            output = data["output"]
            config.output_formats = output.get("formats", config.output_formats)
            if "directory" in output:
                config.output_dir = Path(output["directory"])

        # Performance Configuration
        if "performance" in data:
            perf = data["performance"]
            config.parallel_analyzers = perf.get("parallel_analyzers", config.parallel_analyzers)
            config.max_workers = perf.get("max_workers", config.max_workers)
            config.timeout_seconds = perf.get("timeout_seconds", config.timeout_seconds)

        # Cache Configuration
        if "cache" in data:
            cache = data["cache"]
            config.cache_enabled = cache.get("enabled", config.cache_enabled)
            config.cache_ttl_hours = cache.get("ttl_hours", config.cache_ttl_hours)
            if "directory" in cache:
                config.cache_dir = Path(cache["directory"]).expanduser()

        return config

    @classmethod
    def from_files(cls, env_path: Optional[Path] = None, config_path: Optional[Path] = None) -> "Config":
        """Create configuration from both env and YAML files."""
        if env_path and env_path.exists():
            load_dotenv(env_path)

        config = cls.from_env()

        if config_path and config_path.exists():
            config = cls.from_yaml(config_path)

        return config

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Validate API key
        if not self.openrouter_api_key:
            errors.append(
                "OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable."
            )

        # Validate file patterns
        if not self.file_patterns:
            errors.append("At least one file pattern must be specified.")

        # Validate weights
        total_weight = sum(self.analyzer_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            errors.append(f"Analyzer weights must sum to 1.0, got {total_weight}")

        # Validate max workers
        if self.max_workers < 1:
            errors.append(f"max_workers must be at least 1, got {self.max_workers}")

        # Validate timeout
        if self.timeout_seconds < 1:
            errors.append(f"timeout_seconds must be at least 1, got {self.timeout_seconds}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "openrouter_api_key": "***" if self.openrouter_api_key else "",
            "openrouter_base_url": self.openrouter_base_url,
            "model": self.model,
            "analyzers": {name: config.to_dict() for name, config in self.analyzers.items()},
            "file_patterns": self.file_patterns,
            "ignore_patterns": self.ignore_patterns,
            "max_file_size_kb": self.max_file_size_kb,
            "parallel_analyzers": self.parallel_analyzers,
            "max_workers": self.max_workers,
            "timeout_seconds": self.timeout_seconds,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_hours": self.cache_ttl_hours,
            "cache_dir": str(self.cache_dir) if self.cache_dir else None,
            "output_formats": self.output_formats,
            "output_dir": str(self.output_dir),
            "verbosity": self.verbosity,
            "analyzer_weights": {k.value: v for k, v in self.analyzer_weights.items()},
        }


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration with automatic discovery."""
    # Try to load from explicit path
    if config_path:
        return Config.from_yaml(config_path)

    # Try to load from common locations
    common_paths = [
        Path("./synexian.yaml"),
        Path("./synexian.yml"),
        Path("./.synexian.yaml"),
        Path("./config/default_config.yaml"),
        Path.home() / ".config" / "synexian" / "config.yaml",
    ]

    for path in common_paths:
        if path.exists():
            return Config.from_yaml(path)

    # Fall back to environment only
    return Config.from_env()
