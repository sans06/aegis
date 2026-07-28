"""Aegis - AI-Powered Software Quality Analysis CLI Tool """

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential


__version__ = "0.1.0"
__author__ = "Synexian Team"
__email__ = "contact@synexian.dev"

from synexian.config import Config
from synexian.models import AnalysisReport, AnalysisResult, Issue, MetricValue

__all__ = [
    "Config",
    "AnalysisReport",
    "AnalysisResult",
    "Issue",
    "MetricValue",
    "__version__",
]
