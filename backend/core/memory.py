"""Opaque session tokens protect persistent conversation data."""

import hashlib
import secrets

from apps.navigator.models import ConversationMessage, StudentProfile, UserSession
from django.db import transaction


def create_session() -> tuple[UserSession, str]:
    token = secrets.token_urlsafe(32)
    session = UserSession.objects.create(token_hash=hashlib.sha256(token.encode()).hexdigest())
    return session, token


def get_session(session_id: str, token: str) -> UserSession:
    try:
        session = UserSession.objects.get(pk=session_id)
    except (UserSession.DoesNotExist, ValueError):
        raise PermissionError("Session not found or token invalid.") from None
    supplied = hashlib.sha256(token.encode()).hexdigest()
    if not secrets.compare_digest(supplied, session.token_hash):
        raise PermissionError("Session not found or token invalid.")
    return session


def context(session: UserSession) -> dict:
    messages = list(session.messages.order_by("-id")[:8])
    profile = getattr(session, "student_profile", None)
    last_ids = []
    for message in messages:
        if message.role == "assistant":
            last_ids = message.content.get("scheme_ids", [])
            break
    return {
        "profile": profile.values if profile else None,
        "scheme_ids": last_ids,
        "messages": [{"role": m.role, "content": m.content} for m in reversed(messages)],
    }


@transaction.atomic
def save_turn(session, question, answer, profile=None):
    ConversationMessage.objects.create(session=session, role="user", content={"question": question})
    ConversationMessage.objects.create(session=session, role="assistant", content=answer)
    if profile is not None:
        StudentProfile.objects.update_or_create(session=session, defaults={"values": profile})
    session.save(update_fields=["updated_at"])
