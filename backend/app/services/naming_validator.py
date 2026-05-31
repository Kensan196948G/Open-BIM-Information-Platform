"""ISO 19650 naming rule validation engine.

Validates information container identifiers against project-defined
segment definitions. Supports configurable separators, segment order,
required/optional segments, and allowed value sets.
"""

import re
from dataclasses import dataclass, field
from enum import Enum


class ValidationLevel(str, Enum):
    compliant = "compliant"
    warning = "warning"
    non_compliant = "non_compliant"


@dataclass
class SegmentDefinition:
    """Definition of a single naming segment."""

    key: str
    label: str
    required: bool = True
    max_length: int | None = None
    min_length: int | None = None
    allowed_values: list[str] = field(default_factory=list)
    pattern: str | None = None  # regex pattern for value
    description: str = ""


@dataclass
class NamingRule:
    """Project-level naming rule configuration."""

    project_id: str
    separator: str = "-"
    segments: list[SegmentDefinition] = field(default_factory=list)


@dataclass
class SegmentValidationIssue:
    segment_key: str
    segment_label: str
    value: str | None
    level: ValidationLevel
    message: str


@dataclass
class ValidationResult:
    identifier: str
    level: ValidationLevel
    issues: list[SegmentValidationIssue] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        return self.level == ValidationLevel.compliant

    @property
    def issues_text(self) -> str:
        return "; ".join(f"[{i.segment_label}] {i.message}" for i in self.issues)


def _default_iso19650_rule(project_id: str) -> NamingRule:
    """ISO 19650-2 Annex A default naming convention."""
    return NamingRule(
        project_id=project_id,
        separator="-",
        segments=[
            SegmentDefinition(
                key="project",
                label="Project",
                required=True,
                min_length=2,
                max_length=20,
                pattern=r"^[A-Z0-9]+$",
                description="Project code (uppercase alphanumeric)",
            ),
            SegmentDefinition(
                key="originator",
                label="Originator",
                required=True,
                min_length=2,
                max_length=10,
                pattern=r"^[A-Z0-9]+$",
                description="Organization code of the originator",
            ),
            SegmentDefinition(
                key="volume_system",
                label="Volume/System",
                required=False,
                max_length=6,
                pattern=r"^[A-Z0-9]+$",
                description="Volume or building system (e.g. ZZ for all)",
            ),
            SegmentDefinition(
                key="level_location",
                label="Level/Location",
                required=False,
                max_length=6,
                pattern=r"^[A-Z0-9]+$",
                description="Floor or location code",
            ),
            SegmentDefinition(
                key="type",
                label="Type",
                required=True,
                min_length=2,
                max_length=4,
                allowed_values=["DR", "M3", "MO", "MS", "WD", "RP", "SK", "SP", "XX"],
                description="Information type code",
            ),
            SegmentDefinition(
                key="role",
                label="Role",
                required=True,
                max_length=4,
                pattern=r"^[A-Z]{1,4}$",
                description="Discipline/role code (e.g. AR, ST, ME)",
            ),
            SegmentDefinition(
                key="number",
                label="Number",
                required=True,
                min_length=4,
                max_length=6,
                pattern=r"^\d+$",
                description="Sequential number (e.g. 0001)",
            ),
        ],
    )


def validate_identifier(
    identifier: str, rule: NamingRule | None = None
) -> ValidationResult:
    """Validate a container identifier against naming rule segments."""
    if rule is None:
        rule = _default_iso19650_rule("default")

    parts = identifier.split(rule.separator)
    required_count = sum(1 for s in rule.segments if s.required)
    issues: list[SegmentValidationIssue] = []

    if len(parts) < required_count:
        return ValidationResult(
            identifier=identifier,
            level=ValidationLevel.non_compliant,
            issues=[
                SegmentValidationIssue(
                    segment_key="structure",
                    segment_label="Structure",
                    value=identifier,
                    level=ValidationLevel.non_compliant,
                    message=(
                        f"Expected at least {required_count} segments separated by "
                        f"'{rule.separator}', got {len(parts)}"
                    ),
                )
            ],
        )

    # Map parts to segments with look-ahead to skip optional segments when
    # doing so is necessary to satisfy remaining required segments.
    # Example: 5 parts against [req, req, opt, opt, req, req, req] → skip both opts.
    segment_values: dict[str, str] = {}
    part_idx = 0
    for seg_idx, seg in enumerate(rule.segments):
        if part_idx >= len(parts):
            if seg.required:
                issues.append(
                    SegmentValidationIssue(
                        segment_key=seg.key,
                        segment_label=seg.label,
                        value=None,
                        level=ValidationLevel.non_compliant,
                        message=f"Required segment '{seg.label}' is missing",
                    )
                )
            continue

        # Look ahead: count remaining required segments after this one
        remaining_required = sum(1 for s in rule.segments[seg_idx + 1 :] if s.required)
        remaining_parts = len(parts) - part_idx

        # Skip optional segment if we'd run out of parts for later required ones
        if not seg.required and remaining_parts <= remaining_required:
            continue

        value = parts[part_idx]
        segment_values[seg.key] = value
        part_idx += 1
        _validate_segment(seg, value, issues)

    level = (
        ValidationLevel.non_compliant
        if any(i.level == ValidationLevel.non_compliant for i in issues)
        else ValidationLevel.warning
        if issues
        else ValidationLevel.compliant
    )
    return ValidationResult(identifier=identifier, level=level, issues=issues)


def _validate_segment(
    seg: SegmentDefinition, value: str, issues: list[SegmentValidationIssue]
) -> None:
    if seg.min_length and len(value) < seg.min_length:
        issues.append(
            SegmentValidationIssue(
                segment_key=seg.key,
                segment_label=seg.label,
                value=value,
                level=ValidationLevel.non_compliant,
                message=f"Too short: min {seg.min_length} chars, got {len(value)}",
            )
        )
    if seg.max_length and len(value) > seg.max_length:
        issues.append(
            SegmentValidationIssue(
                segment_key=seg.key,
                segment_label=seg.label,
                value=value,
                level=ValidationLevel.non_compliant,
                message=f"Too long: max {seg.max_length} chars, got {len(value)}",
            )
        )
    if seg.allowed_values and value not in seg.allowed_values:
        issues.append(
            SegmentValidationIssue(
                segment_key=seg.key,
                segment_label=seg.label,
                value=value,
                level=ValidationLevel.non_compliant,
                message=f"'{value}' not in allowed values: {seg.allowed_values}",
            )
        )
    if seg.pattern and not re.match(seg.pattern, value):
        issues.append(
            SegmentValidationIssue(
                segment_key=seg.key,
                segment_label=seg.label,
                value=value,
                level=ValidationLevel.warning,
                message=f"'{value}' does not match pattern '{seg.pattern}'",
            )
        )
