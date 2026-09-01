# Distance Education ERP

A full-featured **Distance Education ERP** built with Django for managing student admissions, enquiries, documents, fees, and reports.

## Features

### Student Management
- Student registration with photo upload
- Student profile with personal, contact, and course details
- Status tracking (Prospect → Applicant → Active → Completed)

### Enquiry Management
- Create and track enquiries
- Auto-fill student details from existing records
- Follow-up scheduling
- Convert enquiries to admissions

### Admission Management
- Admission creation from enquiries
- Status workflow (Application → Documents Pending → Verified → Fee Pending → Active)
- University and course assignment
- Academic session management

### Document Management
- Upload and verify student documents
- Document types: Aadhaar, 10th/12th Certificate, Degree, TC, Migration, etc.
- Verify/Reject with reasons

### Fee Management
- Payment tracking with multiple modes (Cash, UPI, Bank Transfer, Card)
- Auto-generated PDF receipts
- Balance calculation
- Void payment support

### Reports
- Admission reports
- Enquiry reports
- Fee collection reports

### Public Pages
- Landing page with course listing
- Student registration form
- About, Services, Success Stories, Partner Universities, Privacy Policy

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 6.1 |
| Database | PostgreSQL |
| Frontend | Bootstrap 5.3 |
| Charts | Chart.js |
| PDF | ReportLab |
| Icons | Bootstrap Icons |

## Installation

```bash
# Clone the repository
git clone https://github.com/kavipriyaraj-code/distance-erp.git
cd distance-erp

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install django psycopg2-binary reportlab Pillow

# Setup database
# Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE distance_erp;"

# Run migrations
python manage.py migrate

# Seed data
python manage.py seed_sessions
python manage.py seed_document_types

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

## Default Login

| Role | Username | Password |
|------|----------|----------|
| Super Admin | admin | Admin@123 |

## Project Structure

```
distance_erp/
├── accounts/        # User management & authentication
├── admissions/      # Admission CRUD & workflow
├── core/            # Dashboard, settings, public pages
├── courses/         # Course management
├── documents/       # Document upload & verification
├── enquiries/       # Enquiry & follow-up management
├── fees/            # Payment & receipt management
├── reports/         # Reporting module
├── students/        # Student registration & profiles
├── universities/    # University management
├── templates/       # HTML templates
└── static/          # Static files (CSS, JS)
```

## Testing

```bash
python manage.py test
```

82 test cases covering models, views, APIs, and authentication.

