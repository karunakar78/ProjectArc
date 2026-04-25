import csv
import reversion

from django.shortcuts         import render, redirect, get_object_or_404
from django.contrib.auth      import login
from django.contrib.auth.decorators import login_required
from django.contrib            import messages
from django.http               import HttpResponse, JsonResponse
from django.views.generic      import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls               import reverse_lazy
from django.utils              import timezone

from .models  import Project, Milestone, MilestoneVersion
from .forms   import ProjectForm, MilestoneUploadForm, CSVExportForm


# ── small helper ──────────────────────────
# Reuse this wherever you need to check roles
# instead of repeating is_staff checks inline.

def is_guide(user):
    """Staff users are treated as guides / faculty."""
    return user.is_staff


def is_coordinator(user):
    """Superusers are treated as coordinators."""
    return user.is_superuser


# ──────────────────────────────────────────
# Dashboard
# What the user sees right after login.
# Role-aware: coordinator, guide, student
# each get a different context.
# ──────────────────────────────────────────

@login_required
def dashboard(request):
    user = request.user
    context = {'user': user}

    if is_coordinator(user):
        # coordinators see everything
        context['projects']     = Project.objects.all().select_related('guide')
        context['total']        = context['projects'].count()
        context['role']         = 'coordinator'

    elif is_guide(user):
        # guides see only their assigned projects
        context['projects']     = Project.objects.filter(
                                    guide=user
                                  ).prefetch_related('members', 'milestones')
        context['role']         = 'guide'

    else:
        # students see only projects they are members of
        context['projects']     = request.user.enrolled_projects.prefetch_related(
                                    'milestones'
                                  )
        context['role']         = 'student'

    return render(request, 'projects/dashboard.html', context)


# ──────────────────────────────────────────
# Project List
# Simple list of all projects.
# Used as the /projects/ browse page.
# ──────────────────────────────────────────

class ProjectListView(LoginRequiredMixin, ListView):
    model               = Project
    template_name       = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by         = 10

    def get_queryset(self):
        # optional ?q= search in the URL
        query = self.request.GET.get('q', '')
        qs    = Project.objects.select_related('guide')
        if query:
            qs = qs.filter(title__icontains=query)
        return qs


# ──────────────────────────────────────────
# Project Create (Register)
# Handles the "Register New Project" form.
# Uses reversion so every save is versioned.
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

            messages.success(
                request,
                f'Project "{project.title}" registered successfully.'
            )
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form})


# ──────────────────────────────────────────
# Project Detail
# Shows all milestone stages and their
# current status for one project.
# ──────────────────────────────────────────

class ProjectDetailView(LoginRequiredMixin, DetailView):
    model               = Project
    template_name       = 'projects/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # build a dict of stage → milestone object (or None)
        # so the template can render every stage row cleanly
        stages = ['synopsis', 'phase1', 'phase2', 'final', 'publication']
        milestone_map = {}
        for stage in stages:
            milestone_map[stage] = Milestone.objects.filter(
                project=self.object,
                stage=stage
            ).first()

        context['milestone_map'] = milestone_map
        context['stages']        = stages
        context['is_guide']      = is_guide(self.request.user)
        context['is_coordinator']= is_coordinator(self.request.user)
        return context
    

# ──────────────────────────────────────────
# Project List
# Simple list of all projects.
# Used as the /projects/ browse page.
# ──────────────────────────────────────────

class ProjectListView(LoginRequiredMixin, ListView):
    model               = Project
    template_name       = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by         = 10

    def get_queryset(self):
        # optional ?q= search in the URL
        query = self.request.GET.get('q', '')
        qs    = Project.objects.select_related('guide')
        if query:
            qs = qs.filter(title__icontains=query)
        return qs


# ──────────────────────────────────────────
# Project Create (Register)
# Handles the "Register New Project" form.
# Uses reversion so every save is versioned.
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

            messages.success(
                request,
                f'Project "{project.title}" registered successfully.'
            )
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form})


# ──────────────────────────────────────────
# Project Detail
# Shows all milestone stages and their
# current status for one project.
# ──────────────────────────────────────────

