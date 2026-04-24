from django.contrib import admin
from django.utils.html import format_html

import reversion
from reversion.admin import VersionAdmin

from .models import Project, Milestone, MilestoneVersion
from .signals import Notification


# ──────────────────────────────────────────
# MilestoneVersion inline
# Shows all uploaded file versions inside
# the Milestone admin page — read only.
# ──────────────────────────────────────────

class MilestoneVersionInline(admin.TabularInline):
    model           = MilestoneVersion
    extra           = 0          # don't show empty extra rows
    readonly_fields = [
        'version_number',
        'file',
        'uploaded_by',
        'uploaded_at',
        'file_link',
    ]
    # prevent adding versions from admin — uploads go through the app
    can_delete      = False

    def file_link(self, obj):
        """Renders a clickable download link in the admin."""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Download v{}</a>',
                obj.file.url,
                obj.version_number
            )
        return '—'
    file_link.short_description = 'Download'


# ──────────────────────────────────────────
# Milestone inline
# Shows all milestones inside the Project
# admin page so you can manage both in
# one screen.
# ──────────────────────────────────────────

class MilestoneInline(admin.TabularInline):
    model           = Milestone
    extra           = 0
    readonly_fields = ['submitted_by', 'submitted_at']

    # guide can update status and marks inline
    fields = [
        'stage',
        'status',
        'marks',
        'submitted_by',
        'submitted_at',
    ]


# ──────────────────────────────────────────
# Project Admin
# VersionAdmin from reversion gives us a
# "History" button showing all past versions.
# ──────────────────────────────────────────

@admin.register(Project)
class ProjectAdmin(VersionAdmin):

    # columns shown in the project list page
    list_display = [
        'title',
        'domain',
        'guide_name',
        'member_count',
        'completion',
        'created_at',
    ]

    # filter sidebar on the right
    list_filter = [
        'domain',
        'guide',
        'created_at',
    ]

    # search bar at the top
    search_fields = [
        'title',
        'members__username',
        'members__first_name',
        'guide__username',
    ]

    # show milestone rows inside the project page
    inlines = [MilestoneInline]

    # these fields are set automatically — don't let admin change them
    readonly_fields = ['created_at', 'updated_at']

    # layout of the project edit form
    fieldsets = [
        ('Project Info', {
            'fields': ['title', 'domain', 'description']
        }),
        ('Team', {
            'fields': ['guide', 'members']
        }),
        ('Timestamps', {
            'fields':  ['created_at', 'updated_at'],
            'classes': ['collapse'],   # collapsed by default
        }),
    ]

    # ── custom column methods ──────────────

    def guide_name(self, obj):
        if obj.guide:
            return obj.guide.get_full_name() or obj.guide.username
        return '—'
    guide_name.short_description = 'Guide'

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Team size'

    def completion(self, obj):
        """
        Shows a coloured progress bar in the admin list.
        Green ≥ 80%, amber ≥ 40%, red below that.
        """
        pct = obj.completion_percent()
        if pct >= 80:
            color = '#2ecc71'   # green
        elif pct >= 40:
            color = '#f39c12'   # amber
        else:
            color = '#e74c3c'   # red

        return format_html(
            '<div style="width:100px;background:#eee;border-radius:4px">'
            '<div style="width:{}%;background:{};height:12px;'
            'border-radius:4px;text-align:center;font-size:10px;'
            'color:white;line-height:12px">{}</div></div>{}%',
            pct, color, f'{pct}%', pct
        )
    completion.short_description = 'Progress'


# ──────────────────────────────────────────
# Milestone Admin
# Full control over stage status and marks.
# Bulk approve / reject via admin actions.
# ──────────────────────────────────────────

@admin.register(Milestone)
class MilestoneAdmin(VersionAdmin):

    list_display = [
        'project',
        'stage',
        'status_badge',
        'marks',
        'submitted_by',
        'submitted_at',
    ]

    list_filter  = ['stage', 'status']

    search_fields = [
        'project__title',
        'submitted_by__username',
    ]

    readonly_fields = ['submitted_by', 'submitted_at']

    # show file versions inside the milestone page
    inlines = [MilestoneVersionInline]

    # ── bulk actions ──────────────────────

    @admin.action(description='Approve selected milestones')
    def bulk_approve(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(
            request,
            f'{updated} milestone(s) approved successfully.'
        )

    @admin.action(description='Reject selected milestones')
    def bulk_reject(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(
            request,
            f'{updated} milestone(s) rejected.'
        )

    actions = ['bulk_approve', 'bulk_reject']

    # ── custom column methods ──────────────

    def status_badge(self, obj):
        """
        Renders a colour-coded status label
        instead of plain text in the list.
        """
        colors = {
            'pending':   '#95a5a6',
            'submitted': '#3498db',
            'approved':  '#2ecc71',
            'rejected':  '#e74c3c',
        }
        color = colors.get(obj.status, '#ccc')
        return format_html(
            '<span style="background:{};color:white;padding:2px 10px;'
            'border-radius:10px;font-size:11px">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ──────────────────────────────────────────
# Notification Admin
# Coordinators can see and clear
# notifications from admin.
# ──────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):

    list_display  = ['recipient', 'short_message', 'is_read', 'created_at']
    list_filter   = ['is_read', 'recipient']
    readonly_fields = ['recipient', 'message', 'created_at']

    @admin.action(description='Mark selected notifications as read')
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notification(s) marked as read.')

    actions = ['mark_read']

    def short_message(self, obj):
        """Truncate long messages in the list view."""
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
    short_message.short_description = 'Message'