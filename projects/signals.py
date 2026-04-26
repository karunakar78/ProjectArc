from django.db.models.signals  import post_save
from django.dispatch           import receiver
from django.contrib.auth.models import User
from django.utils              import timezone
from django.db                 import models


# ──────────────────────────────────────────
# Notification model
# Stores coordinator alerts in the DB.
# Drives the bell badge in the navbar.
# ──────────────────────────────────────────

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
# Signal — notify coordinator when guide
# submits an evaluation.
#
# Trigger: post_save on Evaluation
# Condition: guide_submitted_at just changed
#   from None to a timestamp
#
# Replaces the old Phase 1 completion signal
# per the updated SRS.
# ──────────────────────────────────────────

@receiver(post_save, sender='projects.Evaluation')
def notify_coordinator_on_evaluation(sender, instance, created, **kwargs):
    """
    Fires when a guide saves an evaluation with
    guide_submitted_at populated.
    Notifies all coordinators (superusers).
    """

    # only act when guide has actually submitted
    if not instance.guide_submitted_at:
        return

    # only act when coordinator approval is still pending
    # avoids re-notifying on coordinator's own save
    if instance.coordinator_approval != 'pending':
        return

    coordinators = User.objects.filter(is_superuser=True)
    if not coordinators.exists():
        return

    guide = instance.project.guide
    guide_name = (
        guide.get_full_name() or guide.username
        if guide else 'Unknown Guide'
    )

    message = (
        f"Guide '{guide_name}' has submitted an evaluation "
        f"for project '{instance.project.title}'. "
        f"Rating: {instance.guide_rating}/10. "
        f"Awaiting your approval."
    )

    for coordinator in coordinators:

        # avoid duplicate notifications for the same evaluation
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
