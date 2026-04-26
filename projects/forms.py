from django import forms
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User

from .models import Project, Milestone, MilestoneVersion, Evaluation


# ──────────────────────────────────────────
# ProjectForm
# Used on the Register Project page.
# Guide is NOT included here — guide is
# allotted separately by admin.
# ──────────────────────────────────────────

class ProjectForm(forms.ModelForm):

    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_staff=False),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size':  '6',
        }),
        required=False,
        help_text='Hold Cmd (Mac) or Ctrl (Windows) to select multiple students.'
    )

    class Meta:
        model  = Project
        # guide excluded — allotted by admin after registration
        fields = ['title', 'domain', 'description', 'members']
        widgets = {
            'title': forms.TextInput(attrs={
                'class':        'form-control',
                'placeholder':  'Enter a unique project title',
                'id':           'id_title',
                'autocomplete': 'off',
            }),
            'domain': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class':       'form-control',
                'rows':        3,
                'placeholder': 'Brief description of the project (optional)',
            }),
        }

    def clean_title(self):
        """
        Case-insensitive uniqueness check.
        Excludes current instance when editing.
        """
        title = self.cleaned_data.get('title', '').strip()
        qs    = Project.objects.filter(title__iexact=title)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                f'A project titled "{title}" already exists. '
                'Please choose a different title.'
            )
        return title


# ──────────────────────────────────────────
# GuideAllotmentForm
# Used on the admin allotment page.
# Shows dropdown of faculty (is_staff=True)
# and updates the project's guide FK.
# ──────────────────────────────────────────

class GuideAllotmentForm(forms.ModelForm):

    guide = forms.ModelChoiceField(
        # faculty = staff users who are not superusers
        queryset=User.objects.filter(is_staff=True, is_superuser=False),
        empty_label='— Select a guide —',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Select a faculty member to assign as guide for this project.'
    )

    class Meta:
        model  = Project
        fields = ['guide']

    def clean_guide(self):
        guide = self.cleaned_data.get('guide')
        if not guide:
            raise forms.ValidationError('Please select a guide.')
        return guide


# ──────────────────────────────────────────
# MilestoneUploadForm
# File upload per stage.
# Validates extension and size.
# ──────────────────────────────────────────

class MilestoneUploadForm(forms.ModelForm):

    file = forms.FileField(
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'zip'],
                message='Only PDF, DOC, DOCX, and ZIP files are allowed.'
            )
        ],
        widget=forms.ClearableFileInput(attrs={
            'class':  'form-control',
            'accept': '.pdf,.doc,.docx,.zip',
        }),
        help_text='Accepted: PDF, DOC, DOCX, ZIP. Max size: 50 MB.'
    )

    class Meta:
        model  = MilestoneVersion
        fields = ['file']

    def clean_file(self):
        file     = self.cleaned_data.get('file')
        max_size = 50 * 1024 * 1024   # 50 MB
        if file and file.size > max_size:
            raise forms.ValidationError(
                f'File size is {file.size // (1024*1024)} MB. '
                'Maximum allowed is 50 MB.'
            )
        return file


# ──────────────────────────────────────────
# EvaluationForm
# Filled by guide after reviewing uploads.
# Only guide fields are shown here —
# coordinator fields are on a separate form.
# ──────────────────────────────────────────

class EvaluationForm(forms.ModelForm):

    guide_rating = forms.ChoiceField(
        choices=Evaluation.RATING_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Rate the project out of 10.'
    )

    guide_comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'class':       'form-control',
            'rows':        4,
            'placeholder': 'Enter your observations, feedback, and recommendations...',
        }),
        help_text='Provide detailed feedback on the project.'
    )

    class Meta:
        model  = Evaluation
        fields = ['guide_rating', 'guide_comments']

    def clean_guide_rating(self):
        rating = self.cleaned_data.get('guide_rating')
        if not rating:
            raise forms.ValidationError('Please select a rating.')
        return int(rating)


# ──────────────────────────────────────────
# CoordinatorApprovalForm
# Filled by coordinator after guide submits.
# Sets approval status, publication status,
# and optionally uploads certificate.
# ──────────────────────────────────────────

class CoordinatorApprovalForm(forms.ModelForm):

    coordinator_approval = forms.ChoiceField(
        choices=Evaluation.COORDINATOR_APPROVAL_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Set your approval decision.'
    )

    coordinator_comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class':       'form-control',
            'rows':        3,
            'placeholder': 'Optional comments for the guide and team...',
        })
    )

    publication_status = forms.ChoiceField(
        choices=Evaluation.PUBLICATION_STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Set the current publication status of the project.'
    )

    certificate_copy = forms.FileField(
        required=False,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'],
                message='Certificate must be PDF or image (JPG, PNG).'
            )
        ],
        widget=forms.ClearableFileInput(attrs={
            'class':  'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png',
        }),
        help_text='Upload scanned certificate copy if available (PDF/image).'
    )

    class Meta:
        model  = Evaluation
        fields = [
            'coordinator_approval',
            'coordinator_comments',
            'publication_status',
            'certificate_copy',
        ]

    def clean_certificate_copy(self):
        cert     = self.cleaned_data.get('certificate_copy')
        max_size = 10 * 1024 * 1024   # 10 MB for certificate
        if cert and cert.size > max_size:
            raise forms.ValidationError(
                f'Certificate file is too large. Maximum allowed is 10 MB.'
            )
        return cert


# ──────────────────────────────────────────
# CSVExportForm
# Filter params for the export view.
# All fields optional — blank = export all.
# ──────────────────────────────────────────

class CSVExportForm(forms.Form):

    guide = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True, is_superuser=False),
        required=False,
        empty_label='— All guides —',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    domain = forms.ChoiceField(
        choices=[('', '— All domains —')] + Project.DOMAIN_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # new filter — publication status from Evaluation model
    publication_status = forms.ChoiceField(
        choices=[('', '— All statuses —')] + Evaluation.PUBLICATION_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
