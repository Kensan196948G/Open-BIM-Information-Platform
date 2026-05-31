
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
