from django.db.models.signals   import post_save
from django.dispatch            import receiver
from django.contrib.auth.models import User
from django.core.mail           import send_mail
from django.conf                import settings
from django.db                  import models


# ──────────────────────────────────────────
# Notification model
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
# Signal — fires when guide submits
# evaluation. Sends DB notification AND
# an email to every coordinator.
# ──────────────────────────────────────────

@receiver(post_save, sender='projects.Evaluation')
def notify_coordinator_on_evaluation(sender, instance, created, **kwargs):

    # only act when guide has submitted
    if not instance.guide_submitted_at:
        return

    # don't re-fire when coordinator saves their own approval
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

    # email content
    subject = (
        f"[ProjectArc] Evaluation submitted — "
        f"{instance.project.title}"
    )

    email_body = f"""
ProjectArc — Evaluation Submission Alert
─────────────────────────────────────────

Guide         : {guide_name}
Project       : {instance.project.title}
Domain        : {instance.project.get_domain_display()}
Rating Given  : {instance.guide_rating} / 10
Submitted At  : {instance.guide_submitted_at.strftime('%d %b %Y, %H:%M')}

Guide Comments:
{instance.guide_comments or 'No comments provided.'}

─────────────────────────────────────────
Please log in to ProjectArc to review and
approve this evaluation.

http://127.0.0.1:8000/coordinator/approve/{instance.project.pk}/
─────────────────────────────────────────
"""

    for coordinator in coordinators:

        # ── DB notification (bell badge) ──
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

        # ── Email notification ─────────────
        # uses coordinator's email if set,
        # falls back to a placeholder
        recipient_email = coordinator.email or 'coordinator@projectarc.local'

        try:
            send_mail(
                subject=subject,
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=True,
                # fail_silently=True means email errors
                # won't crash the evaluation submission
            )
        except Exception:
            # never let email failure break the app
            pass
