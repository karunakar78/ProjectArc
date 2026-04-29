import csv
import reversion

from django.shortcuts          import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib             import messages
from django.http                import HttpResponse, JsonResponse
from django.views.generic       import DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils               import timezone

from .models import Project, Milestone, MilestoneVersion, Evaluation
from .forms  import (
    ProjectForm,
    GuideAllotmentForm,
    MilestoneUploadForm,
    EvaluationForm,
    CoordinatorApprovalForm,
    CSVExportForm,
)


# ──────────────────────────────────────────
# Role helpers
# ──────────────────────────────────────────

def is_guide(user):
    return user.is_staff and not user.is_superuser

def is_coordinator(user):
    return user.is_superuser


# ──────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────

@login_required
def dashboard(request):
    user    = request.user
    context = {'user': user}

    if is_coordinator(user):
        context['projects'] = Project.objects.all().select_related('guide')
        context['total']    = context['projects'].count()
        context['role']     = 'coordinator'

        # pending evaluations waiting for coordinator approval
        context['pending_approvals'] = Evaluation.objects.filter(
            coordinator_approval='pending',
            guide_submitted_at__isnull=False
        ).select_related('project')

    elif is_guide(user):
        context['projects'] = Project.objects.filter(
            guide=user
        ).prefetch_related('members', 'milestones')
        context['role'] = 'guide'

        # evaluations this guide needs to submit
        context['pending_evaluations'] = Project.objects.filter(
            guide=user
        ).exclude(
            evaluation__guide_submitted_at__isnull=False
        )

    else:
        context['projects'] = user.enrolled_projects.prefetch_related('milestones')
        context['role']     = 'student'

    return render(request, 'projects/dashboard.html', context)


# ──────────────────────────────────────────
# Project List
# ──────────────────────────────────────────

@login_required
def project_list(request):
    query = request.GET.get('q', '').strip()

    # coordinators and guides see all projects
    # students see only projects they are members of
    if is_coordinator(request.user) or is_guide(request.user):
        projects = Project.objects.select_related('guide').prefetch_related('members')
    else:
        projects = request.user.enrolled_projects.select_related(
            'guide'
        ).prefetch_related('members')

    if query:
        projects = projects.filter(title__icontains=query)

    return render(request, 'projects/project_list.html', {
        'projects': projects,
        'query':    query,
    })


# ──────────────────────────────────────────
# Project Detail
# ──────────────────────────────────────────

class ProjectDetailView(LoginRequiredMixin, DetailView):
    model               = Project
    template_name       = 'projects/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stages  = ['synopsis', 'phase1', 'phase2', 'final', 'publication']

        milestone_map = {}
        for stage in stages:
            milestone_map[stage] = Milestone.objects.filter(
                project=self.object,
                stage=stage
            ).first()

        # get evaluation if it exists
        evaluation = Evaluation.objects.filter(
            project=self.object
        ).first()

        context['milestone_map']  = milestone_map
        context['stages']         = stages
        context['is_guide']       = is_guide(self.request.user)
        context['is_coordinator'] = is_coordinator(self.request.user)
        context['evaluation']     = evaluation
        return context


# ──────────────────────────────────────────
# Register Project
# Guide is NOT selected here — allotted
# separately by coordinator.
# ──────────────────────────────────────────

@login_required
def register_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            with reversion.create_revision():
                project = form.save()
                reversion.set_user(request.user)
                reversion.set_comment('Project registered.')

            # make sure the registering student is always a member
            if request.user not in project.members.all():
                project.members.add(request.user)

            messages.success(
                request,
                f'Project "{project.title}" registered. '
                'A guide will be assigned by the coordinator.'
            )
            return redirect('project_detail', pk=project.pk)
    else:
        # pre-select the logged-in student in the members dropdown
        form = ProjectForm(initial={'members': [request.user.pk]})

    return render(request, 'projects/project_form.html', {'form': form})


