"""Base input handler interface """

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List


class BaseInputHandler(ABC):
    """Base class for all input handlers."""

    def __init__(self, source: str):
        """Initialize the input handler.

        Args:
            source: Input source (path, URL, etc.)
        """
        self.source = source

    @abstractmethod
    def prepare(self) -> Path:
        """Prepare the input source for analysis.

        Returns:
            Path to the working directory

        Raises:
            InputError: If preparation fails
        """
        pass

    @abstractmethod
    def get_files(self) -> List[Path]:
        """Get list of files to analyze.

        Returns:
            List of file paths

        Raises:
            InputError: If file retrieval fails
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up temporary files if needed."""
        pass

    def __enter__(self):
        """Context manager entry."""
        self.prepare()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
