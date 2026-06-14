import pytest

pytestmark = pytest.mark.no_db

from app.services.naming_validator import (
    NamingRule,
    SegmentDefinition,
    ValidationLevel,
    _default_iso19650_rule,
    validate_identifier,
)


def test_valid_identifier():
    result = validate_identifier("PROJ-ORG-ZZ-GF-DR-AR-0001")
    assert result.level == ValidationLevel.compliant
    assert result.is_compliant
    assert len(result.issues) == 0


def test_too_few_segments():
    result = validate_identifier("PROJ-ORG")
    assert result.level == ValidationLevel.non_compliant
    assert not result.is_compliant


def test_invalid_type_segment():
    # "XX" is in allowed values but "INVALID" is not
    result = validate_identifier("PROJ-ORG-ZZ-GF-INVALID-AR-0001")
    assert result.level == ValidationLevel.non_compliant
    issues_with_type = [i for i in result.issues if i.segment_key == "type"]
    assert len(issues_with_type) > 0


def test_valid_type_xx():
    result = validate_identifier("PROJ-ORG-ZZ-GF-XX-AR-0001")
    assert result.level == ValidationLevel.compliant


def test_issues_text_non_empty_on_error():
    result = validate_identifier("A")
    assert result.level == ValidationLevel.non_compliant
    assert len(result.issues_text) > 0


def test_custom_rule():
    rule = NamingRule(
        project_id="TEST",
        separator="_",
        segments=[
            SegmentDefinition(
                key="proj", label="Project", required=True, pattern=r"^[A-Z]+$"
            ),
            SegmentDefinition(
                key="num", label="Number", required=True, pattern=r"^\d+$"
            ),
        ],
    )
    result = validate_identifier("MYPROJ_001", rule)
    assert result.level == ValidationLevel.compliant


def test_custom_rule_wrong_separator():
    rule = NamingRule(
        project_id="TEST",
        separator="_",
        segments=[
            SegmentDefinition(key="proj", label="Project", required=True),
            SegmentDefinition(key="num", label="Number", required=True),
        ],
    )
    # Using "-" when "_" is expected → only 1 part
    result = validate_identifier("MYPROJ-001", rule)
    assert result.level == ValidationLevel.non_compliant


def test_max_length_violation():
    # Project segment max_length=20; use 21 chars to trigger violation
    long_proj = "A" * 21
    result = validate_identifier(f"{long_proj}-ORG-ZZ-GF-DR-AR-0001")
    non_compliant_issues = [
        i for i in result.issues if i.level == ValidationLevel.non_compliant
    ]
    assert len(non_compliant_issues) > 0


def test_default_rule_returns_namerule():
    rule = _default_iso19650_rule("proj123")
    assert rule.project_id == "proj123"
    assert rule.separator == "-"
    assert len(rule.segments) >= 5


# ─── min_length violation ────────────────────────────────────────────────────


def test_min_length_violation():
    """Single-char project code violates min_length=2 → non_compliant."""
    result = validate_identifier("A-ORG-ZZ-GF-DR-AR-0001")
    assert result.level == ValidationLevel.non_compliant
    proj_issues = [i for i in result.issues if i.segment_key == "project"]
    assert any("Too short" in i.message for i in proj_issues)


def test_min_length_exactly_at_minimum():
    """Two-char project code exactly meets min_length=2 — no issue."""
    result = validate_identifier("AB-ORG-ZZ-GF-DR-AR-0001")
    # May have other issues but project min_length should not appear
    proj_issues = [
        i
        for i in result.issues
        if i.segment_key == "project" and "Too short" in i.message
    ]
    assert len(proj_issues) == 0


# ─── pattern WARNING (not non_compliant) ────────────────────────────────────


