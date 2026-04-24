from django.urls import path
from . import views

urlpatterns = [

    # ── Dashboard ─────────────────────────────────
    # First page after login
    path(
        'dashboard/',
        views.dashboard,
        name='dashboard'
    ),

    # ── Projects ──────────────────────────────────
    # Browse all projects (with optional ?q= search)
    path(
        'projects/',
        views.ProjectListView.as_view(),
        name='project_list'
    ),

    # Register a new project
    path(
        'projects/new/',
        views.register_project,
        name='register_project'
    ),

    # View one project and all its milestone stages
    path(
        'projects/<int:pk>/',
        views.ProjectDetailView.as_view(),
        name='project_detail'
    ),

    # ── Milestones ────────────────────────────────
    # Upload a file for a specific stage
    # stage is one of: synopsis, phase1, phase2, final, publication
    path(
        'projects/<int:pk>/upload/<str:stage>/',
        views.upload_milestone,
        name='upload_milestone'
    ),

    # View all uploaded versions for a stage
    path(
        'projects/<int:pk>/history/<str:stage>/',
        views.milestone_history,
        name='milestone_history'
    ),

    # ── Guide actions ─────────────────────────────
    # Approve a milestone (POST only, guide/coordinator)
    path(
        'milestones/<int:milestone_id>/approve/',
        views.approve_milestone,
        name='approve_milestone'
    ),

    # Reject a milestone (POST only, guide/coordinator)
    path(
        'milestones/<int:milestone_id>/reject/',
        views.reject_milestone,
        name='reject_milestone'
    ),

    # ── AJAX ──────────────────────────────────────
    # Called by ajax_search.js as user types a title
    # Returns JSON — not a HTML page
    path(
        'api/title-check/',
        views.title_check,
        name='title_check'
    ),

    # ── Exports ───────────────────────────────────
    # Filter form + download CSV
    # Add ?download=1 to the URL to trigger file download
    path(
        'export/',
        views.export_csv,
        name='export_csv'
    ),

]