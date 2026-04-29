# ProjectArc — Student Project & Milestone Tracker

> A centralized Django web application for managing senior-year capstone
> projects across their full lifecycle — from registration through milestone
> uploads, guide evaluation, coordinator approval, and publication tracking.

---

## 🔗 Live URL

```
[To be updated after deployment]
```

---

## 👥 Team Details

| Field         | Details                        |
|---------------|--------------------------------|
| Team Name     | _(your team name)_             |
| Institution   | _(your college / university)_  |
| Department    | _(your department)_            |
| Semester      | _(e.g. VI Semester)_           |
| Academic Year | _(e.g. 2024–25)_               |
| Subject       | Full Stack Development         |
| Subject Code  | _(your subject code)_          |

### Team Members

| Name | USN / Roll No | Role |
|------|---------------|------|
| _(Member 1 name)_ | _(USN)_ | Developer |
| _(Member 2 name)_ | _(USN)_ | Developer |
| _(Member 3 name)_ | _(USN)_ | Developer |
| _(Member 4 name)_ | _(USN)_ | Developer |

### Faculty Guide

| Name | Designation | Department |
|------|-------------|------------|
| _(Guide name)_ | _(e.g. Assistant Professor)_ | _(Department)_ |

---

## 🎯 Theme

**Theme 2 — Student Project & Milestone Tracker**

### System Objective

Orchestrate a centralized repository and milestone tracking framework for
senior-year capstone projects, enabling multi-role collaboration and version
control across five defined stages — Synopsis, Phase 1, Phase 2, Final Report,
and Publication Details.

### Key Features Implemented

| Feature | Description |
|---------|-------------|
| Project Registration | Title uniqueness check (server-side + AJAX real-time) |
| Guide Allotment | Coordinator assigns faculty via dropdown |
| Milestone Uploads | 5-stage file upload with versioning (PDF/DOC/ZIP ≤ 50MB) |
| Evaluation Workflow | Guide rating → Coordinator approval → Publication status |
| Certificate Upload | Coordinator uploads acceptance certificate |
| CSV Export | Filtered by guide / domain / publication status |
| README Export | Auto-generated with live DB stats and CO-SDG table |
| Email Notifications | Gmail SMTP — guide evaluation, milestone approve/reject |
| AJAX Title Search | Real-time duplicate detection via jQuery |
| Version History | Every upload preserved — files never overwritten |
| Role-aware Dashboards | Student / Guide / Coordinator views |
| Progress Visualization | Chart.js horizontal bar chart for coordinators |

### Technology Stack

| Layer | Technology |
|-------|------------|
| Framework | Django 5.x (MVT Architecture) |
| Database | SQLite (development) |
| ORM | Django ORM — FK, M2M, OneToOne relations |
| Frontend | Bootstrap 5, jQuery, Chart.js |
| Versioning | django-reversion |
| Email | Gmail SMTP via Django send_mail |
| File Storage | Django FileField (media/) |
| Authentication | Django built-in auth |

---

## 📚 CO–SDG Mapping

| Course Outcome | How This Project Demonstrates It | SDG Target Addressed |
|----------------|----------------------------------|----------------------|
| **CO1** — MVT Architecture | URL routing across 18 named endpoints covering dashboard, project CRUD, milestone upload, guide allotment, evaluation, export, and AJAX APIs. Loose coupling maintained across 5 logical components — models, views, forms, signals, admin. | **SDG 4.4** — Increase the number of youth and adults who have relevant skills for employment and entrepreneurship |
| **CO2** — Models & Forms | Five ORM models (Project, Milestone, MilestoneVersion, Evaluation, Notification) with FK, M2M, and OneToOne relations. Forms include FileExtensionValidator, 50MB size check, case-insensitive title uniqueness, and sequential approval logic. | **SDG 9.5** — Enhance scientific research and upgrade the technological capabilities of industrial sectors |
| **CO3** — Template Inheritance | All 14 templates extend base.html via {% block content %}. Navbar, flash messages, and notification bell are defined once and inherited everywhere. Role-aware rendering via {% if user.is_superuser %} and {% if user.is_staff %} guards. | **SDG 4.5** — Eliminate gender disparities and ensure equal access to all levels of education |
| **CO4** — Non-HTML Output | CSV export using HttpResponse(content_type='text/csv') filtered by guide, domain, and publication status. README.md export using text/markdown MIME type. Django Signals (post_save on Evaluation) send Gmail SMTP emails on evaluation submission, milestone approval, and rejection. | **SDG 16.6** — Develop effective, accountable, and transparent institutions at all levels |
| **CO5** — AJAX Integration | Real-time title duplicate detection via jQuery .keyup() with 400ms debounce calling /api/title-check/ and rendering JsonResponse inline. Notification bell count updated every 30 seconds via $.get() without page reload. CSRF token injected on all state-changing AJAX requests. | **SDG 9.5** — Promote inclusive and sustainable industrialization and foster innovation |

