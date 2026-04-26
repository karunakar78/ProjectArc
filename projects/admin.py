from django.contrib    import admin
from django.utils.html import format_html, mark_safe

import reversion
from reversion.admin import VersionAdmin

from .models  import Project, Milestone, MilestoneVersion, Evaluation
from .signals import Notification


# ──────────────────────────────────────────
# Inlines
# ──────────────────────────────────────────

class MilestoneVersionInline(admin.TabularInline):
    model           = MilestoneVersion
    extra           = 0
    can_delete      = False
    readonly_fields = ['version_number', 'file', 'uploaded_by', 'uploaded_at', 'file_link']

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">Download v{}</a>',
                obj.file.url, obj.version_number)
        return '-'
    file_link.short_description = 'Download'


class MilestoneInline(admin.TabularInline):
    model           = Milestone
    extra           = 0
    readonly_fields = ['submitted_by', 'submitted_at']
    fields          = ['stage', 'status', 'marks', 'submitted_by', 'submitted_at']


class EvaluationInline(admin.StackedInline):
    model           = Evaluation
    extra           = 0
    can_delete      = False
    readonly_fields = ['guide_submitted_at', 'coordinator_approved_at', 'created_at', 'updated_at']
    fields = [
        'guide_rating', 'guide_comments', 'guide_submitted_at',
        'coordinator_approval', 'coordinator_comments', 'coordinator_approved_at',
        'publication_status', 'certificate_copy',
        'created_at', 'updated_at',
    ]


# ──────────────────────────────────────────
# Project Admin
# ──────────────────────────────────────────

@admin.register(Project)
class ProjectAdmin(VersionAdmin):

    list_display  = ['title', 'domain', 'guide_name', 'member_count',
                     'completion', 'evaluation_status', 'publication', 'created_at']
    list_filter   = ['domain', 'guide', 'created_at']
    search_fields = ['title', 'members__username', 'members__first_name', 'guide__username']
    readonly_fields = ['created_at', 'updated_at']
    inlines       = [MilestoneInline, EvaluationInline]

    fieldsets = [
        ('Project Info', {'fields': ['title', 'domain', 'description']}),
        ('Team',         {'fields': ['guide', 'members']}),
        ('Timestamps',   {'fields': ['created_at', 'updated_at'], 'classes': ['collapse']}),
    ]

    def guide_name(self, obj):
        if obj.guide:
            return obj.guide.get_full_name() or obj.guide.username
        return 'Not assigned'
    guide_name.short_description = 'Guide'

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Team'

    def completion(self, obj):
        pct   = obj.completion_percent()
        color = '#2ecc71' if pct >= 80 else '#f39c12' if pct >= 40 else '#e74c3c'
        return format_html(
            '<div style="width:100px;background:#eee;border-radius:4px">'
            '<div style="width:{0}%;background:{1};height:12px;border-radius:4px;'
            'text-align:center;font-size:10px;color:white;line-height:12px">'
            '{0}%</div></div>',
            pct, color
        )
    completion.short_description = 'Progress'

    def evaluation_status(self, obj):
        try:
            ev    = obj.evaluation
            color = {'pending': '#f39c12', 'approved': '#2ecc71',
                     'rejected': '#e74c3c'}.get(ev.coordinator_approval, '#ccc')
            return format_html(
                '<span style="background:{};color:white;padding:2px 10px;'
                'border-radius:10px;font-size:11px">{}</span>',
                color, ev.get_coordinator_approval_display()
            )
        except Evaluation.DoesNotExist:
            return 'No evaluation'
    evaluation_status.short_description = 'Evaluation'

    def publication(self, obj):
        try:
            ev    = obj.evaluation
            color = {
                'not_submitted': '#bdc3c7', 'submitted': '#3498db',
                'accepted': '#2ecc71',      'rejected':  '#e74c3c',
            }.get(ev.publication_status, '#ccc')
            return format_html(
                '<span style="background:{};color:white;padding:2px 10px;'
                'border-radius:10px;font-size:11px">{}</span>',
                color, ev.get_publication_status_display()
            )
        except Evaluation.DoesNotExist:
            return '-'
    publication.short_description = 'Publication'


# ──────────────────────────────────────────
# Milestone Admin
# ──────────────────────────────────────────

