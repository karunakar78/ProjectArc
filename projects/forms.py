from django import forms
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User

from .models import Project, Milestone, MilestoneVersion


# ──────────────────────────────────────────
# ProjectForm
# Used on the "Register Project" page.
# Handles title, domain, description,
# guide selection, and team members.
# ──────────────────────────────────────────

class ProjectForm(forms.ModelForm):

    # guide dropdown — only show users who are staff (faculty)
    guide = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True),
        empty_label='— Select a guide —',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    # members multi-select — only non-staff users (students)
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_staff=False),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        help_text='Select all students in your team.'
    )

    class Meta:
        model  = Project
        fields = ['title', 'domain', 'description', 'guide', 'members']
        widgets = {
            'title': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Enter a unique project title',
                # data attribute used by our AJAX title checker
                'id':          'id_title',
                'autocomplete':'off',
            }),
            'domain': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows':  3,
                'placeholder': 'Brief description of the project (optional)',
            }),
        }

    def clean_title(self):
        """
        Server-side uniqueness check.
        Case-insensitive — 'Smart Dustbin' and 'smart dustbin'
        are treated as duplicates.
        """
        title = self.cleaned_data.get('title', '').strip()

        # when editing an existing project, exclude the current one
        qs = Project.objects.filter(title__iexact=title)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                f'A project titled "{title}" already exists. '
                'Please choose a different title.'
            )
        return title


# ──────────────────────────────────────────
# MilestoneUploadForm
# Used on the upload page for each stage.
# Validates file type and size before save.
# ──────────────────────────────────────────

class MilestoneUploadForm(forms.ModelForm):

    # allowed extensions per the SRS
    file = forms.FileField(
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'zip'],
                message='Only PDF, DOC, DOCX, and ZIP files are allowed.'
            )
        ],
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.zip',
        }),
        help_text='Accepted formats: PDF, DOC, DOCX, ZIP. Maximum size: 50 MB.'
    )

    class Meta:
        model  = MilestoneVersion
        # stage is set by the URL, not the form
        # version_number is calculated in the view
        fields = ['file']

    def clean_file(self):
        """
        Enforce the 50 MB file size limit at the form level.
        Settings enforces it at the server level — this gives
        a clean user-facing error message instead of a crash.
        """
        file = self.cleaned_data.get('file')

        if file:
            max_size = 50 * 1024 * 1024   # 50 MB in bytes
            if file.size > max_size:
                raise forms.ValidationError(
                    f'File size is {file.size // (1024*1024)} MB. '
                    'Maximum allowed is 50 MB.'
                )
        return file


# ──────────────────────────────────────────
# CSVExportForm
# Simple filter form on the export page.
# Guide and domain are both optional —
# leaving both blank exports everything.
# ──────────────────────────────────────────

class CSVExportForm(forms.Form):

    guide = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True),
        required=False,
        empty_label='— All guides —',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    domain = forms.ChoiceField(
        choices=[('', '— All domains —')] + Project.DOMAIN_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )