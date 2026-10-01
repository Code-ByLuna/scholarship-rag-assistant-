"""Small REST handlers; business logic remains in application services."""

from core import corpus, memory
from core.eligibility import check_eligibility
from core.observability import event
from core.schemas import INITIAL_FIELDS, EligibilityRequest, SearchRequest, StudentProfile
from django.db import connection
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from api.common import endpoint


@endpoint("POST", StudentProfile)
def profile_validate(request, payload):
    missing = [f for f in INITIAL_FIELDS if getattr(payload, f) is None]
    return Response(
        {"profile": payload.model_dump(), "valid": not missing, "missing_required_fields": missing},
        status=200 if not missing else 400,
    )


@endpoint("POST", EligibilityRequest)
def eligibility_check(request, payload):
    results = check_eligibility(payload.profile, corpus.records(payload.scheme_ids))
    event(
        "eligibility_check",
        result_counts={
            s: sum(r.status == s for r in results)
            for s in ("ELIGIBLE", "NOT_ELIGIBLE", "NEEDS_VERIFICATION")
        },
    )
    return Response(
        {
            "results": [r.model_dump() for r in results],
            "citations": [
                corpus.citation(
                    corpus.detail(r.scheme_id), r.scheme_id + ":eligibility"
                ).model_dump()
                for r in results
            ],
        }
    )


@endpoint("POST", SearchRequest)
def scholarship_search(request, payload):
    found = corpus.search(**payload.model_dump())
    return Response(
        {
            "results": [
                {
                    "scheme_id": s["scheme_id"],
                    "name": s["name"],
                    "provider": s["provider"],
                    "objective": s.get("objective"),
                    "citation": corpus.citation(s, s["scheme_id"] + ":record").model_dump(),
                }
                for s in found
            ]
        }
    )


@endpoint("GET")
def scholarship_detail(request, payload, scheme_id):
    try:
        scheme = corpus.detail(scheme_id)
    except ValueError:
        return Response(
            {"error": {"code": "NOT_FOUND", "message": "Scholarship not found."}}, status=404
        )
    return Response(
        {
            "scholarship": scheme,
            "citation": corpus.citation(scheme, scheme_id + ":record").model_dump(),
        }
    )


@endpoint("POST")
def sessions_create(request, payload):
    if request.data:
        raise ValueError("Session creation does not accept profile or other arguments.")
    session, token = memory.create_session()
    return Response({"session_id": str(session.id), "session_token": token}, status=201)


@endpoint("GET")
def sessions_detail(request, payload, session_id):
    session = memory.get_session(session_id, request.headers.get("X-Session-Token", ""))
    return Response({"session_id": str(session.id), "context": memory.context(session)})


@endpoint("GET")
def health(request, payload):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    from core.rag.retrieval import index_status

    index = index_status()
    return Response(
        {
            "status": "ok",
            "database": connection.vendor,
            "dataset": {"records": len(corpus.records()), "sha256": corpus.fingerprint()},
            "vector_index": index,
            "assistant": "configured" if index["ready"] else "degraded",
        }
    )


@endpoint("POST", permissions=[IsAdminUser])
def admin_ingest(request, payload):
    from django.core.management import call_command

    call_command("ingest_scholarships")
    return Response({"status": "indexed", "records": len(corpus.records())})


@endpoint("GET", permissions=[IsAdminUser])
def agent_usage(request, payload):
    from apps.navigator.models import LLMUsageLog
    from django.db.models import Sum

    return Response(
        LLMUsageLog.objects.aggregate(
            calls=__import__("django.db.models", fromlist=["Count"]).Count("id"),
            input_tokens=Sum("input_tokens"),
            output_tokens=Sum("output_tokens"),
            total_tokens=Sum("total_tokens"),
            estimated_cost=Sum("estimated_cost"),
        )
    )
