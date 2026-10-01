from django.urls import path

from api import assistant, views

urlpatterns = [
    path("rag/query", assistant.rag_query),
    path("agent/query", assistant.agent_query),
    path("scholarships/search", views.scholarship_search),
    path("scholarships/<str:scheme_id>", views.scholarship_detail),
    path("sessions", views.sessions_create),
    path("sessions/<str:session_id>", views.sessions_detail),
    path("health", views.health),
    path("admin/ingest", views.admin_ingest),
    path("agent/usage", views.agent_usage),
]