# ──────────────────────────────────────────
# Guide Allotment
# Coordinator-only page.
# Lists all projects without a guide +
# lets coordinator assign one via dropdown.
# ──────────────────────────────────────────

@login_required
def allot_guide_list(request):
    if not is_coordinator(request.user):
        messages.error(request, 'Only coordinators can allot guides.')
        return redirect('dashboard')

    unallotted = Project.objects.filter(guide__isnull=True).prefetch_related('members')
    allotted   = Project.objects.filter(guide__isnull=False).select_related('guide')

    return render(request, 'projects/admin_allotment.html', {
        'unallotted': unallotted,
        'allotted':   allotted,
        'total':      unallotted.count() + allotted.count(),  # add this
    })


@login_required
def allot_guide(request, pk):
    if not is_coordinator(request.user):
        messages.error(request, 'Only coordinators can allot guides.')
        return redirect('dashboard')

    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        form = GuideAllotmentForm(request.POST, instance=project)
        if form.is_valid():
            with reversion.create_revision():
                form.save()
                reversion.set_user(request.user)
                reversion.set_comment(
                    f'Guide allotted: {project.guide}'
                )
            messages.success(
                request,
                f'Guide "{project.guide.get_full_name() or project.guide.username}" '
                f'allotted to "{project.title}".'
            )
            return redirect('allot_guide_list')
    else:
        form = GuideAllotmentForm(instance=project)

    return render(request, 'projects/allot_guide_form.html', {
        'form':    form,
        'project': project,
    })


# ──────────────────────────────────────────
# Guide Evaluation
# Guide fills rating + comments after
# reviewing all milestone uploads.
# Only the assigned guide can submit.
# ──────────────────────────────────────────

@login_required
def evaluate(request, pk):
    project = get_object_or_404(Project, pk=pk)

    # only the assigned guide can evaluate
    if not (is_guide(request.user) or is_coordinator(request.user)):
        messages.error(request, 'Only guides can submit evaluations.')
        return redirect('dashboard')

    if is_guide(request.user) and project.guide != request.user:
        messages.error(request, 'You are not the assigned guide for this project.')
        return redirect('dashboard')

    # get or create the evaluation record for this project
    evaluation, created = Evaluation.objects.get_or_create(
        project=project
    )

    # block re-submission if guide already submitted
    if evaluation.guide_has_submitted() and is_guide(request.user):
        messages.warning(
            request,
            'You have already submitted the evaluation for this project. '
            'Awaiting coordinator approval.'
        )
        return redirect('project_detail', pk=pk)

    if request.method == 'POST':
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            eval_obj = form.save(commit=False)
            eval_obj.guide_submitted_at = timezone.now()
            eval_obj.save()

            messages.success(
                request,
                f'Evaluation submitted for "{project.title}". '
                'The coordinator has been notified.'
            )
            return redirect('project_detail', pk=pk)
    else:
        form = EvaluationForm(instance=evaluation)

    return render(request, 'projects/guide_evaluation.html', {
        'form':       form,
        'project':    project,
        'evaluation': evaluation,
    })


# ──────────────────────────────────────────
# Coordinator Approval
# Coordinator reviews guide evaluation,
# sets approval + publication status +
# uploads certificate.
# ──────────────────────────────────────────

