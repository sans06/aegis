"""Base reporter interface"""

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential


from abc import ABC, abstractmethod
from pathlib import Path

from synexian.models import AnalysisReport


class BaseReporter(ABC):
    """Base class for all reporters."""

    @abstractmethod
    def generate(self, report: AnalysisReport) -> Path:
        """Generate report.

        Args:
            report: Analysis report

        Returns:
            Path to generated report file
        """
        pass
