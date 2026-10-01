"""JSON logs without user message/profile/credential contents."""

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

request_id = ContextVar("request_id", default=None)
logger = logging.getLogger("navigator")


class JSONFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            "request_id": request_id.get(),
        }
        payload.update(getattr(record, "details", {}))
        return json.dumps(payload, default=str)


def event(name: str, **details):
    logger.info(name, extra={"details": details})


class RequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-ID", "")
        rid = supplied if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", supplied) else str(uuid.uuid4())
        token = request_id.set(rid)
        request.request_id = rid
        started = time.perf_counter()
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = rid
            event(
                "http_request",
                endpoint=request.path,
                status=response.status_code,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
            return response
        finally:
            request_id.reset(token)
