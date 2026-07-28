"""GitHub repository input handler """

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

from pathlib import Path
from typing import List, Optional

from synexian.input.base import BaseInputHandler
from synexian.utils.file_utils import get_files_from_directory
from synexian.utils.git_utils import clone_repository, cleanup_repository
from synexian.utils.validators import validate_github_url
from synexian.exceptions import GitHubError, InputError


class GitHubRepoHandler(BaseInputHandler):
    """Handle GitHub repository input."""

    def __init__(
        self,
        url: str,
        file_patterns: List[str],
        ignore_patterns: List[str],
        max_file_size_kb: int = 1000,
        branch: Optional[str] = None,
        github_token: Optional[str] = None,
    ):
        """Initialize handler.

        Args:
            url: GitHub repository URL
            file_patterns: File patterns to include
            ignore_patterns: Patterns to ignore
            max_file_size_kb: Maximum file size in KB
            branch: Specific branch to clone
            github_token: GitHub token for private repos
        """
        super().__init__(url)
        self.url = validate_github_url(url)
        self.file_patterns = file_patterns
        self.ignore_patterns = ignore_patterns
        self.max_file_size_kb = max_file_size_kb
        self.branch = branch
        self.github_token = github_token
        self._clone_path: Optional[Path] = None
        self._files = []

    def prepare(self) -> Path:
        """Clone the repository.

        Returns:
            Path to cloned repository

        Raises:
            InputError: If cloning fails
        """
        try:
            # Add token to URL if provided
            url = self.url
            if self.github_token and "github.com" in url:
                url = url.replace("https://", f"https://{self.github_token}@")

            self._clone_path = clone_repository(
                url=url,
                branch=self.branch,
                depth=1,  # Shallow clone
            )

            return self._clone_path

        except GitHubError as e:
            raise InputError(f"Failed to clone repository: {e}")

    def get_files(self) -> List[Path]:
        """Get all files from cloned repository.

        Returns:
            List of file paths

        Raises:
            InputError: If files cannot be retrieved
        """
        if not self._clone_path:
            raise InputError("Repository not prepared. Call prepare() first.")

        if not self._files:
            self._files = get_files_from_directory(
                self._clone_path,
                self.file_patterns,
                self.ignore_patterns,
                self.max_file_size_kb,
            )

        return self._files

    def cleanup(self) -> None:
        """Clean up cloned repository."""
        if self._clone_path:
            cleanup_repository(self._clone_path)
            self._clone_path = None
