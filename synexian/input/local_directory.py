"""Local directory input handler"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential


from pathlib import Path
from typing import List

from synexian.input.base import BaseInputHandler
from synexian.utils.file_utils import get_files_from_directory
from synexian.utils.validators import validate_directory_exists
from synexian.exceptions import InputError


class LocalDirectoryHandler(BaseInputHandler):
    """Handle local directory input."""

    def __init__(
        self,
        directory: Path,
        file_patterns: List[str],
        ignore_patterns: List[str],
        max_file_size_kb: int = 1000,
    ):
        """Initialize handler.

        Args:
            directory: Directory to analyze
            file_patterns: File patterns to include
            ignore_patterns: Patterns to ignore
            max_file_size_kb: Maximum file size in KB
        """
        super().__init__(str(directory))
        self.directory = directory
        self.file_patterns = file_patterns
        self.ignore_patterns = ignore_patterns
        self.max_file_size_kb = max_file_size_kb
        self._files = []

    def prepare(self) -> Path:
        """Prepare directory for analysis.

        Returns:
            Path to the directory

        Raises:
            InputError: If directory doesn't exist
        """
        try:
            validate_directory_exists(self.directory)
            return self.directory
        except Exception as e:
            raise InputError(f"Failed to prepare directory: {e}")

    def get_files(self) -> List[Path]:
        """Get all files from directory.

        Returns:
            List of file paths
        """
        if not self._files:
            self._files = get_files_from_directory(
                self.directory,
                self.file_patterns,
                self.ignore_patterns,
                self.max_file_size_kb,
            )
        return self._files

    def cleanup(self) -> None:
        """No cleanup needed for local directories."""
        pass