@login_required
def coordinator_approve(request, pk):
    if not is_coordinator(request.user):
        messages.error(request, 'Only coordinators can approve evaluations.')
        return redirect('dashboard')

    project    = get_object_or_404(Project, pk=pk)
    evaluation = get_object_or_404(Evaluation, project=project)

    # coordinator can only act after guide has submitted
    if not evaluation.guide_has_submitted():
        messages.warning(
            request,
            'The guide has not submitted the evaluation yet.'
        )
        return redirect('project_detail', pk=pk)

    if request.method == 'POST':
        form = CoordinatorApprovalForm(
            request.POST,
            request.FILES,
            instance=evaluation
        )
        if form.is_valid():
            eval_obj = form.save(commit=False)
            eval_obj.coordinator_approved_at = timezone.now()
            eval_obj.save()

            messages.success(
                request,
                f'Evaluation for "{project.title}" '
                f'{evaluation.get_coordinator_approval_display()}.'
            )
            return redirect('project_detail', pk=pk)
    else:
        form = CoordinatorApprovalForm(instance=evaluation)

    return render(request, 'projects/coordinator_approval.html', {
        'form':       form,
        'project':    project,
        'evaluation': evaluation,
    })


# ──────────────────────────────────────────
# Milestone Upload
# ──────────────────────────────────────────

STAGE_ORDER = ['synopsis', 'phase1', 'phase2', 'final', 'publication']


@login_required
def upload_milestone(request, pk, stage):
    project = get_object_or_404(Project, pk=pk)

    if stage not in STAGE_ORDER:
        messages.error(request, 'Invalid milestone stage.')
        return redirect('project_detail', pk=pk)

    # gate check
    stage_index = STAGE_ORDER.index(stage)
    if stage_index > 0:
        prev_stage     = STAGE_ORDER[stage_index - 1]
        prev_milestone = Milestone.objects.filter(
            project=project,
            stage=prev_stage
        ).first()
        if not prev_milestone or prev_milestone.status != 'approved':
            messages.warning(
                request,
                f'You must complete and get '
                f'"{prev_stage.replace("phase", "Phase ").title()}" '
                f'approved before uploading this stage.'
            )
            return redirect('project_detail', pk=pk)

    if request.method == 'POST':
        form = MilestoneUploadForm(request.POST, request.FILES)
        if form.is_valid():
            milestone, _ = Milestone.objects.get_or_create(
                project=project,
                stage=stage,
                defaults={
                    'status':       'pending',
                    'submitted_by': request.user,
                }
            )
            last_version = milestone.versions.order_by('-version_number').first()
            next_version = (last_version.version_number + 1) if last_version else 1

            version                = form.save(commit=False)
            version.milestone      = milestone
            version.version_number = next_version
            version.uploaded_by    = request.user
            version.save()

            milestone.status       = 'submitted'
            milestone.submitted_by = request.user
            milestone.save()

            messages.success(
                request,
                f'Version {next_version} uploaded. Awaiting guide review.'
            )
            return redirect('project_detail', pk=pk)
    else:
        form = MilestoneUploadForm()

    return render(request, 'milestones/upload.html', {
        'form':    form,
        'project': project,
        'stage':   stage,
    })


# ──────────────────────────────────────────
# Milestone History
# ──────────────────────────────────────────

@login_required
def milestone_history(request, pk, stage):
    project   = get_object_or_404(Project, pk=pk)
    milestone = get_object_or_404(Milestone, project=project, stage=stage)
    versions  = milestone.versions.order_by('-version_number')
    return render(request, 'milestones/history.html', {
        'project':   project,
        'milestone': milestone,
        'versions':  versions,
    })


# ──────────────────────────────────────────
# Approve Milestone
# ──────────────────────────────────────────

