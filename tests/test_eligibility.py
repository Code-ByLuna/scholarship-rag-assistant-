import pytest
from core.corpus import load_dataset, records
from core.eligibility import evaluate_rule, evaluate_scheme
from core.schemas import Rule, StudentProfile


@pytest.mark.parametrize(
    "op,actual,expected,state",
    [
        ("equals", "female", "female", "PASSED"),
        ("equals", "male", "female", "FAILED"),
        ("not_equals", 2, 3, "PASSED"),
        ("<", 2, 3, "PASSED"),
        ("<=", 3, 3, "PASSED"),
        (">", 3, 3, "FAILED"),
        (">=", 3, 3, "PASSED"),
        ("required", False, True, "FAILED"),
        ("required", None, True, "MISSING"),
        ("in", "SC", ["sc", "st"], "PASSED"),
        ("unknown", 1, 1, "REQUIRES_VERIFICATION"),
    ],
)
def test_operators(op, actual, expected, state):
    rule = Rule(
        field="x", operator=op, required_value=expected, source_path="test", description="test"
    )
    assert evaluate_rule(rule, {"x": actual}).status == state


def scheme(prefix):
    return next(s for s in records() if s["scheme_id"].startswith(prefix))


def test_missing_income_never_passes():
    result = evaluate_scheme(scheme("pm_yasasvi"), {"category": "OBC"})
    assert result.status == "NEEDS_VERIFICATION"
    assert "annual_family_income" in result.missing_information


def test_definite_failure_overrides_missing():
    result = evaluate_scheme(scheme("post_graduate_indira"), {"gender": "male"})
    assert result.status == "NOT_ELIGIBLE"


def test_lateral_entry_unknown_is_missing():
    result = evaluate_scheme(
        scheme("pragati_scholarship_scheme_for_girl_students_technical_degree"),
        {"year_of_study": 2},
    )
    assert not any(r.field == "lateral_entry" for r in result.failed_rules)
    assert "lateral_entry" in result.missing_information


def test_gate_or_unknown_is_not_failed():
    result = evaluate_scheme(
        scheme("post_graduate_scholarship_scheme_for_gate"), {"valid_gate_score": False}
    )
    assert not any(r.operator == "any_true" for r in result.failed_rules)
    assert "valid_ceed_score" in result.missing_information


def test_income_contradiction_never_auto_decides():
    result = evaluate_scheme(
        scheme("pre_matric_scholarship_for_scheduled_tribe"), {"annual_family_income": 999999}
    )
    assert not any(r.field == "annual_family_income" for r in result.failed_rules)
    assert any(r.field == "source_contradiction" for r in result.rule_trace)


def test_unknown_conditions_block_eligible():
    result = evaluate_scheme(
        {"scheme_id": "sample", "name": "sample", "eligibility": {"unmapped": "requires review"}},
        {},
    )
    assert result.status == "NEEDS_VERIFICATION"


def test_fully_mapped_record_can_be_eligible():
    result = evaluate_scheme(
        {
            "scheme_id": "sample",
            "name": "sample",
            "eligibility": {"gender": {"operator": "equals", "value": "female"}},
        },
        {"gender": "female"},
    )
    assert result.status == "ELIGIBLE"


def test_all_records_have_trace():
    for s in load_dataset()["schemes"]:
        r = evaluate_scheme(s, StudentProfile())
        assert r.status == "NEEDS_VERIFICATION"
        assert r.rule_trace


def test_profile_rejects_fabricated_fields_and_wrong_types():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        StudentProfile(annual_family_income="unknown")
    with pytest.raises(ValidationError):
        StudentProfile(gender="female", invented=True)


def test_or_missing_fields_only_include_unknown_values():
    result = evaluate_scheme(
        scheme("post_graduate_scholarship_scheme_for_gate"), {"valid_gate_score": False}
    )
    assert "valid_ceed_score" in result.missing_information
    assert "valid_gate_score" not in result.missing_information


def test_conditional_threshold_missing_only_prerequisite():
    result = evaluate_scheme(scheme("national_means"), {"class7_marks": 70})
    assert "category" in result.missing_information
    assert "class7_marks" not in result.missing_information


def test_explicit_regions_are_hard_constraints():
    result = evaluate_scheme(
        scheme("pragati_scholarship_scheme_for_girl_students_technical_degree"), {"state": "Kerala"}
    )
    assert any(r.field == "state" for r in result.failed_rules)


def test_gate_integrated_exception_is_not_rejected_without_program_verification():
    result = evaluate_scheme(
        scheme("post_graduate_scholarship_scheme_for_gate"),
        {"course_level": "undergraduate", "valid_gate_score": True},
    )
    assert result.status == "NEEDS_VERIFICATION"