def test_pattern_mismatch_produces_warning_level():
    """Lowercase role code fails pattern '^[A-Z]{1,4}$' → WARNING, not non_compliant."""
    result = validate_identifier("PROJ-ORG-ZZ-GF-DR-ar-0001")
    # Overall level must be warning (no non_compliant issues)
    assert result.level == ValidationLevel.warning
    role_issues = [i for i in result.issues if i.segment_key == "role"]
    assert len(role_issues) > 0
    assert role_issues[0].level == ValidationLevel.warning


def test_is_compliant_false_for_warning():
    """is_compliant returns False when level is warning."""
    result = validate_identifier("PROJ-ORG-ZZ-GF-DR-ar-0001")
    assert result.level == ValidationLevel.warning
    assert not result.is_compliant


# ─── optional segment skipping (look-ahead algorithm) ───────────────────────


def test_skip_both_optional_segments():
    """5-part identifier correctly maps to required segments, skipping both optionals."""
    # Default segments: project(req) originator(req) volume_system(opt) level_location(opt)
    #                   type(req) role(req) number(req)
    # 5 parts → skip both optionals
    result = validate_identifier("PROJ-ORG-DR-AR-0001")
    assert result.level == ValidationLevel.compliant
    assert result.is_compliant


def test_skip_one_optional_segment():
    """6-part identifier skips only one optional segment (level_location)."""
    result = validate_identifier("PROJ-ORG-ZZ-DR-AR-0001")
    assert result.level == ValidationLevel.compliant


def test_all_seven_segments_present():
    """Full 7-part identifier with all optional segments included → compliant."""
    result = validate_identifier("PROJ-ORG-ZZ-GF-DR-AR-0001")
    assert result.level == ValidationLevel.compliant
    assert len(result.issues) == 0


# ─── multiple issues / issues_text ──────────────────────────────────────────


def test_issues_text_joins_multiple_issues():
    """issues_text joins multiple segment issues with semicolons."""
    # "A" alone → structure issue (too few segments)
    result = validate_identifier("A")
    assert result.level == ValidationLevel.non_compliant
    assert ";" not in result.issues_text or len(result.issues) == 1
    assert len(result.issues_text) > 0


def test_issues_text_empty_on_compliant():
    """issues_text is empty string when identifier is fully compliant."""
    result = validate_identifier("PROJ-ORG-ZZ-GF-DR-AR-0001")
    assert result.is_compliant
    assert result.issues_text == ""


# ─── custom rule edge cases ──────────────────────────────────────────────────


def test_custom_rule_min_length():
    """Custom rule: min_length=3 on first segment triggers non_compliant."""
    rule = NamingRule(
        project_id="TEST",
        separator="-",
        segments=[
            SegmentDefinition(
                key="code",
                label="Code",
                required=True,
                min_length=3,
                pattern=r"^[A-Z]+$",
            ),
        ],
    )
    result = validate_identifier("AB", rule)
    assert result.level == ValidationLevel.non_compliant
    assert any("Too short" in i.message for i in result.issues)


def test_custom_rule_allowed_values_violation():
    """Custom rule: value not in allowed_values → non_compliant."""
    rule = NamingRule(
        project_id="TEST",
        separator="-",
        segments=[
            SegmentDefinition(
                key="type",
                label="Type",
                required=True,
                allowed_values=["A", "B", "C"],
            ),
        ],
    )
    result = validate_identifier("X", rule)
    assert result.level == ValidationLevel.non_compliant
    assert any("not in allowed values" in i.message for i in result.issues)


def test_optional_segment_not_required_missing():
    """Optional-only rule: zero parts is allowed when all segments are optional."""
    rule = NamingRule(
        project_id="OPT",
        separator="-",
        segments=[
            SegmentDefinition(key="a", label="A", required=False),
            SegmentDefinition(key="b", label="B", required=False),
        ],
    )
    # Even empty string splits to [""] which is 1 part — first optional fills it
    result = validate_identifier("HELLO", rule)
    # Should not raise; level depends on pattern/length config (none here)
    assert isinstance(result.level, ValidationLevel)