---

## ✍️ SDG Justification (150 words)

Our Student Project and Milestone Tracker, ProjectArc, advances **SDG 4:
Quality Education** (Target 4.4) by digitizing capstone project management,
enabling students to develop industry-aligned software engineering skills
through a structured five-stage milestone workflow. The role-aware dashboard
system (CO3) ensures equitable access for students, guides, and coordinators
regardless of technical background, directly addressing SDG 4.5.

The CSV and README export features (CO4) support **SDG 16** (Target 16.6) by
providing transparent, filterable institutional reports that enable effective
academic oversight. Django Signals automate email notifications via Gmail SMTP,
embedding responsive communication into the academic process without manual
intervention.

Built on Django's MVT architecture (CO1) with validated ORM models (CO2),
the system enforces academic integrity through file versioning — every
submission is preserved, never overwritten. The AJAX title search (CO5)
prevents duplicate research efforts across teams, directly supporting
**SDG 9.5** by fostering an innovation-aware, collaborative research
infrastructure aligned with modern full-stack web development standards.

---

## ✅ Verification Checklist

- [x] App loads at `http://127.0.0.1:8000`
- [x] Register project with unique title → saves to DB
- [x] Duplicate title → shows error, no DB save
- [x] AJAX title search fires on keyup with debounce
- [x] Guide allotment via coordinator dropdown
- [x] Milestone upload with file type and size validation
- [x] Stage gate — cannot upload Phase N until Phase N-1 approved
- [x] Marks required before guide can approve
- [x] Rejection modal requires reason — visible to student
- [x] Version history preserves all uploads (never overwritten)
- [x] Guide submits evaluation → coordinator notified by email
- [x] Coordinator approves + sets publication status + uploads certificate
- [x] Email sent to students on approve and reject
- [x] Bell badge updates via AJAX polling
- [x] `/export/?domain=AI` → downloads valid CSV
- [x] README.md export with live DB stats
- [x] Marks summary with per-stage breakdown on project detail
- [x] Project edit page with locked editing after approval
- [x] Admin panel — inlines, badges, bulk actions, reversion history
- [x] Mobile view — forms and dashboard usable on phone screen
- [x] README.md contains CO-SDG table + 150-word justification

---

## 📁 Project Structure

```
projectarc/
├── projects/
│   ├── models.py        # Project, Milestone, MilestoneVersion, Evaluation
│   ├── forms.py         # ProjectForm, GuideAllotmentForm, EvaluationForm,
│   │                    # CoordinatorApprovalForm, CSVExportForm
│   ├── views.py         # 20+ views — dashboard, CRUD, upload, export, AJAX
│   ├── urls.py          # 18 named URL patterns
│   ├── signals.py       # post_save on Evaluation + Notification model
│   └── admin.py         # Customized admin with inlines, badges, bulk actions
├── templates/
│   ├── base.html                        # Bootstrap layout, navbar, bell
│   ├── registration/login.html          # Login page
│   ├── projects/
│   │   ├── dashboard.html               # Role-aware dashboard
│   │   ├── project_list.html            # Browse + search
│   │   ├── project_detail.html          # Milestones + marks + evaluation
│   │   ├── project_form.html            # Register with member picker
│   │   ├── project_edit.html            # Edit with pre-loaded members
│   │   ├── admin_allotment.html         # Guide allotment list
│   │   ├── allot_guide_form.html        # Assign guide form
│   │   ├── guide_evaluation.html        # Guide evaluation form
│   │   └── coordinator_approval.html    # Coordinator approval form
│   ├── milestones/
│   │   ├── upload.html                  # File upload with drag-drop
│   │   └── history.html                 # Version history
│   ├── exports/
│   │   └── confirm.html                 # CSV + README export page
│   └── notifications/
│       └── list.html                    # Coordinator notifications
├── static/
│   └── js/
│       └── ajax_search.js               # Real-time title duplicate checker
├── media/                               # Uploaded files (gitignored)
├── manage.py
├── requirements.txt
└── README.md
```

---

## 📦 Requirements

```
django>=4.2
django-reversion>=5.0
```

Install with:

```bash
pip install -r requirements.txt
```

---

## 🚀 Local Setup

```bash
# Clone the repository
git clone <repo-url>
cd projectarc

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (coordinator)
python manage.py createsuperuser

# Start server
python manage.py runserver
```

Visit `http://127.0.0.1:8000`

---

## 🔐 User Roles

| Role | Django Flag | Access |
|------|-------------|--------|
| Student | `is_staff=False` | Own projects only — upload, view history |
| Guide | `is_staff=True` | Assigned projects — approve, reject, evaluate |
| Coordinator | `is_superuser=True` | All projects — allot guides, approve evaluations, export |

---

*ProjectArc — Built with Django · Bootstrap 5 · jQuery · Chart.js*