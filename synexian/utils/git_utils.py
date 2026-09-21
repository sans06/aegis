"""Git utility functions """

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from git import Repo
from git.exc import GitCommandError

from synexian.exceptions import GitHubError


def clone_repository(
    url: str,
    destination: Optional[Path] = None,
    branch: Optional[str] = None,
    depth: int = 1,
) -> Path:
    """Clone a Git repository.

    Args:
        url: Repository URL
        destination: Destination directory (temp dir if None)
        branch: Specific branch to clone
        depth: Clone depth (1 for shallow clone)

    Returns:
        Path to cloned repository

    Raises:
        GitHubError: If cloning fails
    """
    try:
        if destination is None:
            destination = Path(tempfile.mkdtemp(prefix="synexian_repo_"))

        clone_kwargs = {
            "depth": depth,
        }

        if branch:
            clone_kwargs["branch"] = branch

        Repo.clone_from(url, destination, **clone_kwargs)
        return destination

    except GitCommandError as e:
        raise GitHubError(f"Failed to clone repository {url}: {e}")


def is_git_repository(path: Path) -> bool:
    """Check if path is a Git repository.

    Args:
        path: Path to check

    Returns:
        True if Git repository
    """
    try:
        Repo(path)
        return True
    except Exception:
        return False


def get_repository_info(path: Path) -> dict:
    """Get information about a Git repository.

    Args:
        path: Path to repository

    Returns:
        Dictionary with repository info
    """
    try:
        repo = Repo(path)

        return {
            "is_dirty": repo.is_dirty(),
            "active_branch": repo.active_branch.name,
            "commit_hash": repo.head.commit.hexsha[:8],
            "commit_message": repo.head.commit.message.strip(),
            "remote_url": repo.remotes.origin.url if repo.remotes else None,
        }
    except Exception:
        return {}


def cleanup_repository(path: Path) -> None:
    """Clean up a cloned repository.

    Args:
        path: Path to repository directory
    """
    try:
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
    except Exception:
        pass