class ProjectDetailView(LoginRequiredMixin, DetailView):
    model               = Project
    template_name       = 'projects/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # build a dict of stage → milestone object (or None)
        # so the template can render every stage row cleanly
        stages = ['synopsis', 'phase1', 'phase2', 'final', 'publication']
        milestone_map = {}
        for stage in stages:
            milestone_map[stage] = Milestone.objects.filter(
                project=self.object,
                stage=stage
            ).first()

        context['milestone_map'] = milestone_map
        context['stages']        = stages
        context['is_guide']      = is_guide(self.request.user)
        context['is_coordinator']= is_coordinator(self.request.user)
        return context
    

# ──────────────────────────────────────────
# Milestone Upload
# Students upload a file for a given stage.
# Every upload creates a new MilestoneVersion
# row — the file is never overwritten.
# ──────────────────────────────────────────

STAGE_ORDER = ['synopsis', 'phase1', 'phase2', 'final', 'publication']


@login_required
def upload_milestone(request, pk, stage):
    project = get_object_or_404(Project, pk=pk)

    # make sure the stage name is valid
    if stage not in STAGE_ORDER:
        messages.error(request, 'Invalid milestone stage.')
        return redirect('project_detail', pk=pk)

    # gate check — previous stage must be approved before this one
    stage_index = STAGE_ORDER.index(stage)
    if stage_index > 0:
        prev_stage = STAGE_ORDER[stage_index - 1]
        prev_milestone = Milestone.objects.filter(
            project=project,
            stage=prev_stage
        ).first()

        if not prev_milestone or prev_milestone.status != 'approved':
            messages.warning(
                request,
                f'You must complete '
                f'"{prev_stage.replace("phase", "Phase ").title()}" '
                f'before uploading this stage.'
            )
            return redirect('project_detail', pk=pk)

    if request.method == 'POST':
        form = MilestoneUploadForm(request.POST, request.FILES)
        if form.is_valid():

            # get or create the Milestone row for this stage
            milestone, _ = Milestone.objects.get_or_create(
                project=project,
                stage=stage,
                defaults={
                    'status':       'pending',
                    'submitted_by': request.user,
                }
            )

            # find the next version number for this milestone
            last_version = milestone.versions.order_by('-version_number').first()
            next_version = (last_version.version_number + 1) if last_version else 1

            # save the new version row with the uploaded file
            version          = form.save(commit=False)
            version.milestone      = milestone
            version.version_number = next_version
            version.uploaded_by    = request.user
            version.save()

            # mark the milestone as submitted for guide review
            milestone.status       = 'submitted'
            milestone.submitted_by = request.user
            milestone.save()

            messages.success(
                request,
                f'Version {next_version} uploaded successfully. '
                'Awaiting guide review.'
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
# Version History
# Shows all uploaded versions for one stage.
# Guides and students can both view this.
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
# Guide-only POST action.
# Moves milestone status to 'approved'
# and optionally saves marks.
# ──────────────────────────────────────────

@login_required
def approve_milestone(request, milestone_id):
    if not is_guide(request.user) and not is_coordinator(request.user):
        messages.error(request, 'You do not have permission to approve milestones.')
        return redirect('dashboard')

    milestone = get_object_or_404(Milestone, pk=milestone_id)

    if request.method == 'POST':
        marks = request.POST.get('marks', '').strip()

        with reversion.create_revision():
            milestone.status = 'approved'
            if marks:
                try:
                    milestone.marks = float(marks)
                except ValueError:
                    pass
            milestone.save()
            reversion.set_user(request.user)
            reversion.set_comment(f'Approved by {request.user.username}.')

        messages.success(
            request,
            f'{milestone.get_stage_display()} approved for '
            f'"{milestone.project.title}".'
        )

    return redirect('project_detail', pk=milestone.project.pk)


# ──────────────────────────────────────────
# Reject Milestone
# Guide-only POST action.
# Moves milestone back to 'rejected'
# so the student can re-upload.
# ──────────────────────────────────────────

@login_required
def reject_milestone(request, milestone_id):
    if not is_guide(request.user) and not is_coordinator(request.user):
        messages.error(request, 'You do not have permission to reject milestones.')
        return redirect('dashboard')

    milestone = get_object_or_404(Milestone, pk=milestone_id)

    if request.method == 'POST':
        with reversion.create_revision():
            milestone.status = 'rejected'
            milestone.save()
            reversion.set_user(request.user)
            reversion.set_comment(f'Rejected by {request.user.username}.')

        messages.warning(
            request,
            f'{milestone.get_stage_display()} rejected for '
            f'"{milestone.project.title}". Student can re-upload.'
        )

    return redirect('project_detail', pk=milestone.project.pk)



# ──────────────────────────────────────────
# AJAX Title Check
# Called by ajax_search.js as user types.
# Returns JSON list of similar titles.
# No login required — runs on the public
# registration form.
# ──────────────────────────────────────────

def title_check(request):
    query   = request.GET.get('q', '').strip()
    results = []

    if len(query) >= 3:   # only search once at least 3 chars typed
        matches = Project.objects.filter(
            title__icontains=query
        ).values_list('title', flat=True)[:5]
        results = list(matches)

    return JsonResponse({'titles': results})


# ──────────────────────────────────────────
# CSV Export
# Coordinator downloads a filtered CSV.
# Filter params come from GET:
#   ?guide_id=1   → filter by guide
#   ?domain=AI    → filter by domain
# Both are optional — blank = export all.
# ──────────────────────────────────────────

@login_required
def export_csv(request):
    # only coordinators and guides can export
    if not is_guide(request.user) and not is_coordinator(request.user):
        messages.error(request, 'You do not have permission to export data.')
        return redirect('dashboard')

    form = CSVExportForm(request.GET or None)

    # build the queryset
    qs = Project.objects.select_related('guide').prefetch_related(
        'members', 'milestones'
    )

    if form.is_valid():
        guide  = form.cleaned_data.get('guide')
        domain = form.cleaned_data.get('domain')
        if guide:
            qs = qs.filter(guide=guide)
        if domain:
            qs = qs.filter(domain=domain)

    # if it's a download request, stream the CSV
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
            'Status',
            'Marks',
            'Submitted At',
        ])

        # one row per milestone per project
        for project in qs:
            members_str = ', '.join(
                m.get_full_name() or m.username
                for m in project.members.all()
            )
            guide_str = (
                project.guide.get_full_name() or project.guide.username
                if project.guide else '—'
            )

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
                        ms.submitted_at.strftime('%d %b %Y') if ms.submitted_at else '—',
                    ])
            else:
                # project with no milestones yet still appears in export
                writer.writerow([
                    project.title,
                    project.get_domain_display(),
                    guide_str,
                    members_str,
                    '—', '—', '—', '—',
                ])

        return response

    # if not a download request, show the filter form
    return render(request, 'exports/confirm.html', {
        'form':     form,
        'projects': qs,
        'count':    qs.count(),
    })


# ──────────────────────────────────────────
# Notification count
# Called by the bell badge JS in base.html
# every 30 seconds. Returns unread count.
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
# Coordinator clicks the bell and lands here.
# Shows all notifications, marks them read.
# ──────────────────────────────────────────

@login_required
def notifications_list(request):
    from .signals import Notification

    # only coordinators have notifications
    if not is_coordinator(request.user):
        messages.error(request, 'You do not have permission to view notifications.')
        return redirect('dashboard')

    notifs = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')

    # mark all as read when the page is opened
    notifs.filter(is_read=False).update(is_read=True)

    return render(request, 'notifications/list.html', {
        'notifications': notifs
    })


# ──────────────────────────────────────────
# Project List view for browsing
# Supports optional ?q= title search
# ──────────────────────────────────────────

@login_required
def project_list(request):
    query    = request.GET.get('q', '').strip()
    projects = Project.objects.select_related('guide').prefetch_related('members')

    if query:
        projects = projects.filter(title__icontains=query)

    return render(request, 'projects/project_list.html', {
        'projects': projects,
        'query':    query,
    })