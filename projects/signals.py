from django.db.models.signals import post_save
from django.dispatch           import receiver
from django.contrib.auth.models import User
from django.utils              import timezone

from .models import Milestone


# ──────────────────────────────────────────
# Notification model (lightweight)
# Stored in the DB so coordinators can see
# a bell badge on their dashboard.
# We define it here to keep things simple —
# no separate notifications app needed.
# ──────────────────────────────────────────

from django.db import models

class Notification(models.Model):

    recipient  = models.ForeignKey(
                   User,
                   on_delete=models.CASCADE,
                   related_name='notifications'
                 )
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"→ {self.recipient.username}: {self.message[:60]}"


# ──────────────────────────────────────────
# Signal receiver
# Runs every time any Milestone is saved.
# Only acts when:
#   1. The stage is 'phase1'
#   2. The new status is 'approved'
# ──────────────────────────────────────────

@receiver(post_save, sender=Milestone)
def check_phase1_complete(sender, instance, **kwargs):
    """
    When a Phase 1 milestone is approved, check if ALL projects
    under the same guide have their Phase 1 approved.
    If yes — notify every coordinator.
    """

    # ignore saves that are not a Phase 1 approval
    if instance.stage != 'phase1' or instance.status != 'approved':
        return

    guide = instance.project.guide
    if not guide:
        return

    # get all projects assigned to this guide
    all_projects = guide.guided_projects.all()

    if not all_projects.exists():
        return

    # check if every one of those projects has an approved Phase 1
    all_done = all(
        Milestone.objects.filter(
            project=project,
            stage='phase1',
            status='approved'
        ).exists()
        for project in all_projects
    )

    if not all_done:
        return   # some teams still haven't finished Phase 1

    # ── all teams done — notify every coordinator ──
    coordinators = User.objects.filter(is_superuser=True)

    if not coordinators.exists():
        return

    message = (
        f"All teams under guide '{guide.get_full_name() or guide.username}' "
        f"have completed Phase 1. "
        f"({all_projects.count()} project(s) cleared.)"
    )

    for coordinator in coordinators:

        # avoid duplicate notifications —
        # don't re-notify if this message already exists unread
        already_notified = Notification.objects.filter(
            recipient=coordinator,
            message=message,
            is_read=False
        ).exists()

        if not already_notified:
            Notification.objects.create(
                recipient=coordinator,
                message=message
            )