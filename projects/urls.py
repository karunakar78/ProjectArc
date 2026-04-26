from django.urls import path
from . import views

urlpatterns = [

    # ── Dashboard ─────────────────────────────────
    path(
        'dashboard/',
        views.dashboard,
        name='dashboard'
    ),

    # ── Projects ──────────────────────────────────
    path(
        'projects/',
        views.project_list,
        name='project_list'
    ),

    path(
        'projects/new/',
        views.register_project,
        name='register_project'
    ),

    path(
        'projects/<int:pk>/',
        views.ProjectDetailView.as_view(),
        name='project_detail'
    ),

    # ── Guide Allotment ───────────────────────────
    # coordinator sees all projects + allotment status
    path(
        'allot-guide/',
        views.allot_guide_list,
        name='allot_guide_list'
    ),

    # coordinator assigns guide to a specific project
    path(
        'allot-guide/<int:pk>/',
        views.allot_guide,
        name='allot_guide'
    ),

    # ── Evaluation ────────────────────────────────
    # guide submits rating + comments
    path(
        'evaluate/<int:pk>/',
        views.evaluate,
        name='evaluate'
    ),

    # coordinator approves + sets publication status
    path(
        'coordinator/approve/<int:pk>/',
        views.coordinator_approve,
        name='coordinator_approve'
    ),

    # ── Milestones ────────────────────────────────
    path(
        'projects/<int:pk>/upload/<str:stage>/',
        views.upload_milestone,
        name='upload_milestone'
    ),

    path(
        'projects/<int:pk>/history/<str:stage>/',
        views.milestone_history,
        name='milestone_history'
    ),

    # ── Guide actions ─────────────────────────────
    path(
        'milestones/<int:milestone_id>/approve/',
        views.approve_milestone,
        name='approve_milestone'
    ),

    path(
        'milestones/<int:milestone_id>/reject/',
        views.reject_milestone,
        name='reject_milestone'
    ),

    # ── AJAX ──────────────────────────────────────
    path(
        'api/title-check/',
        views.title_check,
        name='title_check'
    ),

    path(
        'api/notif-count/',
        views.notif_count,
        name='notif_count'
    ),

    # ── Exports ───────────────────────────────────
    path(
        'export/',
        views.export_csv,
        name='export_csv'
    ),

    # ── Notifications ─────────────────────────────
    path(
        'notifications/',
        views.notifications_list,
        name='notifications_list'
    ),

]
