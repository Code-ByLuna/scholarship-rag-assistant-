"""Validated profiles, deterministic decisions, and public assistant responses."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt

Status = Literal["ELIGIBLE", "NOT_ELIGIBLE", "NEEDS_VERIFICATION"]
RuleState = Literal["PASSED", "FAILED", "MISSING", "REQUIRES_VERIFICATION", "NOT_APPLICABLE"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StudentProfile(StrictModel):
    state: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    annual_family_income: StrictFloat | None = Field(default=None, ge=0)
    course_level: str | None = Field(default=None, min_length=1, max_length=100)
    year_of_study: StrictInt | None = Field(default=None, ge=1, le=20)
    study_mode: str | None = Field(default=None, min_length=1, max_length=100)
    age: StrictInt | None = Field(default=None, ge=0, le=120)
    gender: str | None = Field(default=None, max_length=40)
    course_type: str | None = Field(default=None, max_length=100)
    disability_percentage: StrictFloat | None = Field(default=None, ge=0, le=100)
    receiving_other_scholarship: StrictBool | None = None
    institution_type: str | None = Field(default=None, max_length=200)
    institution_approved: StrictBool | None = None
    single_girl_child: StrictBool | None = None
    lateral_entry: StrictBool | None = None
    class12_percentile: StrictFloat | None = Field(default=None, ge=0, le=100)
    university_rank: StrictInt | None = Field(default=None, ge=1)
    valid_gate_score: StrictBool | None = None
    valid_ceed_score: StrictBool | None = None
    family_scholarship_holders: StrictInt | None = Field(default=None, ge=0)
    sports_achievement: str | None = Field(default=None, max_length=500)
    sports_event_level: str | None = Field(default=None, max_length=100)
    citizenship: str | None = Field(default=None, max_length=100)
    school_class: StrictInt | None = Field(default=None, ge=1, le=12)
    class7_marks: StrictFloat | None = Field(default=None, ge=0, le=100)
    undergraduate_marks: StrictFloat | None = Field(default=None, ge=0, le=100)


INITIAL_FIELDS = (
    "state",
    "category",
    "annual_family_income",
    "course_level",
    "year_of_study",
    "study_mode",
)


class Rule(StrictModel):
    field: str
    operator: str
    required_value: Any = None
    source_path: str
    description: str
    when: dict[str, Any] | None = None


class RuleTrace(Rule):
    actual_value: Any = None
    status: RuleState
    explanation: str


class EligibilityResult(StrictModel):
    scheme_id: str
    scheme_name: str
    status: Status
    matched_rules: list[RuleTrace]
    failed_rules: list[RuleTrace]
    missing_information: list[str]
    verification_required: list[str]
    rule_trace: list[RuleTrace]


class Citation(StrictModel):
    scheme_id: str
    scheme_name: str
    source_name: str | None = None
    source_url: str | None = None
    retrieved_from: str
    original_record_key: str | None = None


class Evidence(StrictModel):
    chunk_id: str
    scheme_id: str
    section: str
    text: str


class WarningItem(StrictModel):
    code: str
    message: str


class ScholarshipAnswer(StrictModel):
    answer: str
    scheme_ids: list[str]
    citations: list[Citation]
    eligibility: list[EligibilityResult] = Field(default_factory=list)
    required_documents: dict[str, list[str]] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    explanation_state: Literal["GROUNDED", "DETERMINISTIC_FALLBACK", "INSUFFICIENT_SOURCES"]
    warnings: list[WarningItem] = Field(default_factory=list)
    timings_ms: dict[str, float] = Field(default_factory=dict)
    request_id: str | None = None
    session_id: str | None = None


class SearchRequest(StrictModel):
    question: str = Field(default="", max_length=2000)
    scheme_ids: list[str] | None = Field(default=None, max_length=16)
    category: str | None = Field(default=None, max_length=100)
    top_k: int = Field(default=5, ge=1, le=16)


class EligibilityRequest(StrictModel):
    profile: StudentProfile
    scheme_ids: list[str] | None = Field(default=None, max_length=16)


class QueryRequest(SearchRequest):
    question: str = Field(min_length=1, max_length=2000)
    profile: StudentProfile | None = None
    session_id: str | None = Field(default=None, max_length=40)


class Quote(StrictModel):
    chunk_id: str
    quote: str = Field(min_length=1, max_length=3000)


class GroundedDraft(StrictModel):
    fragments: list[Quote] = Field(min_length=1, max_length=8)