@login_required
def approve_milestone(request, milestone_id):
    if not is_guide(request.user) and not is_coordinator(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    milestone = get_object_or_404(Milestone, pk=milestone_id)

    if request.method == 'POST':
        marks = request.POST.get('marks', '').strip()

        # marks are required before approving
        if not marks:
            messages.error(
                request,
                f'Please enter marks before approving '
                f'{milestone.get_stage_display()}.'
            )
            return redirect('project_detail', pk=milestone.project.pk)

        try:
            marks_value = float(marks)
            if marks_value < 0 or marks_value > 100:
                raise ValueError
        except ValueError:
            messages.error(
                request,
                'Marks must be a number between 0 and 100.'
            )
            return redirect('project_detail', pk=milestone.project.pk)

        with reversion.create_revision():
            milestone.status = 'approved'
            milestone.marks  = marks_value
            milestone.save()
            reversion.set_user(request.user)
            reversion.set_comment(
                f'Approved with {marks_value} marks by {request.user.username}.'
            )

        # ── email students ─────────────────────
        from django.core.mail import send_mail
        from django.conf import settings

        project  = milestone.project
        students = project.members.filter(is_staff=False)

        subject = (
            f'[ProjectArc] {milestone.get_stage_display()} '
            f'approved — {project.title}'
        )

        # work out next stage message
        STAGE_ORDER = ['synopsis', 'phase1', 'phase2', 'final', 'publication']
        STAGE_LABELS = {
            'synopsis':    'Synopsis',
            'phase1':      'Phase 1',
            'phase2':      'Phase 2',
            'final':       'Final Report',
            'publication': 'Publication Details',
        }
        current_index = STAGE_ORDER.index(milestone.stage)
        if current_index < len(STAGE_ORDER) - 1:
            next_stage       = STAGE_ORDER[current_index + 1]
            next_stage_label = STAGE_LABELS[next_stage]
            next_step = (
                f'You can now upload your {next_stage_label}.\n'
                f'http://127.0.0.1:8000/projects/{project.pk}'
                f'/upload/{next_stage}/'
            )
        else:
            next_step = (
                'Congratulations — all stages are complete!\n'
                'Your guide will now submit the final evaluation.'
            )

        body = f"""
ProjectArc — Milestone Approved
────────────────────────────────

Project : {project.title}
Stage   : {milestone.get_stage_display()}
Status  : Approved ✓
Marks   : {marks_value} / 100

Guide   : {project.guide.get_full_name() or project.guide.username if project.guide else '—'}

────────────────────────────────
Next Step:
{next_step}
────────────────────────────────
"""

        for student in students:
            if not student.email:
                continue   # skip silently — no email set
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[student.email],
                    fail_silently=True,
                )
            except Exception:
                pass       # never let email failure block the approval

        notified = [s.username for s in students if s.email]
        notif_msg = (
            f'Notified: {", ".join(notified)}' if notified
            else 'No student emails on file.'
        )
        messages.success(
            request,
            f'{milestone.get_stage_display()} approved with '
            f'{marks_value} marks. {notif_msg}'
        )

    return redirect('project_detail', pk=milestone.project.pk)

# ──────────────────────────────────────────
# Reject Milestone
# ──────────────────────────────────────────

@login_required
def reject_milestone(request, milestone_id):
    if not is_guide(request.user) and not is_coordinator(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    milestone = get_object_or_404(Milestone, pk=milestone_id)

    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()

        if not reason:
            messages.error(
                request,
                'Please provide a reason for rejection '
                'so the student knows what to fix.'
            )
            return redirect('project_detail', pk=milestone.project.pk)

        with reversion.create_revision():
            milestone.status           = 'rejected'
            milestone.rejection_reason = reason
            milestone.save()
            reversion.set_user(request.user)
            reversion.set_comment(
                f'Rejected by {request.user.username}. Reason: {reason}'
            )

        # notify student via email
        project  = milestone.project
        students = project.members.filter(is_staff=False)

        subject = (
            f'[ProjectArc] {milestone.get_stage_display()} '
            f'rejected — {project.title}'
        )
        body = f"""
ProjectArc — Milestone Rejected
────────────────────────────────

Project : {project.title}
Stage   : {milestone.get_stage_display()}
Status  : Rejected

Reason:
{reason}

────────────────────────────────
Please log in to ProjectArc,
review the feedback, and re-upload
your document.

http://127.0.0.1:8000/projects/{project.pk}/upload/{milestone.stage}/
────────────────────────────────
"""
        from django.core.mail import send_mail
        from django.conf import settings

        for student in students:
            if not student.email:
                continue   # skip silently — no email set
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[student.email],
                    fail_silently=True,
                )
            except Exception:
                pass

        messages.warning(
            request,
            f'{milestone.get_stage_display()} rejected. '
            'Student notified with reason.'
        )

    return redirect('project_detail', pk=milestone.project.pk)


