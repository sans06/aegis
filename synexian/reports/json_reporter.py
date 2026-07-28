"""JSON report generator"""

#=====================================
# © 2026 Synexian Labs Private Limited
# Proprietary and Confidential

import json
from datetime import datetime
from pathlib import Path

from synexian.models import AnalysisReport
from synexian.reports.base import BaseReporter
from synexian.utils.file_utils import ensure_dir


class JSONReporter(BaseReporter):
    """Generate JSON reports."""

    def __init__(self, output_dir: Path):
        """Initialize reporter.

        Args:
            output_dir: Output directory for reports
        """
        self.output_dir = output_dir

    def generate(self, report: AnalysisReport) -> Path:
        """Generate JSON report.

        Args:
            report: Analysis report

        Returns:
            Path to JSON file
        """
        ensure_dir(self.output_dir)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"synexian_report_{timestamp}.json"
        output_path = self.output_dir / filename

        # Write report
        with open(output_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        # Also write as latest.json
        latest_path = self.output_dir / "latest.json"
        with open(latest_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        return output_path
