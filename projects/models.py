from django.db import models
from django.contrib.auth.models import User
import reversion


# ──────────────────────────────────────────
# Project
# ──────────────────────────────────────────

@reversion.register()
class Project(models.Model):

    DOMAIN_CHOICES = [
        ('AI',  'Artificial Intelligence'),
        ('ML',  'Machine Learning'),
        ('IoT', 'Internet of Things'),
        ('OT',  'Other'),
    ]

    title       = models.CharField(max_length=200, unique=True)
    domain      = models.CharField(max_length=10, choices=DOMAIN_CHOICES, default='AI')
    description = models.TextField(blank=True)

    # guide is allotted separately by admin after registration
    guide       = models.ForeignKey(
                    User,
                    on_delete=models.SET_NULL,
                    null=True,
                    blank=True,
                    related_name='guided_projects'
                  )

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
        last = self.milestones.filter(
            status='approved'
        ).order_by('-submitted_at').first()
        return last.stage if last else 'Not started'

    def completion_percent(self):
        STAGES = ['synopsis', 'phase1', 'phase2', 'final', 'publication']
        approved = self.milestones.filter(
            status='approved'
        ).values_list('stage', flat=True)
        count = sum(1 for s in STAGES if s in approved)
        return int((count / len(STAGES)) * 100)


# ──────────────────────────────────────────
# Milestone
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
    marks        = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rejection_reason  = models.TextField(
                      blank=True,
                      help_text='Reason for rejection — visible to the student.'
                    )
    submitted_by = models.ForeignKey(
                     User,
                     on_delete=models.SET_NULL,
                     null=True,
                     related_name='submitted_milestones'
                   )
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'stage')
        ordering        = ['project', 'stage']

    def __str__(self):
        return f"{self.project.title} — {self.get_stage_display()} [{self.status}]"


# ──────────────────────────────────────────
# MilestoneVersion
# Every upload = new row. Never overwrite.
# ──────────────────────────────────────────

def upload_path(instance, filename):
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
    file           = models.FileField(upload_to=upload_path)
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


# ──────────────────────────────────────────
# Evaluation
# NEW — sits between milestone uploads and
# CSV export. Drives the coordinator
# approval workflow.
#
# Flow:
#   Guide fills rating + comments
#     → coordinator sees it as pending
#     → coordinator approves + sets
#       publication status + uploads
#       certificate
# ──────────────────────────────────────────

def certificate_upload_path(instance, filename):
    return f"certificates/{instance.project.id}/{filename}"


@reversion.register()
class Evaluation(models.Model):

    PUBLICATION_STATUS_CHOICES = [
        ('not_submitted', 'Not Submitted'),
        ('submitted',     'Submitted'),
        ('accepted',      'Accepted'),
        ('rejected',      'Rejected'),
    ]

    COORDINATOR_APPROVAL_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    RATING_CHOICES = [(i, str(i)) for i in range(1, 11)]  # 1 to 10

    project = models.OneToOneField(
                Project,
                on_delete=models.CASCADE,
                related_name='evaluation'
              )

    # ── guide fields ──────────────────────
    # filled by guide after reviewing uploads
    guide_rating   = models.IntegerField(
                       choices=RATING_CHOICES,
                       null=True,
                       blank=True
                     )
    guide_comments = models.TextField(
                       blank=True,
                       help_text='Guide observations and feedback on the project.'
                     )
    guide_submitted_at = models.DateTimeField(null=True, blank=True)

    # ── coordinator fields ────────────────
    # filled by coordinator after guide submits
    coordinator_approval = models.CharField(
                             max_length=20,
                             choices=COORDINATOR_APPROVAL_CHOICES,
                             default='pending'
                           )
    coordinator_comments = models.TextField(blank=True)
    coordinator_approved_at = models.DateTimeField(null=True, blank=True)

    # ── publication fields ────────────────
    # updated by coordinator after approval
    publication_status = models.CharField(
                           max_length=20,
                           choices=PUBLICATION_STATUS_CHOICES,
                           default='not_submitted'
                         )

    # certificate copy uploaded by coordinator
    certificate_copy = models.FileField(
                         upload_to=certificate_upload_path,
                         null=True,
                         blank=True,
                         help_text='Upload scanned certificate copy (PDF/image).'
                       )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Evaluation — {self.project.title} [{self.coordinator_approval}]"

    def guide_has_submitted(self):
        """True if guide has filled and submitted the evaluation."""
        return self.guide_rating is not None and self.guide_submitted_at is not None

    def is_fully_approved(self):
        """True when coordinator has approved and publication status is set."""
        return (
            self.coordinator_approval == 'approved' and
            self.publication_status != 'not_submitted'
        )
