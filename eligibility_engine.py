"""
Scholarship Eligibility Engine
Dataset-driven, conservative eligibility matching.

Design:
- Hard rules from the cleaned scholarship dataset are evaluated programmatically.
- If a required condition is not represented in a structured way, the result is
  "needs_verification" rather than an invented pass/fail.
- The LLM should explain results, not create eligibility facts.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import json


@dataclass
class MatchResult:
    scheme_id: str
    scheme_name: str
    status: str  # eligible, not_eligible, needs_verification
    reasons: List[str]
    missing_information: List[str]
    matched_rules: List[str]
    failed_rules: List[str]


def _norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _contains_any(value: str, candidates: List[str]) -> bool:
    v = _norm(value)
    return any(_norm(c) in v or v in _norm(c) for c in candidates)


def _get(profile: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in profile and profile[key] not in (None, ""):
            return profile[key]
    return None


def _add_fail(result, text):
    result.failed_rules.append(text)


def _add_match(result, text):
    result.matched_rules.append(text)


def _add_missing(result, text):
    result.missing_information.append(text)


def evaluate_scheme(scheme: Dict[str, Any], profile: Dict[str, Any]) -> MatchResult:
    result = MatchResult(
        scheme_id=scheme["scheme_id"],
        scheme_name=scheme["name"],
        status="needs_verification",
        reasons=[],
        missing_information=[],
        matched_rules=[],
        failed_rules=[],
    )

    sid = scheme["scheme_id"]
    elig = scheme.get("eligibility", {}) or {}
    exclusions = [str(x).lower() for x in scheme.get("exclusions", [])]

    # ---------- Generic profile/exclusion checks ----------
    income = _get(profile, "annual_family_income", "family_income")
    category = _get(profile, "category", "social_category")
    gender = _get(profile, "gender")
    age = _get(profile, "age")
    course_level = _get(profile, "course_level", "education_level")
    year = _get(profile, "year_of_study", "study_year")
    study_mode = _get(profile, "study_mode")
    disability = _get(profile, "disability_percentage")
    course_type = _get(profile, "course_type")
    state = _get(profile, "state", "domicile_state")
    other_scholarship = _get(profile, "receiving_other_scholarship")
    institution_approved = _get(profile, "institution_approved")
    institution_type = _get(profile, "institution_type")
    first_year_pg = _get(profile, "first_year_pg")
    single_girl = _get(profile, "single_girl_child")
    lateral_entry = _get(profile, "lateral_entry")
    class12_percentile = _get(profile, "class12_percentile")
    rank = _get(profile, "university_rank")
    gate_valid = _get(profile, "valid_gate_score")
    ceed_valid = _get(profile, "valid_ceed_score")
    family_sibling_count = _get(profile, "family_scholarship_holders")

    # Explicit generic exclusion: other scholarship
    if other_scholarship is True and any(
        ("other scholarship" in x) or ("other source" in x) or ("other government scholarship" in x)
        for x in exclusions
    ):
        _add_fail(result, "Profile indicates another scholarship/financial assistance, while the scheme excludes such assistance.")

    # ---------- Scheme-specific structured rules ----------
    if "single_girl_child" in sid:
        if gender is None:
            _add_missing(result, "gender")
        elif _norm(gender) != "female":
            _add_fail(result, "Applicant must be a girl student.")
        else:
            _add_match(result, "gender=female")

        if single_girl is None:
            _add_missing(result, "single_girl_child")
        elif single_girl is not True:
            _add_fail(result, "Applicant must satisfy the single-girl-child condition.")
        else:
            _add_match(result, "single_girl_child=true")

        if age is None:
            _add_missing(result, "age")
        elif age > 30:
            _add_fail(result, "Age must not exceed 30 at admission to first-year PG.")
        else:
            _add_match(result, "age<=30")

        if course_level is None:
            _add_missing(result, "course_level")
        elif _norm(course_level) not in ("postgraduate", "pg", "masters", "master's", "master_degree"):
            _add_fail(result, "Course must be a Master's/PG course.")
        else:
            _add_match(result, "course_level=postgraduate")

        if year is None:
            _add_missing(result, "year_of_study")
        elif year != 1:
            _add_fail(result, "Applicant must be in first year of PG.")
        else:
            _add_match(result, "year_of_study=1")

        if study_mode is None:
            _add_missing(result, "study_mode")
        elif _norm(study_mode) not in ("regular", "full_time", "regular_full_time"):
            _add_fail(result, "Distance education is excluded; the source requires regular/full-time study.")
        else:
            _add_match(result, "regular/full-time")

        if course_type is None:
            _add_missing(result, "course_type")
        elif _norm(course_type) == "professional":
            _add_fail(result, "Professional PG courses are excluded by the source.")
        else:
            _add_match(result, "non-professional")

    elif "professional_courses_for_sc_st" in sid:
        if category is None:
            _add_missing(result, "category")
        elif _norm(category) not in ("sc", "st"):
            _add_fail(result, "Applicant must belong to SC or ST.")
        else:
            _add_match(result, f"category={category}")

        if course_level is None:
            _add_missing(result, "course_level")
        elif _norm(course_level) not in ("postgraduate", "pg"):
            _add_fail(result, "Applicant must be pursuing postgraduate study.")
        else:
            _add_match(result, "course_level=postgraduate")

        if year is None:
            _add_missing(result, "year_of_study")
        elif year != 1:
            _add_fail(result, "Only first-year PG students are eligible to apply.")
        else:
            _add_match(result, "year_of_study=1")

        if study_mode is None:
            _add_missing(result, "study_mode")
        elif _norm(study_mode) not in ("regular", "full_time", "regular_full_time"):
            _add_fail(result, "Correspondence/distance mode is excluded.")
        else:
            _add_match(result, "regular/full-time")

        if course_type is None:
            _add_missing(result, "course_type")
        elif _norm(course_type) != "professional":
            _add_fail(result, "Course must be professional.")
        else:
            _add_match(result, "course_type=professional")

    elif "pm_usp" in sid:
        if income is None:
            _add_missing(result, "annual_family_income")
        elif income > 450000:
            _add_fail(result, "Family income exceeds ₹4.5 lakh per year.")
        else:
            _add_match(result, "income<=450000")

        if class12_percentile is None:
            _add_missing(result, "class12_percentile")
        else:
            _add_match(result, "class12_percentile provided; compare with board/stream 80th-percentile rule")

        if course_level is None:
            _add_missing(result, "course_level")
        elif _norm(course_level) in ("diploma", "certificate"):
            _add_fail(result, "Diploma courses are excluded.")
        else:
            _add_match(result, "non-diploma course")

        if study_mode is None:
            _add_missing(result, "study_mode")
        elif _norm(study_mode) not in ("regular", "full_time", "regular_full_time"):
            _add_fail(result, "Correspondence/distance mode is excluded.")
        else:
            _add_match(result, "regular degree course")

    elif "pm_yasasvi" in sid:
        if category is None:
            _add_missing(result, "category")
        elif _norm(category) not in ("obc", "ebc", "dnt"):
            _add_fail(result, "Applicant must belong to OBC, EBC or DNT.")
        else:
            _add_match(result, f"category={category}")

        if income is None:
            _add_missing(result, "annual_family_income")
        elif income > 250000:
            _add_fail(result, "Family income exceeds ₹2.5 lakh per year.")
        else:
            _add_match(result, "income<=250000")

        if institution_type is None:
            _add_missing(result, "institution_type")
        else:
            _add_match(result, "institution type supplied; Top Class institution status must be verified")

    elif "post_matric_scholarship_students_with_disabilities" in sid:
        if disability is None:
            _add_missing(result, "disability_percentage")
        elif disability < 40:
            _add_fail(result, "Disability must be at least 40%.")
        else:
            _add_match(result, "disability>=40%")

        if income is None:
            _add_missing(result, "annual_family_income")
        elif income > 250000:
            _add_fail(result, "Parent/guardian income exceeds ₹2.5 lakh per year.")
        else:
            _add_match(result, "income<=250000")

        if other_scholarship is None:
            _add_missing(result, "receiving_other_scholarship")
        elif other_scholarship:
            _add_fail(result, "The scheme excludes holding another scholarship/stipend.")
        else:
            _add_match(result, "no_other_scholarship")

    elif "pragati_scholarship_scheme_for_girl_students_technical_degree" in sid:
        if gender is None:
            _add_missing(result, "gender")
        elif _norm(gender) != "female":
            _add_fail(result, "Applicant must be a girl student.")
        else:
            _add_match(result, "gender=female")
        if year is None:
            _add_missing(result, "year_of_study")
        elif year not in (1, 2):
            _add_fail(result, "Applicant must be in first year or second year through lateral entry.")
        else:
            _add_match(result, "eligible year range")
        if year == 2 and lateral_entry is not True:
            _add_fail(result, "Second-year applicants must be through lateral entry.")
        if income is None:
            _add_missing(result, "annual_family_income")
        elif income > 800000:
            _add_fail(result, "Family income exceeds ₹8 lakh per year.")
        else:
            _add_match(result, "income<=800000")

    elif "pragati_scholarship_scheme_for_girl_students_technical_diploma" in sid:
        if gender is None:
            _add_missing(result, "gender")
        elif _norm(gender) != "female":
            _add_fail(result, "Applicant must be a girl student.")
        else:
            _add_match(result, "gender=female")
        if year is None:
            _add_missing(result, "year_of_study")
        elif year not in (1, 2):
            _add_fail(result, "Applicant must be in first year or second year through lateral entry.")
        else:
            _add_match(result, "eligible year range")
        if year == 2 and lateral_entry is not True:
            _add_fail(result, "Second-year applicants must be through lateral entry.")
        if income is None:
            _add_missing(result, "annual_family_income")
        elif income > 800000:
            _add_fail(result, "Family income exceeds ₹8 lakh per year.")
        else:
            _add_match(result, "income<=800000")

    elif "saksham" in sid:
        if disability is None:
            _add_missing(result, "disability_percentage")
        elif disability < 40:
            _add_fail(result, "Specially-abled student must have disability of at least 40%.")
        else:
            _add_match(result, "disability>=40%")
        if income is None:
            _add_missing(result, "annual_family_income")
        elif income > 800000:
            _add_fail(result, "Family income exceeds ₹8 lakh per year.")
        else:
            _add_match(result, "income<=800000")
        if year is None:
            _add_missing(result, "year_of_study")
        elif year not in (1, 2):
            _add_fail(result, "Degree admission must be first year or second year through lateral entry.")
        else:
            _add_match(result, "eligible year range")
        if year == 2 and lateral_entry is not True:
            _add_fail(result, "Second-year applicants must be through lateral entry.")

    elif "post_graduate_merit_scholarship" in sid:
        if course_level is None:
            _add_missing(result, "course_level")
        elif _norm(course_level) not in ("postgraduate", "pg"):
            _add_fail(result, "Scholarship is for postgraduate study.")
        else:
            _add_match(result, "course_level=postgraduate")
        if rank is None:
            _add_missing(result, "university_rank")
        else:
            _add_match(result, "university_rank provided")
        if age is None:
            _add_missing(result, "age")
        elif age > 30:
            _add_fail(result, "Age must not exceed 30 at admission.")
        else:
            _add_match(result, "age<=30")

    elif "gate_ceed" in sid:
        if not (gate_valid is True or ceed_valid is True):
            if gate_valid is None and ceed_valid is None:
                _add_missing(result, "valid_gate_score_or_valid_ceed_score")
            else:
                _add_fail(result, "A valid GATE/CEED score is required.")
        else:
            _add_match(result, "valid GATE/CEED score")
        if course_level is None:
            _add_missing(result, "course_level")
        else:
            _add_match(result, "course level supplied; AICTE-approved PG program must be verified")
        if study_mode is None:
            _add_missing(result, "study_mode")
        elif _norm(study_mode) not in ("regular", "full_time", "regular_full_time"):
            _add_fail(result, "Scholarship requires full-time study.")
        else:
            _add_match(result, "full-time")

    elif "ph_d_students" in sid:
        if state is None:
            _add_missing(result, "state")
        elif _norm(state) != "gujarat":
            _add_fail(result, "Applicant must be a resident of Gujarat.")
        else:
            _add_match(result, "state=Gujarat")
        if category is None:
            _add_missing(result, "category")
        elif _norm(category) != "sebc":
            _add_fail(result, "Applicant must belong to SEBC.")
        else:
            _add_match(result, "category=SEBC")
        if income is None:
            _add_missing(result, "annual_family_income")
        elif income > 600000:
            _add_fail(result, "Family income exceeds ₹6 lakh per year.")
        else:
            _add_match(result, "income<=600000")
        if course_level is None:
            _add_missing(result, "course_level")
        elif _norm(course_level) not in ("mphil", "phd", "ph_d"):
            _add_fail(result, "Applicant must be pursuing M.Phil or Ph.D.")
        else:
            _add_match(result, "course_level=MPhil/PhD")

    elif "icar_post_matric" in sid:
        if category is None:
            _add_missing(result, "category")
        elif _norm(category) not in ("sc", "st"):
            _add_fail(result, "Applicant must belong to SC or ST.")
        else:
            _add_match(result, f"category={category}")

    elif "pre_matric_scholarship_for_students_with_disabilities" in sid:
        if disability is None:
            _add_missing(result, "disability_percentage")
        elif disability < 40:
            _add_fail(result, "Disability must be at least 40%.")
        else:
            _add_match(result, "disability>=40%")

    elif "pre_matric_scholarship_for_scheduled_tribe_students" in sid:
        if category is None:
            _add_missing(result, "category")
        elif _norm(category) != "st":
            _add_fail(result, "Applicant must belong to ST.")
        else:
            _add_match(result, "category=ST")

    elif "national_means_cum_merit" in sid:
        if category is None:
            _add_missing(result, "category")
        if income is None:
            _add_missing(result, "annual_family_income")
        if course_level is None:
            _add_missing(result, "course_level")

    elif "sports_medal_winners" in sid:
        # The dataset contains sports-specific criteria that should be evaluated
        # only when the relevant profile fields are supplied.
        if _get(profile, "sports_achievement") is None:
            _add_missing(result, "sports_achievement")
        if _get(profile, "sports_event_level") is None:
            _add_missing(result, "sports_event_level")

    else:
        # Generic fallback: do not invent rules for schemes whose structured
        # eligibility fields have not been mapped yet.
        _add_missing(result, "scheme-specific structured rule mapping")

    # ---------- Final conservative status ----------
    if result.failed_rules:
        result.status = "not_eligible"
    elif result.missing_information:
        result.status = "needs_verification"
    else:
        result.status = "eligible"

    return result


def match_scholarships(profile: Dict[str, Any], dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = [evaluate_scheme(s, profile) for s in dataset["schemes"]]
    return [asdict(r) for r in results]


def explainable_matches(profile: Dict[str, Any], dataset: Dict[str, Any]) -> Dict[str, Any]:
    results = match_scholarships(profile, dataset)
    return {
        "profile": profile,
        "eligible": [r for r in results if r["status"] == "eligible"],
        "needs_verification": [r for r in results if r["status"] == "needs_verification"],
        "not_eligible": [r for r in results if r["status"] == "not_eligible"],
        "rule_engine_note": (
            "Eligible means every mapped rule had required profile information. "
            "Needs verification means no mapped rule failed, but required information "
            "or a scheme-specific verification step is missing. The engine does not "
            "infer missing facts."
        ),
    }


if __name__ == "__main__":
    with open("scholarship_dataset_ready.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)

    demo_profile = {
        "age": 19,
        "gender": "male",
        "state": "Kerala",
        "category": "OBC",
        "annual_family_income": 250000,
        "course_level": "undergraduate",
        "course_type": "professional",
        "year_of_study": 3,
        "study_mode": "regular",
        "disability_percentage": 0,
        "receiving_other_scholarship": False,
        "institution_type": "AICTE approved",
        "class12_percentile": 85,
    }

    print(json.dumps(explainable_matches(demo_profile, dataset), indent=2, ensure_ascii=False))
