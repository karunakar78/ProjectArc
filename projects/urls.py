from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("projects/", views.ProjectListView.as_view(), name="project_list"),
    path("projects/new/", views.register_project, name="register_project"),
    path(
        "projects/<int:pk>/", views.ProjectDetailView.as_view(), name="project_detail"
    ),
    path(
        "projects/<int:pk>/upload/<str:stage>/",
        views.upload_milestone,
        name="upload_milestone",
    ),
    path(
        "projects/<int:pk>/history/<str:stage>/",
        views.milestone_history,
        name="milestone_history",
    ),
    path(
        "milestones/<int:milestone_id>/approve/",
        views.approve_milestone,
        name="approve_milestone",
    ),
    path(
        "milestones/<int:milestone_id>/reject/",
        views.reject_milestone,
        name="reject_milestone",
    ),
    path("api/title-check/", views.title_check, name="title_check"),
    path("export/", views.export_csv, name="export_csv"),
    path("api/notif-count/", views.notif_count, name="notif_count"),
]
