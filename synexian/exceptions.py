"""Custom exception classes for Aegis """

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential


class SynexianError(Exception):
    """Base exception for all Synexian errors."""
    pass


class ConfigurationError(SynexianError):
    """Raised when there's a configuration error."""
    pass


class InputError(SynexianError):
    """Raised when there's an error with input handling."""
    pass


class AnalyzerError(SynexianError):
    """Raised when an analyzer encounters an error."""

    def __init__(self, analyzer_name: str, message: str):
        self.analyzer_name = analyzer_name
        super().__init__(f"[{analyzer_name}] {message}")


class AIClientError(SynexianError):
    """Raised when there's an error with the AI client."""
    pass


class CacheError(SynexianError):
    """Raised when there's an error with caching."""
    pass


class ValidationError(SynexianError):
    """Raised when validation fails."""
    pass


class SourceNotFoundError(InputError):
    """Raised when a file or directory is not found."""
    pass


class GitHubError(InputError):
    """Raised when there's an error cloning or accessing a GitHub repository."""
    pass


class ParserError(AnalyzerError):
    """Raised when code parsing fails."""

    def __init__(self, analyzer_name: str, file_path: str, message: str):
        self.file_path = file_path
        super().__init__(analyzer_name, f"Failed to parse {file_path}: {message}")


class NetworkError(AIClientError):
    """Raised when there's a network error communicating with the AI service."""
    pass


class RateLimitError(AIClientError):
    """Raised when the AI service rate limit is exceeded."""
    pass


class AnalysisFailedError(SynexianError):
    """Raised when the entire analysis fails."""

    def __init__(self, message: str, partial_results=None):
        self.partial_results = partial_results
        super().__init__(message)
