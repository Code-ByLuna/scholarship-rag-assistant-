from core import memory
from core.agent.workflow import query
from core.schemas import QueryRequest, ScholarshipAnswer
from rest_framework.response import Response

from api.common import endpoint


def execute(request, payload):
    session = (
        memory.get_session(payload.session_id, request.headers.get("X-Session-Token", ""))
        if payload.session_id
        else None
    )
    answer = query(payload, request.request_id, session)
    return Response(answer.model_dump())


@endpoint("POST", QueryRequest, response_schema=ScholarshipAnswer.model_json_schema())
def agent_query(request, payload):
    return execute(request, payload)


@endpoint("POST", QueryRequest, response_schema=ScholarshipAnswer.model_json_schema())
def rag_query(request, payload):
    return execute(request, payload)
