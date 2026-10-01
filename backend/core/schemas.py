"""Public RAG requests, generated answers, and traceable source evidence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Citation(StrictModel):
    scheme_id: str
    scheme_name: str
    source_name: str | None = None
    source_url: str | None = None
    retrieved_from: str
    original_record_key: str | None = None
    excerpt: str | None = None


class ErrorItem(StrictModel):
    code: str
    message: str


class ScholarshipAnswer(StrictModel):
    answer: str
    sources: list[Citation] = Field(max_length=16)
    status: Literal["success", "out_of_scope", "insufficient_evidence", "error"]
    error: ErrorItem | None = None
    request_id: str | None = None
    session_id: str | None = None


class SearchRequest(StrictModel):
    question: str = Field(default="", max_length=2000)
    scheme_ids: list[str] | None = Field(default=None, max_length=16)
    category: str | None = Field(default=None, max_length=100)
    top_k: int = Field(default=8, ge=1, le=16)


class RetrievalRequest(SearchRequest):
    intent: str | None = Field(default=None, max_length=30)
    sections: (
        list[
            Literal[
                "objective",
                "target_groups",
                "tags",
                "benefits",
                "eligibility",
                "documents_required",
                "application",
                "exclusions",
                "selection",
                "important_notes",
            ]
        ]
        | None
    ) = Field(default=None, max_length=10)


class QueryRequest(SearchRequest):
    context_scheme_id: str | None = Field(default=None, min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=40)


class Quote(StrictModel):
    chunk_id: str
    quote: str = Field(min_length=1, max_length=3000)


class GroundedDraft(StrictModel):
    answer: str = Field(min_length=1, max_length=8000)
    status: Literal["success", "out_of_scope", "insufficient_evidence"]
    supports: list[Quote] = Field(max_length=16)


class ClarificationDraft(GroundedDraft):
    status: Literal["insufficient_evidence"]
    supports: list[Quote] = Field(default_factory=list, max_length=0)


class GroundingReview(StrictModel):
    notes_examined: list[str] = Field(default_factory=list, max_length=32)
    supported: StrictBool
    issues: list[str] = Field(max_length=16)
