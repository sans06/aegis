"""Single file input handler """

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

from pathlib import Path
from typing import List

from synexian.input.base import BaseInputHandler
from synexian.utils.validators import validate_file_exists
from synexian.exceptions import InputError


class SingleFileHandler(BaseInputHandler):
    """Handle single file input."""

    def __init__(self, file_path: Path):
        """Initialize handler.

        Args:
            file_path: File to analyze
        """
        super().__init__(str(file_path))
        self.file_path = file_path

    def prepare(self) -> Path:
        """Prepare file for analysis.

        Returns:
            Path to the file's parent directory

        Raises:
            InputError: If file doesn't exist
        """
        try:
            validate_file_exists(self.file_path)
            return self.file_path.parent
        except Exception as e:
            raise InputError(f"Failed to prepare file: {e}")

    def get_files(self) -> List[Path]:
        """Get the single file.

        Returns:
            List containing the single file path
        """
        return [self.file_path]

    def cleanup(self) -> None:
        """No cleanup needed for single files."""
        pass
