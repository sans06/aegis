"""Tests for configuration management system"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import os
from pathlib import Path

import pytest

from synexian.config import AnalyzerConfig, Config
from synexian.exceptions import ConfigurationError


class TestAnalyzerConfig:
    """Tests for AnalyzerConfig."""

    def test_default_config(self):
        config = AnalyzerConfig()
        assert config.enabled is True
        assert config.thresholds == {}
        assert config.options == {}

    def test_config_to_dict(self):
        config = AnalyzerConfig(
            enabled=True,
            thresholds={"test": 10.0},
            options={"opt": "value"},
        )
        data = config.to_dict()
        assert data["enabled"] is True
        assert data["thresholds"]["test"] == 10.0


class TestConfig:
    """Tests for main Config."""

    def test_default_config(self):
        config = Config()
        assert config.parallel_analyzers is True
        assert config.cache_enabled is True
        assert len(config.analyzers) > 0

    def test_config_validation_no_api_key(self):
        config = Config()
        config.openrouter_api_key = ""
        errors = config.validate()
        assert len(errors) > 0
        assert any("API key" in error for error in errors)

    def test_config_validation_weights(self):
        config = Config()
        config.openrouter_api_key = "test_key"
        # Modify weights to not sum to 1.0
        from synexian.constants import AnalyzerType
        config.analyzer_weights = {AnalyzerType.COMPLEXITY: 1.0}
        errors = config.validate()
        assert len(errors) > 0

    def test_config_to_dict(self):
        config = Config()
        config.openrouter_api_key = "test_key"
        data = config.to_dict()
        assert "openrouter_api_key" in data
        assert data["openrouter_api_key"] == "***"  # Should be masked
