from django.db import models
from django.contrib.auth.models import User
import reversion


# ──────────────────────────────────────────
# Project
# One project per team. A guide is assigned
# and multiple students are team members.
# ──────────────────────────────────────────

@reversion.register()   # tracks history of every save on this model
class Project(models.Model):

    DOMAIN_CHOICES = [
        ('AI',  'Artificial Intelligence'),
        ('ML',  'Machine Learning'),
        ('IoT', 'Internet of Things'),
        ('OT',  'Other'),
    ]

    # title must be unique — enforced at DB level too
    title       = models.CharField(max_length=200, unique=True)
    domain      = models.CharField(max_length=10, choices=DOMAIN_CHOICES, default='AI')
    description = models.TextField(blank=True)

    # guide is a single faculty member (FK = many projects → one guide)
    guide       = models.ForeignKey(
                    User,
                    on_delete=models.SET_NULL,
                    null=True,
                    related_name='guided_projects'
                  )

    # members = multiple students on one project (M2M)
    members     = models.ManyToManyField(
                    User,
                    related_name='enrolled_projects',
                    blank=True
                  )

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def current_stage(self):
        """Returns the latest approved milestone stage name."""
        last = self.milestones.filter(
            status='approved'
        ).order_by('-submitted_at').first()
        return last.stage if last else 'Not started'

    def completion_percent(self):
        """Returns how far through the 5 stages this project is (0–100)."""
        STAGES = ['synopsis', 'phase1', 'phase2', 'final', 'publication']
        approved = self.milestones.filter(status='approved').values_list('stage', flat=True)
        count = sum(1 for s in STAGES if s in approved)
        return int((count / len(STAGES)) * 100)


# ──────────────────────────────────────────
# Milestone
# One row per stage per project.
# Status moves: pending → submitted → approved/rejected
# ──────────────────────────────────────────

@reversion.register()
class Milestone(models.Model):

    STAGE_CHOICES = [
        ('synopsis',    'Synopsis'),
        ('phase1',      'Phase 1'),
        ('phase2',      'Phase 2'),
        ('final',       'Final Report'),
        ('publication', 'Publication Details'),
    ]

    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('submitted', 'Submitted'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
    ]

    project      = models.ForeignKey(
                     Project,
                     on_delete=models.CASCADE,
                     related_name='milestones'
                   )
    stage        = models.CharField(max_length=20, choices=STAGE_CHOICES)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # marks assigned by guide after review (nullable until graded)
    marks        = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    submitted_by = models.ForeignKey(
                     User,
                     on_delete=models.SET_NULL,
                     null=True,
                     related_name='submitted_milestones'
                   )
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        # a project can only have one row per stage
        unique_together = ('project', 'stage')
        ordering = ['project', 'stage']

    def __str__(self):
        return f"{self.project.title} — {self.get_stage_display()} [{self.status}]"


# ──────────────────────────────────────────
# MilestoneVersion
# Every file upload is a new row here.
# Files are never overwritten — this is the
# version history the SRS requires.
# ──────────────────────────────────────────

def upload_path(instance, filename):
    """
    Builds a clean storage path:
    milestones/<project_id>/<stage>/v<N>_<filename>
    """
    return (
        f"milestones/"
        f"{instance.milestone.project.id}/"
        f"{instance.milestone.stage}/"
        f"v{instance.version_number}_{filename}"
    )


class MilestoneVersion(models.Model):

    milestone      = models.ForeignKey(
                       Milestone,
                       on_delete=models.CASCADE,
                       related_name='versions'
                     )

    # file goes to the path built by upload_path()
    file           = models.FileField(upload_to=upload_path)

    # auto-incremented in the view when saving a new version
    version_number = models.PositiveIntegerField(default=1)

    uploaded_by    = models.ForeignKey(
                       User,
                       on_delete=models.SET_NULL,
                       null=True,
                       related_name='uploaded_versions'
                     )
    uploaded_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']

    def __str__(self):
        return (
            f"{self.milestone} — "
            f"v{self.version_number} "
            f"({self.uploaded_at.strftime('%d %b %Y')})"
        ) 