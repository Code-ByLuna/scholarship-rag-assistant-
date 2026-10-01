from django.urls import path

from api import views

urlpatterns = [
    path("profile/validate", views.profile_validate),
    path("eligibility/check", views.eligibility_check),
    path("scholarships/search", views.scholarship_search),
    path("scholarships/<str:scheme_id>", views.scholarship_detail),
    path("sessions", views.sessions_create),
    path("sessions/<str:session_id>", views.sessions_detail),
    path("health", views.health),
    path("admin/ingest", views.admin_ingest),
    path("agent/usage", views.agent_usage),
]