@admin.register(Milestone)
class MilestoneAdmin(VersionAdmin):

    list_display    = ['project', 'stage', 'status_badge', 'marks',
                       'submitted_by', 'submitted_at']
    list_filter     = ['stage', 'status']
    search_fields   = ['project__title', 'submitted_by__username']
    readonly_fields = ['submitted_by', 'submitted_at']
    inlines         = [MilestoneVersionInline]

    @admin.action(description='Approve selected milestones')
    def bulk_approve(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} milestone(s) approved.')

    @admin.action(description='Reject selected milestones')
    def bulk_reject(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} milestone(s) rejected.')

    actions = ['bulk_approve', 'bulk_reject']

    def status_badge(self, obj):
        colors = {
            'pending':   '#95a5a6',
            'submitted': '#3498db',
            'approved':  '#2ecc71',
            'rejected':  '#e74c3c',
        }
        return format_html(
            '<span style="background:{};color:white;padding:2px 10px;'
            'border-radius:10px;font-size:11px">{}</span>',
            colors.get(obj.status, '#ccc'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ──────────────────────────────────────────
# Evaluation Admin
# ──────────────────────────────────────────

@admin.register(Evaluation)
class EvaluationAdmin(VersionAdmin):

    list_display    = ['project', 'guide_name', 'guide_rating', 'guide_submitted',
                       'approval_badge', 'publication_badge', 'created_at']
    list_filter     = ['coordinator_approval', 'publication_status']
    search_fields   = ['project__title', 'project__guide__username']
    readonly_fields = ['guide_submitted_at', 'coordinator_approved_at',
                       'created_at', 'updated_at']

    fieldsets = [
        ('Project',            {'fields': ['project']}),
        ('Guide Evaluation',   {'fields': ['guide_rating', 'guide_comments', 'guide_submitted_at']}),
        ('Coordinator',        {'fields': ['coordinator_approval', 'coordinator_comments',
                                           'coordinator_approved_at']}),
        ('Publication',        {'fields': ['publication_status', 'certificate_copy']}),
        ('Timestamps',         {'fields': ['created_at', 'updated_at'], 'classes': ['collapse']}),
    ]

    def guide_name(self, obj):
        if obj.project.guide:
            return obj.project.guide.get_full_name() or obj.project.guide.username
        return '-'
    guide_name.short_description = 'Guide'

    def guide_submitted(self, obj):
        if obj.guide_submitted_at:
            return format_html(
                '<span style="color:#2ecc71">&#10003; {}</span>',
                obj.guide_submitted_at.strftime('%d %b %Y')
            )
        return format_html('<span style="color:#e74c3c">Pending</span>')
    guide_submitted.short_description = 'Guide Submitted'

    def approval_badge(self, obj):
        color = {'pending': '#f39c12', 'approved': '#2ecc71',
                 'rejected': '#e74c3c'}.get(obj.coordinator_approval, '#ccc')
        return format_html(
            '<span style="background:{};color:white;padding:2px 10px;'
            'border-radius:10px;font-size:11px">{}</span>',
            color, obj.get_coordinator_approval_display()
        )
    approval_badge.short_description = 'Approval'

    def publication_badge(self, obj):
        color = {
            'not_submitted': '#bdc3c7', 'submitted': '#3498db',
            'accepted': '#2ecc71',      'rejected':  '#e74c3c',
        }.get(obj.publication_status, '#ccc')
        return format_html(
            '<span style="background:{};color:white;padding:2px 10px;'
            'border-radius:10px;font-size:11px">{}</span>',
            color, obj.get_publication_status_display()
        )
    publication_badge.short_description = 'Publication'

    @admin.action(description='Mark selected evaluations as approved')
    def bulk_approve(self, request, queryset):
        updated = queryset.update(coordinator_approval='approved')
        self.message_user(request, f'{updated} evaluation(s) approved.')

    @admin.action(description='Mark selected as accepted publication')
    def bulk_set_accepted(self, request, queryset):
        updated = queryset.update(publication_status='accepted')
        self.message_user(request, f'{updated} project(s) marked accepted.')

    actions = ['bulk_approve', 'bulk_set_accepted']


# ──────────────────────────────────────────
# Notification Admin
# ──────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display    = ['recipient', 'short_message', 'is_read', 'created_at']
    list_filter     = ['is_read', 'recipient']
    readonly_fields = ['recipient', 'message', 'created_at']

    @admin.action(description='Mark selected notifications as read')
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notification(s) marked as read.')

    actions = ['mark_read']

    def short_message(self, obj):
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
    short_message.short_description = 'Message'
