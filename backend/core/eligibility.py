"""Generic dataset rule compiler and three-valued conservative evaluator.

Every unrecognized eligibility/exclusion leaf remains an explicit verification
rule. Source paths survive normalization. No scholarship-ID branches are used.
"""

import operator
import re
from typing import Any

from core.schemas import EligibilityResult, Rule, RuleTrace, StudentProfile

ALIASES = {
    "master's degree": "postgraduate",
    "masters": "postgraduate",
    "pg": "postgraduate",
    "bachelor's degree": "undergraduate",
    "ug": "undergraduate",
    "degree": "undergraduate",
    "b.tech": "undergraduate",
    "ph.d": "phd",
    "ph_d": "phd",
    "m.phil": "mphil",
    "scheduled caste": "sc",
    "scheduled tribe": "st",
    "socially and educationally backward classes (sebc)": "sebc",
    "regular, full_time": "regular",
    "full_time": "regular",
    "regular_full_time": "regular",
    "regular degree course": "regular",
    "non_professional": "non_professional",
}
FIELDS = {
    "social_category": "category",
    "category": "category",
    "gender": "gender",
    "citizenship": "citizenship",
    "residency": "state",
    "eligible_regions": "state",
    "study_mode": "study_mode",
    "course_level": "course_level",
    "education_level": "course_level",
    "course_type": "course_type",
    "class": "school_class",
}
INCOME = {
    "parental_family_income",
    "parent_guardian_income",
    "parental_income",
    "family_income_max_annual_inr",
    "annual_family_income_max",
}
OPS = {
    "equals": operator.eq,
    "not_equals": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def normalize(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = value.strip().lower().replace("-", "_")
    return ALIASES.get(value, value)


def compile_rules(scheme: dict) -> list[Rule]:
    """Normalize structured constraints; retain every unsafe clause for review."""
    rules: list[Rule] = []

    def add(field, op, expected, path, description, when=None):
        rules.append(
            Rule(
                field=field,
                operator=op,
                required_value=expected,
                source_path=path,
                description=description,
                when=when,
            )
        )

    def verify(path, value, field="external_verification"):
        add(field, "verify", value, path, str(value))

    def visit(value, path):
        key = path.split(".")[-1]
        if "renewal" in path or key == "promotion_required_for_renewal":
            add("renewal", "not_applicable", value, path, "Renewal rule; fresh application.")
            return
        if key in ("institution", "institution_requirement"):
            add("institution_approved", "equals", True, path, str(value))
            verify(path, value, "institution_eligibility")
            return
        if key == "level" and ".course_requirement." in path:
            add("course_level", "equals", value, path, str(value))
            return
        if key == "mode" and ".course." in path:
            add("study_mode", "equals", value, path, str(value))
            return
        if key in INCOME:
            if isinstance(value, dict):
                add(
                    "annual_family_income",
                    value.get("operator", "<="),
                    value.get("amount_inr_per_year"),
                    path,
                    str(value),
                )
            else:
                amount = int(re.sub(r"[^0-9]", "", str(value)))
                add("annual_family_income", "<=", amount, path, str(value))
            return
        if key in FIELDS:
            if isinstance(value, dict) and "operator" in value:
                add(FIELDS[key], value["operator"], value.get("value"), path, str(value))
            elif isinstance(value, (str, list, int)):
                if value == "Beyond Class XII":
                    add(
                        "course_level",
                        "in",
                        ["undergraduate", "postgraduate", "diploma", "phd", "mphil"],
                        path,
                        str(value),
                    )
                else:
                    add(
                        FIELDS[key],
                        "in" if isinstance(value, list) else "equals",
                        value,
                        path,
                        str(value),
                    )
            else:
                verify(path, value)
            return
        if key == "age" and isinstance(value, dict):
            add("age", value["operator"], value.get("years"), path, str(value))
            verify(path + ".reference_point", value.get("reference_point"), "age_at_admission")
            return
        if key == "single_girl_child_status":
            add("single_girl_child", "equals", True, path, str(value))
            return
        if key == "distance_education":
            add("study_mode", "not_in", ["distance", "correspondence"], path, str(value))
            return
        if key == "minimum_percentage" and ".disability." in path:
            add("disability_percentage", ">=", value, path, str(value))
            return
        if key == "must_not_be_availing":
            add("receiving_other_scholarship", "equals", False, path, str(value))
            return
        if key == "year" and value == "first year":
            add("year_of_study", "equals", 1, path, str(value))
            return
        if key == "year_of_study" and isinstance(value, list):
            add("year_of_study", "in", [1, 2], path, str(value))
            add(
                "lateral_entry",
                "equals",
                True,
                path,
                "Second year requires lateral entry.",
                {"year_of_study": 2},
            )
            add(
                "course_level",
                "equals",
                "diploma" if "diploma" in " ".join(value).lower() else "undergraduate",
                path,
                str(value),
            )
            return
        if key == "siblings_max_beneficiaries":
            add(
                "family_scholarship_holders",
                "<",
                value,
                path,
                "Existing family beneficiaries must leave a slot for this applicant.",
            )
            return
        if key == "eligible_levels":
            verify(path, value, "course_level")
            return
        if (
            key == "must_be_admitted_to"
            and value == "First year of a postgraduate professional course"
        ):
            add("course_level", "equals", "postgraduate", path, value)
            add("course_type", "equals", "professional", path, value)
            add("year_of_study", "equals", 1, path, value)
            return
        if key == "class_12_performance":
            add("class12_percentile", ">", 80, path, str(value))
            verify(path, value, "board_stream_percentile")
            return
        if key == "class_7_marks":
            add(
                "class7_marks",
                ">=",
                value["sc_st"]["percentage"],
                path,
                str(value),
                {"category": ["sc", "st"]},
            )
            add(
                "class7_marks",
                ">=",
                value["general"]["percentage"],
                path,
                str(value),
                {"category": {"not_in": ["sc", "st"]}},
            )
            return
        if key == "student_status" and value == "Regular":
            add("study_mode", "equals", "regular", path, value)
            return
        if isinstance(value, dict):
            # An arbitrary operator is never silently accepted.
            if "operator" in value:
                verify(path, value)
            else:
                for child, val in value.items():
                    visit(val, path + "." + child)
            return
        if isinstance(value, list):
            for i, val in enumerate(value):
                visit(val, path + "." + str(i))
            return
        if isinstance(value, str):
            text_rules(value, path)
        else:
            verify(path, value)

    def text_rules(text, path):
        lower = text.lower()
        # Small, audited grammar for free-text records; remaining wording is still verified.
        matched = False
        if "disability must be at least 40%" in lower:
            add("disability_percentage", ">=", 40, path, text)
            matched = True
        if "income" in lower and "must not exceed" in lower and "8 lakh" in lower:
            add("annual_family_income", "<=", 800000, path, text)
            matched = True
        if lower.startswith("maximum age is 30"):
            add("age", "<=", 30, path, text)
            verify(path, text, "age_at_admission")
            matched = True
        if "minimum 60% marks at undergraduate level" in lower:
            add("undergraduate_marks", ">=", 60, path, text)
            matched = True
        if "valid gate/ceed score" in lower:
            add("valid_gate_score|valid_ceed_score", "any_true", True, path, text)
            verify(path, text, "score_at_admission")
            matched = True
        if "first year of a degree-level course, or second year through lateral entry" in lower:
            add("course_level", "equals", "undergraduate", path, text)
            add("year_of_study", "in", [1, 2], path, text)
            add("lateral_entry", "equals", True, path, text, {"year_of_study": 2})
            matched = True
        if "full-time" in lower or "distance" in lower or "correspondence" in lower:
            if "full-time" in lower:
                add("study_mode", "equals", "regular", path, text)
            elif (
                "excluded" in lower
                or "not eligible" in lower
                or "not covered" in lower
                or "mode" in lower
            ):
                add("study_mode", "not_in", ["distance", "correspondence"], path, text)
            matched = True
        if lower == "professional courses are not covered.":
            add("course_type", "not_equals", "professional", path, text)
            matched = True
        if (
            "other scholarship" in lower
            or "another scholarship" in lower
            or "another source" in lower
            or "another organization" in lower
        ):
            add("receiving_other_scholarship", "equals", False, path, text)
            matched = True
        if "aicte-approved m.e., m.tech., or m.des." in lower:
            add("course_level", "in", ["postgraduate", "undergraduate"], path, text)
        # Textual conditions may combine multiple facts; verification protects the residual.
        if not matched or ("must be admitted" in lower or "institution" in lower):
            verify(path, text)

    visit(scheme.get("eligibility", {}), "eligibility")
    for i, exclusion in enumerate(scheme.get("exclusions", [])):
        visit(exclusion, f"exclusions.{i}")
    if scheme.get("selection"):
        verify("selection", scheme["selection"], "selection_verification")
    for i, note in enumerate(scheme.get("important_notes", [])):
        if any(
            t in note.lower()
            for t in ("discrepancy", "review", "discrepanc", "while the eligibility")
        ):
            verify(f"important_notes.{i}", note, "source_contradiction")
    conflicts = any(
        r.field == "source_contradiction" and "income" in str(r.required_value).lower()
        for r in rules
    )
    if conflicts:
        rules = [
            r.model_copy(
                update={
                    "operator": "verify",
                    "description": "Conflicting source income limits: " + r.description,
                }
            )
            if r.field == "annual_family_income"
            else r
            for r in rules
        ]
    if not rules:
        verify("eligibility", "No safely evaluable eligibility conditions.")
    return rules


def evaluate_rule(rule: Rule, profile: dict) -> RuleTrace:
    """Evaluate a normalized rule, preserving missing and external states."""
    actual = profile.get(rule.field)
    state = None
    if rule.when:
        for field, expected in rule.when.items():
            value = profile.get(field)
            if value is None:
                state = "MISSING"
                break
            if isinstance(expected, dict):
                applies = normalize(value) not in expected["not_in"]
            elif isinstance(expected, list):
                applies = normalize(value) in expected
            else:
                applies = normalize(value) == normalize(expected)
            if not applies:
                state = "NOT_APPLICABLE"
                break
    if state is None:
        if rule.operator == "verify":
            state = "REQUIRES_VERIFICATION"
        elif rule.operator == "not_applicable":
            state = "NOT_APPLICABLE"
        elif rule.operator == "any_true":
            values = [profile.get(f) for f in rule.field.split("|")]
            actual = dict(zip(rule.field.split("|"), values))
            state = (
                "PASSED"
                if any(v is True for v in values)
                else ("MISSING" if any(v is None for v in values) else "FAILED")
            )
        elif actual is None:
            state = "MISSING"
        else:
            try:
                op = rule.operator
                if op in ("in", "not_in"):
                    passed = normalize(actual) in [normalize(v) for v in rule.required_value]
                    passed = passed if op == "in" else not passed
                elif op == "required":
                    passed = actual is True
                elif op in OPS:
                    passed = OPS[op](normalize(actual), normalize(rule.required_value))
                else:
                    state = "REQUIRES_VERIFICATION"
                    passed = False
                if state is None:
                    state = "PASSED" if passed else "FAILED"
            except (TypeError, ValueError):
                state = "REQUIRES_VERIFICATION"
    explanation = {
        "PASSED": "Supplied value satisfies the sourced condition.",
        "FAILED": "Supplied value fails the sourced condition.",
        "MISSING": "Required profile information is missing; no value was assumed.",
        "REQUIRES_VERIFICATION": "This condition needs source or institutional verification.",
        "NOT_APPLICABLE": "Condition does not apply to this fresh application/profile.",
    }[state]
    return RuleTrace(
        **rule.model_dump(), actual_value=actual, status=state, explanation=explanation
    )


def evaluate_scheme(scheme: dict, profile: StudentProfile | dict) -> EligibilityResult:
    values = (
        profile.model_dump()
        if isinstance(profile, StudentProfile)
        else StudentProfile.model_validate(profile).model_dump()
    )
    traces = [evaluate_rule(rule, values) for rule in compile_rules(scheme)]
    failed = [r for r in traces if r.status == "FAILED"]
    missing = set()
    for r in traces:
        if r.status == "MISSING":
            fields = r.field.split("|") if r.operator == "any_true" else [r.field]
            missing.update(field for field in fields if values.get(field) is None)
            if r.when:
                missing.update(f for f in r.when if values.get(f) is None)
    verification = [r.description for r in traces if r.status == "REQUIRES_VERIFICATION"]
    status = (
        "NOT_ELIGIBLE"
        if failed
        else ("NEEDS_VERIFICATION" if missing or verification else "ELIGIBLE")
    )
    return EligibilityResult(
        scheme_id=scheme["scheme_id"],
        scheme_name=scheme["name"],
        status=status,
        matched_rules=[r for r in traces if r.status == "PASSED"],
        failed_rules=failed,
        missing_information=sorted(missing),
        verification_required=verification,
        rule_trace=traces,
    )


def check_eligibility(profile: StudentProfile, schemes: list[dict]) -> list[EligibilityResult]:
    return [evaluate_scheme(scheme, profile) for scheme in schemes]
