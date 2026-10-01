"""Section-aware source chunks; metadata and original-record links never disappear."""

import hashlib
import json
from dataclasses import asdict, dataclass

from core.corpus import citation, records

SECTIONS = (
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
)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    scheme_id: str
    scheme_name: str
    section: str
    text: str
    citation: dict

    def to_dict(self):
        return asdict(self)


def flatten(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(item, (prefix + " / " + key.replace("_", " ")).strip(" /"))
    elif isinstance(value, list):
        for item in value:
            yield from flatten(item, prefix)
    else:
        yield (prefix + ": " if prefix else "") + json.dumps(value, ensure_ascii=False)


def prepare_documents(max_words=150) -> list[Chunk]:
    """Split long sections while keeping source text and section identifiers."""
    chunks = []
    for scheme in records():
        for section in SECTIONS:
            value = scheme.get(section)
            if value in (None, [], {}, ""):
                continue
            text = "\n".join(flatten(value))
            words = text.split()
            for index, start in enumerate(range(0, len(words), max_words)):
                part = " ".join(words[start : start + max_words])
                chunk_id = f"{scheme['scheme_id']}:{section}:{index}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        scheme_id=scheme["scheme_id"],
                        scheme_name=scheme["name"],
                        section=section,
                        text=part,
                        citation=citation(scheme, chunk_id).model_dump(),
                    )
                )
    return chunks


def content_hash(chunk: Chunk) -> str:
    return hashlib.sha256(chunk.text.encode()).hexdigest()
