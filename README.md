# Distance Education ERP

A full-featured **Distance Education ERP** built with Django for RENIC TECH — managing student admissions, enquiries, documents, fees, finance, staff attendance, and reports with role-based access control.

## Live Demo

🔗 **https://web-production-565a4.up.railway.app**

## Features

### Role-Based Access Control
- **Admin** — Full access to all modules
- **Counsellor** — Students, Enquiries, Admissions, Documents, Attendance
- **Accountant** — Fees, Finance, Payments, Reports, Attendance

### Student Management
- Student registration with mandatory fields (Aadhaar, mobile, email, etc.)
- Student profile with personal, contact, and course details
- Status tracking (Prospect → Applicant → Active → Completed)
- Auto-generated Student ID

### Enquiry Management
- Create and track enquiries with mandatory fields
- Follow-up scheduling with date tracking
- Convert enquiries to admissions
- Status workflow (New → Follow-up → Converted/Lost)

### Admission Management
- Admission creation from enquiries or directly
- Status workflow (Application → Documents Pending → Verified → Fee Pending → Active)
- University and course assignment with dynamic course loading
- Incentive amount tracking for counsellors
- Academic session management

### Document Management
- Overview page showing all students as cards
- Per-admission document management
- Document types: Aadhaar, 10th/12th Certificate, Degree, TC, Migration, etc.
- Verify/Reject with reasons
- Document type seeding via management command

### Fee & Payment Management
- Semester-based fee structure with due dates
- Payment tracking with multiple modes (Cash, UPI, Bank Transfer, Card)
- Auto-allocation of payments to semesters
- Auto-generated PDF receipts
- Balance calculation and payment links
- Share Payment page (Razorpay/PhonePe integration)
- Student semester detail view with payment history

### Finance & Day Cash Flow
- Finance Dashboard with KPIs
- Day Book with daily transaction tracking
- Expense management with categories
- Cash & Bank balance tracking
- Day Closing with reconciliation
- Reopen Day support (Admin only)
- University Accounts with payable/receivable tracking
- Refund management
- Payables & Receivables
- Finance Reports (Cash Flow, Budget vs Actual, Trial Balance, P&L, Balance Sheet)
- Bank Reconciliation
- Gateway Settlements (Razorpay/PhonePe)
- GST Report
- Finance Audit Log
- Finance Notifications
- Bank Statement Import
- Branches & Cost Centres (Admin only)
- Finance Settings (Bank/UPI details, payment gateway config)

### Staff Attendance Management
- Admin attendance management page with filters
- Staff Check In / Out (self-service)
- Attendance history with month/year filters
- Monthly attendance report (Admin)
- Attendance-based salary calculation
- Configurable settings (working days, half-day, unpaid leave)

### Staff Salary Management
- Salary records per staff member
- Salary templates
- Auto-calculate from attendance
- Bank details integration
- PDF salary slips

### Staff Bank Details
- Bank account details per staff member
- Account holder name, bank name, account number, IFSC, UPI, PAN

### Dashboard
- **Admin Dashboard** — Students, Admissions, Universities, Fee Due Dates KPIs, Finance overview, University overview
- **Counsellor Dashboard** — Enquiries, Follow-ups, Admissions, Check In/Out
- **Accountant Dashboard** — Fees, Payments, Finance summary, Check In/Out
- Report period filtering (Today, This Week, This Month, Custom Range)
- Due dates showing overdue and upcoming semesters with time remaining

### Collapsible Sidebar Navigation
- Accordion-style collapsible sections
- Role-based menu visibility
- Active page auto-expansion
- Sections: Academics, Setup, Fees, Finance, Finance Reports, Finance Tools, Staff, Attendance, Administration, Reports

### Reports
- Admission Reports with university/course breakdown
- Payment Reports
- Export Students to CSV
- University-wise admission detail
- Finance Reports (Cash Flow, Budget vs Actual, Trial Balance, P&L, Balance Sheet)

### Public Pages
- Landing page with hero section
- About, Services, Success Stories
- Partner Universities
- Privacy Policy
- Public Admission Form

### License System
- License key management
- Expiry tracking with middleware
- Renewal and payment pages
- License expired enforcement

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 6.1 |
| Database | PostgreSQL 18 |
| Frontend | Bootstrap 5.3 |
| Charts | Chart.js 4.4 |
| PDF | ReportLab |
| Icons | Bootstrap Icons 1.11 |
| Font | Inter (Google Fonts) |
| CSS | Custom Design System |
| Payment | Razorpay, PhonePe |
| Email | Resend API |
| Hosting | Railway |

## Installation

```bash
# Clone the repository
git clone https://github.com/kavipriyaraj-code/distance_erp.git
cd distance_erp

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install django psycopg2-binary reportlab Pillow

# Setup database
psql -U postgres -c "CREATE DATABASE distance_erp;"

# Run migrations
python manage.py migrate

# Seed data
python manage.py seed_sessions
python manage.py seed_document_types
python manage.py seed_semesters

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

## Default Login

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | Admin@123 |
| Counsellor | counsellor1 | Counsellor@123 |
| Accountant | accountant1 | Accountant@123 |

## Environment Variables (Railway)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Debug mode (True/False) |
| `ALLOWED_HOSTS` | Allowed hosts |
| `CSRF_TRUSTED_ORIGINS` | CSRF trusted origins |
| `DATABASE_URL` | PostgreSQL connection string |
| `RESEND_API_KEY` | Resend email API key |
| `DEFAULT_FROM_EMAIL` | Default email sender |

## Project Structure

```
distance_erp/
├── accounts/           # User management, authentication, bank details
├── admissions/         # Admission CRUD & workflow, incentive
├── attendance/         # Staff attendance management
├── core/               # Dashboard, settings, public pages, middleware
├── courses/            # Course management
├── documents/          # Document upload & verification
├── enquiries/          # Enquiry & follow-up management
├── fees/               # Semester fees, payment & receipt management
├── finance/            # Day cash flow, expenses, bank, reports, settlements
├── reports/            # Admission, payment, export reports
├── students/           # Student registration & profiles
├── universities/       # University management
├── templates/          # HTML templates (35+ pages)
├── static/             # CSS design system, static files
└── media/              # User uploads
```

## Management Commands

```bash
python manage.py seed_sessions        # Seed academic sessions
python manage.py seed_document_types  # Seed document types
python manage.py seed_semesters       # Seed semester fee structure
python manage.py fix_semesters        # Fix semester data
```

## License

Proprietary - RENIC TECH
