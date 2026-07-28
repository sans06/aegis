"""Cache management for AI responses and analysis results."""

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from platformdirs import user_cache_dir

from synexian.exceptions import CacheError


class CacheManager:
    """Manage caching of analysis results and AI responses."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_hours: int = 24,
        enabled: bool = True,
    ):
        """Initialize cache manager.

        Args:
            cache_dir: Cache directory path
            ttl_hours: Time-to-live in hours
            enabled: Whether caching is enabled
        """
        self.enabled = enabled
        self.ttl_seconds = ttl_hours * 3600

        if cache_dir is None:
            cache_dir = Path(user_cache_dir("synexian"))

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, *args: Any) -> str:
        """Generate cache key from arguments.

        Args:
            *args: Arguments to hash

        Returns:
            Cache key string
        """
        # FIX CR-25 / LV-08: json.dumps previously raised TypeError on Path
        # and datetime objects, causing silent cache misses for any call that
        # passed file paths as cache key components. default=str converts
        # non-serializable types to their string representation before hashing.
        content = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get path to cache file.

        Args:
            key: Cache key

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{key}.json"

    def get(self, *args: Any) -> Optional[Dict[str, Any]]:
        """Get value from cache.

        Args:
            *args: Cache key components

        Returns:
            Cached value or None if not found/expired
        """
        if not self.enabled:
            return None

        try:
            key = self._get_cache_key(*args)
            cache_path = self._get_cache_path(key)

            if not cache_path.exists():
                return None

            # Check if expired
            age = time.time() - cache_path.stat().st_mtime
            if age > self.ttl_seconds:
                cache_path.unlink()
                return None

            # Load and return
            with open(cache_path, "r") as f:
                return json.load(f)

        except Exception as e:
            import logging
            logging.getLogger("synexian.cache").debug(f"Cache read failed: {e}")
            return None

    def set(self, value: Dict[str, Any], *args: Any) -> None:
        """Set value in cache.

        Args:
            value: Value to cache
            *args: Cache key components
        """
        if not self.enabled:
            return

        try:
            key = self._get_cache_key(*args)
            cache_path = self._get_cache_path(key)

            with open(cache_path, "w") as f:
                json.dump(value, f)

        except Exception as e:
            # FIX CR-14 / H-14: Cache write failures must never crash the analysis.
            # Previously raised CacheError which propagated up and crashed the run.
            # Cache is a performance optimisation — its failure is non-fatal.
            import logging
            logging.getLogger("synexian.cache").warning(
                f"Cache write failed (non-fatal, analysis continues): {e}"
            )

    def clear(self) -> None:
        """Clear all cache files."""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
        except Exception as e:
            import logging
            logging.getLogger("synexian.cache").warning(f"Cache clear failed: {e}")

    def clear_expired(self) -> int:
        """Clear expired cache files.

        Returns:
            Number of files deleted
        """
        count = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                age = time.time() - cache_file.stat().st_mtime
                if age > self.ttl_seconds:
                    cache_file.unlink()
                    count += 1
        except Exception:
            pass

        return count
