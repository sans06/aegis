"""
Tests for input handlers.
LocalDirectoryHandler(directory, file_patterns, ignore_patterns, max_file_size_kb)
  .prepare() -> Path  /  .get_files() -> List[Path]
SingleFileHandler(file_path)
  .prepare() -> Path  /  .get_files() -> List[Path]
"""

import pytest
from pathlib import Path
from synexian.input.local_directory import LocalDirectoryHandler
from synexian.input.single_file import SingleFileHandler
from synexian.exceptions import InputError


@pytest.fixture
def project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    (src / "__init__.py").write_text("")
    (src / "main.py").write_text("def main(): pass\n")
    (src / "utils.py").write_text("def helper(): pass\n")
    (tests / "test_main.py").write_text("def test_main(): assert True\n")
    (tmp_path / "setup.py").write_text("from setuptools import setup; setup()\n")
    (tmp_path / "README.md").write_text("# README\n")
    return tmp_path


def local_handler(project, patterns=None, ignore=None, max_kb=1000):
    return LocalDirectoryHandler(
        directory=project,
        file_patterns=patterns or ["**/*.py"],
        ignore_patterns=ignore or [],
        max_file_size_kb=max_kb,
    )


class TestLocalDirectoryHandler:
    def test_discovers_python_files(self, project):
        h = local_handler(project)
        h.prepare()
        files = h.get_files()
        assert len(files) > 0

    def test_all_discovered_are_python(self, project):
        h = local_handler(project)
        h.prepare()
        assert all(f.suffix == ".py" for f in h.get_files())

    def test_markdown_excluded(self, project):
        h = local_handler(project)
        h.prepare()
        assert all(f.suffix != ".md" for f in h.get_files())

    def test_setup_py_included(self, project):
        h = local_handler(project)
        h.prepare()
        names = [f.name for f in h.get_files()]
        assert "setup.py" in names

    def test_all_paths_absolute(self, project):
        h = local_handler(project)
        h.prepare()
        assert all(f.is_absolute() for f in h.get_files())

    def test_all_files_exist(self, project):
        h = local_handler(project)
        h.prepare()
        assert all(f.exists() for f in h.get_files())

    def test_nested_files_found(self, project):
        h = local_handler(project)
        h.prepare()
        src_files = [f for f in h.get_files() if "src" in str(f)]
        assert len(src_files) >= 2

    def test_returns_list(self, project):
        h = local_handler(project)
        h.prepare()
        assert isinstance(h.get_files(), list)

    def test_empty_directory_returns_empty(self, tmp_path):
        h = local_handler(tmp_path)
        h.prepare()
        assert h.get_files() == []

    def test_ignored_pattern_excluded(self, project):
        h = local_handler(project, ignore=["**/test_*.py"])
        h.prepare()
        test_files = [f for f in h.get_files() if f.name.startswith("test_")]
        assert len(test_files) == 0

    def test_no_ignore_includes_tests(self, project):
        h = local_handler(project, ignore=[])
        h.prepare()
        test_files = [f for f in h.get_files() if f.name.startswith("test_")]
        assert len(test_files) > 0

    def test_large_file_excluded(self, tmp_path):
        large = tmp_path / "large.py"
        large.write_text("x = 1\n" * 1000)  # ~6KB
        h = local_handler(tmp_path, max_kb=1)
        h.prepare()
        assert not any(f.name == "large.py" for f in h.get_files())

    def test_nonexistent_directory_raises(self):
        with pytest.raises(Exception):
            h = LocalDirectoryHandler(
                directory=Path("/nonexistent/path"),
                file_patterns=["**/*.py"],
                ignore_patterns=[],
            )
            h.prepare()


class TestSingleFileHandler:
    def test_single_file_returned(self, project):
        f = project / "src" / "main.py"
        h = SingleFileHandler(file_path=f)
        h.prepare()
        files = h.get_files()
        assert len(files) == 1
        assert files[0] == f

    def test_path_is_absolute(self, project):
        f = project / "src" / "main.py"
        h = SingleFileHandler(file_path=f)
        h.prepare()
        assert h.get_files()[0].is_absolute()

    def test_returns_list(self, project):
        f = project / "src" / "main.py"
        h = SingleFileHandler(file_path=f)
        h.prepare()
        assert isinstance(h.get_files(), list)

    def test_nonexistent_file_raises(self):
        with pytest.raises(Exception):
            h = SingleFileHandler(file_path=Path("/nonexistent/file.py"))
            h.prepare()
