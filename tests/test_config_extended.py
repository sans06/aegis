"""
Extended config tests — supplements the existing test_config.py.
Tests: static-only mode, from_yaml, from_env, validate() gaps.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from synexian.config import Config, AnalyzerConfig
from synexian.constants import AnalyzerType


class TestConfigValidation:
    def test_valid_config_no_errors(self):
        c = Config()
        c.openrouter_api_key = "valid-key-12345"
        errors = c.validate()
        assert errors == []

    def test_missing_api_key_currently_hard_errors(self):
        """
        Documents BUG CR-06: missing API key blocks even static-only runs.
        Currently produces a hard error — should be a warning only.
        After fix: this should return [] (or warnings, not errors).
        """
        c = Config()
        c.openrouter_api_key = ""
        errors = c.validate()
        # Current broken behaviour: hard error even if user wants static only
        assert len(errors) > 0  # documents the bug

    @pytest.mark.xfail(reason="BUG CR-06: API key should not block static-only analysis")
    def test_missing_api_key_is_only_warning_after_fix(self):
        """After fix: missing key should NOT produce a blocking error."""
        c = Config()
        c.openrouter_api_key = ""
        errors = c.validate()
        assert errors == []

    def test_negative_max_workers_errors(self):
        c = Config()
        c.openrouter_api_key = "key-123456"
        c.max_workers = -1
        errors = c.validate()
        assert any("max_workers" in e for e in errors)

    def test_zero_timeout_errors(self):
        c = Config()
        c.openrouter_api_key = "key-123456"
        c.timeout_seconds = 0
        errors = c.validate()
        assert any("timeout" in e for e in errors)

    def test_bad_weight_sum_errors(self):
        c = Config()
        c.openrouter_api_key = "key-123456"
        c.analyzer_weights = {
            AnalyzerType.SECURITY: 0.5,
            AnalyzerType.COMPLEXITY: 0.3,
        }
        errors = c.validate()
        assert any("weight" in e.lower() or "sum" in e.lower() for e in errors)

    def test_empty_file_patterns_errors(self):
        c = Config()
        c.openrouter_api_key = "key-123456"
        c.file_patterns = []
        errors = c.validate()
        assert any("pattern" in e.lower() for e in errors)

    def test_custom_rules_zero_weight_passes_validation(self):
        """
        Documents BUG LV-06: validate() cannot detect enabled analyzer with 0.0 weight.
        custom_rules is enabled but has weight 0.0 — this should warn.
        Currently passes validation silently.
        """
        c = Config()
        c.openrouter_api_key = "key-123456"
        errors = c.validate()
        # BUG: no error even though custom_rules enabled but weight=0.0
        assert errors == []  # documents silent failure


class TestAnalyzerConfig:
    def test_default_enabled_true(self):
        config = AnalyzerConfig(enabled=True)
        assert config.enabled is True

    def test_disabled_analyzer(self):
        config = AnalyzerConfig(enabled=False)
        assert config.enabled is False

    def test_thresholds_stored(self):
        config = AnalyzerConfig(enabled=True, thresholds={"cc": 10})
        assert config.thresholds["cc"] == 10

    def test_options_stored(self):
        config = AnalyzerConfig(enabled=True, options={"use_ai": False})
        assert config.options["use_ai"] is False


class TestConfigFromEnv:
    def test_api_key_from_env(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "env-key-123"}):
            c = Config.from_env()
            assert c.openrouter_api_key == "env-key-123"

    def test_model_from_env(self):
        with patch.dict(os.environ, {"SYNEXIAN_MODEL": "custom-model"}):
            c = Config.from_env()
            assert c.model == "custom-model"

    def test_missing_env_uses_defaults(self):
        with patch.dict(os.environ, {}, clear=False):
            env_without_key = {k: v for k, v in os.environ.items()
                              if k != "OPENROUTER_API_KEY"}
            with patch.dict(os.environ, env_without_key, clear=True):
                c = Config.from_env()
                assert c.openrouter_api_key == ""


class TestConfigToDict:
    def test_round_trip(self):
        c = Config()
        c.openrouter_api_key = "test-key"
        d = c.to_dict()
        assert isinstance(d, dict)
        assert "model" in d
        assert "cache_enabled" in d

    def test_sensitive_fields_excluded(self):
        """API key should NOT appear in to_dict() output."""
        c = Config()
        c.openrouter_api_key = "super-secret-key-123"
        d = c.to_dict()
        # Stringify and check
        import json
        serialized = json.dumps(d)
        assert "super-secret-key-123" not in serialized


class TestAnalyzerWeightDefaults:
    def test_weights_sum_to_one(self):
        from synexian.constants import DEFAULT_ANALYZER_WEIGHTS
        total = sum(DEFAULT_ANALYZER_WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_custom_rules_weight_is_nonzero(self):
        """FIX H-02: custom_rules now has a non-zero weight (0.05)."""
        from synexian.constants import DEFAULT_ANALYZER_WEIGHTS, AnalyzerType
        assert DEFAULT_ANALYZER_WEIGHTS[AnalyzerType.CUSTOM_RULES] == 0.05

    def test_security_is_highest_weight(self):
        from synexian.constants import DEFAULT_ANALYZER_WEIGHTS, AnalyzerType
        security_w = DEFAULT_ANALYZER_WEIGHTS[AnalyzerType.SECURITY]
        other_weights = [v for k, v in DEFAULT_ANALYZER_WEIGHTS.items()
                        if k != AnalyzerType.SECURITY]
        assert all(security_w >= w for w in other_weights)