# ──────────────────────────────────────────
# AJAX Title Check
# ──────────────────────────────────────────

def title_check(request):
    query   = request.GET.get('q', '').strip()
    results = []
    if len(query) >= 3:
        matches = Project.objects.filter(
            title__icontains=query
        ).values_list('title', flat=True)[:5]
        results = list(matches)
    return JsonResponse({'titles': results})


# ──────────────────────────────────────────
# Notification Count (bell badge)
# ──────────────────────────────────────────

@login_required
def notif_count(request):
    from .signals import Notification
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    return JsonResponse({'count': count})


# ──────────────────────────────────────────
# Notifications List
# ──────────────────────────────────────────

@login_required
def notifications_list(request):
    from .signals import Notification
    if not is_coordinator(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    notifs = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')

    notifs.filter(is_read=False).update(is_read=True)

    return render(request, 'notifications/list.html', {
        'notifications': notifs
    })


# ──────────────────────────────────────────
# CSV Export
# Now filters by guide, domain, AND
# publication status from Evaluation.
# ──────────────────────────────────────────

@login_required
def export_csv(request):
    if not is_guide(request.user) and not is_coordinator(request.user):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    form = CSVExportForm(request.GET or None)
    qs   = Project.objects.select_related('guide').prefetch_related(
        'members', 'milestones', 'evaluation'
    )

    if form.is_valid():
        guide              = form.cleaned_data.get('guide')
        domain             = form.cleaned_data.get('domain')
        publication_status = form.cleaned_data.get('publication_status')

        if guide:
            qs = qs.filter(guide=guide)
        if domain:
            qs = qs.filter(domain=domain)
        if publication_status:
            qs = qs.filter(evaluation__publication_status=publication_status)

    if request.GET.get('download'):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="projectarc_export.csv"'
        )
        writer = csv.writer(response)

        # header row
        writer.writerow([
            'Project Title',
            'Domain',
            'Guide',
            'Team Members',
            'Stage',
            'Stage Status',
            'Marks',
            'Guide Rating',
            'Coordinator Approval',
            'Publication Status',
            'Submitted At',
        ])

        for project in qs:
            members_str = ', '.join(
                m.get_full_name() or m.username
                for m in project.members.all()
            )
            guide_str = (
                project.guide.get_full_name() or project.guide.username
                if project.guide else '—'
            )

            # get evaluation data safely
            try:
                ev = project.evaluation
                guide_rating    = ev.guide_rating or '—'
                coord_approval  = ev.get_coordinator_approval_display()
                pub_status      = ev.get_publication_status_display()
            except Evaluation.DoesNotExist:
                guide_rating   = '—'
                coord_approval = '—'
                pub_status     = '—'

            milestones = project.milestones.all()
            if milestones.exists():
                for ms in milestones:
                    writer.writerow([
                        project.title,
                        project.get_domain_display(),
                        guide_str,
                        members_str,
                        ms.get_stage_display(),
                        ms.get_status_display(),
                        ms.marks if ms.marks is not None else '—',
                        guide_rating,
                        coord_approval,
                        pub_status,
                        ms.submitted_at.strftime('%d %b %Y') if ms.submitted_at else '—',
                    ])
            else:
                writer.writerow([
                    project.title,
                    project.get_domain_display(),
                    guide_str,
                    members_str,
                    '—', '—', '—',
                    guide_rating,
                    coord_approval,
                    pub_status,
                    '—',
                ])
        return response

    return render(request, 'exports/confirm.html', {
        'form':     form,
        'projects': qs,
        'count':    qs.count(),
    })
