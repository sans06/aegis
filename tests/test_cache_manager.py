"""
Tests for CacheManager — completely untested in the original suite.
API: set(value, *key_args) / get(*key_args) / clear() / clear_expired()
"""

import time
import tempfile
from pathlib import Path
import pytest
from synexian.core.cache_manager import CacheManager


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache"


@pytest.fixture
def cache(cache_dir):
    return CacheManager(cache_dir=cache_dir, ttl_hours=1, enabled=True)


@pytest.fixture
def disabled_cache(cache_dir):
    return CacheManager(cache_dir=cache_dir, ttl_hours=1, enabled=False)


class TestCacheManagerBasicOps:
    def test_cache_miss_returns_none(self, cache):
        assert cache.get("nonexistent") is None

    def test_set_then_get(self, cache):
        cache.set({"data": "value"}, "key1")
        assert cache.get("key1") == {"data": "value"}

    def test_set_dict_value(self, cache):
        payload = {"score": 85.0, "grade": "B", "issues": []}
        cache.set(payload, "analysis", "security")
        assert cache.get("analysis", "security") == payload

    def test_different_keys_different_values(self, cache):
        cache.set({"a": 1}, "key_a")
        cache.set({"b": 2}, "key_b")
        assert cache.get("key_a") == {"a": 1}
        assert cache.get("key_b") == {"b": 2}

    def test_overwrite_replaces_value(self, cache):
        cache.set({"v": "first"}, "k")
        cache.set({"v": "second"}, "k")
        assert cache.get("k") == {"v": "second"}

    def test_creates_cache_directory(self, tmp_path):
        new_dir = tmp_path / "new" / "nested"
        c = CacheManager(cache_dir=new_dir, ttl_hours=1, enabled=True)
        c.set({"x": 1}, "key")
        assert new_dir.exists()

    def test_persists_across_instances(self, cache_dir):
        c1 = CacheManager(cache_dir=cache_dir, ttl_hours=1, enabled=True)
        c1.set({"cross": True}, "persist_key")
        c2 = CacheManager(cache_dir=cache_dir, ttl_hours=1, enabled=True)
        assert c2.get("persist_key") == {"cross": True}

    def test_file_created_on_disk(self, cache, cache_dir):
        cache.set({"test": 1}, "disk_key")
        cache_files = list(cache_dir.glob("*.json")) if cache_dir.exists() else []
        assert len(cache_files) > 0


class TestCacheManagerTTL:
    def test_unexpired_entry_returned(self, cache):
        cache.set({"fresh": True}, "fresh_key")
        assert cache.get("fresh_key") is not None

    def test_expired_entry_returns_none(self, cache_dir):
        c = CacheManager(cache_dir=cache_dir, ttl_hours=0, enabled=True)
        c.set({"gone": True}, "expired")
        time.sleep(0.01)
        assert c.get("expired") is None

    def test_clear_expired_removes_stale_entries(self, cache_dir):
        c = CacheManager(cache_dir=cache_dir, ttl_hours=0, enabled=True)
        c.set({"a": 1}, "old1")
        c.set({"b": 2}, "old2")
        time.sleep(0.01)
        removed = c.clear_expired()
        assert removed >= 0
        assert c.get("old1") is None
        assert c.get("old2") is None


class TestCacheManagerDisabled:
    def test_disabled_get_returns_none(self, disabled_cache):
        assert disabled_cache.get("any_key") is None

    def test_disabled_set_does_not_store(self, disabled_cache, cache_dir):
        disabled_cache.set({"data": 1}, "test_key")
        files = list(cache_dir.glob("*.cache")) if cache_dir.exists() else []
        assert len(files) == 0

    def test_disabled_get_after_set_returns_none(self, disabled_cache):
        disabled_cache.set({"v": 1}, "k")
        assert disabled_cache.get("k") is None


class TestCacheManagerClear:
    def test_clear_removes_all_entries(self, cache):
        cache.set({"a": 1}, "ka")
        cache.set({"b": 2}, "kb")
        cache.clear()
        assert cache.get("ka") is None
        assert cache.get("kb") is None

    def test_clear_expired_returns_int(self, cache):
        result = cache.clear_expired()
        assert isinstance(result, int)
        assert result >= 0


class TestCacheManagerPathKeyBug:
    """Document BUG CR-25 / LV-08: Path objects not JSON-serializable as keys."""

    def test_string_key_works(self, cache):
        cache.set({"r": 1}, "arch", "architecture", 0.3)
        assert cache.get("arch", "architecture", 0.3) == {"r": 1}

    def test_numeric_key_works(self, cache):
        cache.set({"score": 99}, "score_key", 0.7, 100)
        assert cache.get("score_key", 0.7, 100) == {"score": 99}

    @pytest.mark.xfail(reason="BUG CR-25: Path objects cause TypeError in json.dumps key gen")
    def test_path_key_works_after_fix(self, cache):
        """After adding default=str to json.dumps, Path args should work."""
        file_path = Path("/project/src/main.py")
        cache.set({"result": "data"}, "file_key", file_path, "architecture")
        assert cache.get("file_key", file_path, "architecture") == {"result": "data"}
