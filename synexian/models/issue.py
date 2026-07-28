"""Issue models for the Aegis """

#=====================================
#  2026 Synexian Labs Private Limited
# Proprietary and Confidential

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from synexian.constants import IssueCategory, Severity


@dataclass
class Issue:
    """A single issue or finding detected during analysis."""

    severity: Severity
    category: IssueCategory
    title: str
    description: str
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None
    references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary."""
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "file_path": str(self.file_path) if self.file_path else None,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
            "rule_id": self.rule_id,
            "references": self.references,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Issue":
        """Create Issue from dictionary."""
        return cls(
            severity=Severity(data["severity"]),
            category=IssueCategory(data["category"]),
            title=data["title"],
            description=data["description"],
            file_path=Path(data["file_path"]) if data.get("file_path") else None,
            line_number=data.get("line_number"),
            column_number=data.get("column_number"),
            code_snippet=data.get("code_snippet"),
            suggestion=data.get("suggestion"),
            rule_id=data.get("rule_id"),
            references=data.get("references", []),
        )

    def format_for_cli(self) -> str:
        """Format issue for CLI display."""
        severity_colors = {
            Severity.CRITICAL: "red",
            Severity.HIGH: "orange_red1",
            Severity.MEDIUM: "yellow",
            Severity.LOW: "blue",
            Severity.INFO: "cyan",
        }

        location = ""
        if self.file_path:
            location = f"{self.file_path}"
            if self.line_number:
                location += f":{self.line_number}"
                if self.column_number:
                    location += f":{self.column_number}"

        output = f"[{severity_colors.get(self.severity, 'white')}]{self.severity.value.upper()}[/] {self.title}\n"

        if location:
            output += f"  Location: {location}\n"

        output += f"  {self.description}\n"

        if self.suggestion:
            output += f"  Suggestion: {self.suggestion}\n"

        if self.rule_id:
            output += f"  Rule: {self.rule_id}\n"

        return output

    def get_location_string(self) -> Optional[str]:
        """Get a formatted location string for this issue."""
        if not self.file_path:
            return None

        location = str(self.file_path)
        if self.line_number:
            location += f":{self.line_number}"
            if self.column_number:
                location += f":{self.column_number}"

        return location
