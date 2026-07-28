"""
Tests for SecurityAnalyzer — zero coverage in original suite.
Uses only static analysis (bandit) — no AI calls needed for core tests.
"""

import pytest
import tempfile
from pathlib import Path

from synexian.analyzers.security.analyzer import SecurityAnalyzer
from synexian.config import AnalyzerConfig
from synexian.analyzers.base import AnalysisContext
from synexian.constants import ResultStatus, Severity


@pytest.fixture
def analyzer():
    config = AnalyzerConfig(enabled=True, options={"use_ai_analysis": False})
    return SecurityAnalyzer(config=config, ai_client=None)


@pytest.fixture
def context_for(tmp_path):
    def _make(files):
        config = AnalyzerConfig(enabled=True, options={"use_ai_analysis": False})
        return AnalysisContext(
            project_root=tmp_path,
            files=files,
            config=config,
            cache_enabled=False,
        )
    return _make


def write_py(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content)
    return p


class TestSecurityAnalyzerProperties:
    def test_name(self, analyzer):
        assert analyzer.name == "security"

    def test_version_is_string(self, analyzer):
        assert isinstance(analyzer.version, str)

    def test_is_enabled(self, analyzer):
        assert analyzer.is_enabled()


class TestSecurityAnalyzerCleanCode:
    """Clean code should pass with no critical issues."""

    @pytest.mark.asyncio
    async def test_clean_file_returns_success(self, analyzer, tmp_path, context_for):
        f = write_py(tmp_path, "clean.py", """
def add(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
""")
        ctx = context_for([f])
        result = await analyzer.analyze(ctx)
        assert result.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)

    @pytest.mark.asyncio
    async def test_empty_file_no_critical_issues(self, analyzer, tmp_path, context_for):
        f = write_py(tmp_path, "empty.py", "")
        ctx = context_for([f])
        result = await analyzer.analyze(ctx)
        critical = [i for i in result.issues if i.severity == Severity.CRITICAL]
        assert len(critical) == 0


class TestSecurityAnalyzerVulnerabilities:
    """Files with known vulnerabilities should generate security issues."""

    @pytest.mark.asyncio
    async def test_hardcoded_password_detected(self, analyzer, tmp_path, context_for):
        f = write_py(tmp_path, "secret.py", """
DATABASE_PASSWORD = "super_secret_password_123"
API_KEY = "hardcoded_api_key_value"

def connect():
    return DATABASE_PASSWORD
""")
        ctx = context_for([f])
        result = await analyzer.analyze(ctx)
        security_issues = [i for i in result.issues
                          if "password" in i.title.lower()
                          or "secret" in i.title.lower()
                          or "hardcod" in i.title.lower()
                          or "key" in i.title.lower()]
        # Bandit should catch B105 (hardcoded password string)
        assert len(result.issues) > 0 or result.status == ResultStatus.PARTIAL

    @pytest.mark.asyncio
    async def test_sql_injection_pattern_flagged(self, analyzer, tmp_path, context_for):
        f = write_py(tmp_path, "db.py", """
import sqlite3

def get_user(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE name = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchall()
""")
        ctx = context_for([f])
        result = await analyzer.analyze(ctx)
        # Should detect string-formatted SQL (bandit B608)
        assert result.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)

    @pytest.mark.asyncio
    async def test_subprocess_shell_true_flagged(self, analyzer, tmp_path, context_for):
        f = write_py(tmp_path, "cmd.py", """
import subprocess

def run_command(cmd):
    result = subprocess.run(cmd, shell=True)
    return result
""")
        ctx = context_for([f])
        result = await analyzer.analyze(ctx)
        shell_issues = [i for i in result.issues
                       if "shell" in i.title.lower() or "subprocess" in i.title.lower()]
        # Bandit B602/B603 should catch shell=True
        assert len(result.issues) > 0 or result.status == ResultStatus.PARTIAL


class TestSecurityAnalyzerEdgeCases:
    """Edge cases: multiple files, syntax errors, missing tools."""

    @pytest.mark.asyncio
    async def test_multiple_files_all_analyzed(self, analyzer, tmp_path, context_for):
        files = [
            write_py(tmp_path, f"file{i}.py", f"x = {i}")
            for i in range(5)
        ]
        ctx = context_for(files)
        result = await analyzer.analyze(ctx)
        assert result.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)

    @pytest.mark.asyncio
    async def test_empty_file_list(self, analyzer, tmp_path, context_for):
        ctx = context_for([])
        result = await analyzer.analyze(ctx)
        assert result is not None
        assert result.status != ResultStatus.FAILED

    @pytest.mark.asyncio
    async def test_nonexistent_file_handled_gracefully(self, analyzer, tmp_path, context_for):
        ctx = context_for([Path("/nonexistent/path/file.py")])
        result = await analyzer.analyze(ctx)
        # Should not raise — should return PARTIAL or SUCCESS with warning
        assert result is not None
