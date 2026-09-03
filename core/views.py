from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import date, timedelta
from admissions.models import Admission
from enquiries.models import Enquiry
from fees.models import Payment
from students.models import Student
from documents.models import StudentDocument
from universities.models import University
from courses.models import Course


def home_view(request):
    context = {}
    context['universities'] = University.objects.filter(is_active=True)
    from itertools import groupby
    from operator import attrgetter
    all_courses = Course.objects.filter(is_active=True).select_related('university').order_by('category')
    context['courses_by_category'] = [
        (cat, list(courses_iter)) for cat, courses_iter in groupby(all_courses, key=attrgetter('category'))
    ]
    if request.user.is_authenticated:
        context['total_students'] = Student.objects.count()
        context['total_admissions'] = Admission.objects.count()
        context['total_universities'] = University.objects.count()
        context['total_courses'] = Course.objects.count()
    return render(request, 'landing.html', context)


@login_required
def dashboard_view(request):
    role = request.user.role

    if role == 'accountant':
        return _accountant_dashboard(request)
    elif role == 'counsellor':
        return _counsellor_dashboard(request)
    else:
        return _admin_dashboard(request)


def _admin_dashboard(request):
    # Date filtering
    period = request.GET.get('period', '').strip()
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    today = date.today()

    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
    elif period == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif period == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif period == 'last_month':
        first_this_month = today.replace(day=1)
        end_date = first_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif period == 'custom' and from_date and to_date:
        from datetime import datetime as dt
        start_date = dt.strptime(from_date, '%Y-%m-%d').date()
        end_date = dt.strptime(to_date, '%Y-%m-%d').date()
    else:
        start_date = None
        end_date = None

    q = request.GET.get('q', '').strip()
    search_results = []
    if q:
        search_results = Student.objects.filter(
            Q(mobile__icontains=q)
        )[:10]
    total_students = Student.objects.filter(enquiries__isnull=True).count()
    total_admissions = Admission.objects.all()
    if start_date and end_date:
        total_admissions = total_admissions.filter(admission_date__gte=start_date, admission_date__lte=end_date)
    total_admissions = total_admissions.count()
    active_admissions = Admission.objects.filter(status='active').count()
    total_enquiries = Enquiry.objects.exclude(student__admissions__isnull=False).count()
    new_enquiries = Enquiry.objects.filter(status='new').exclude(student__admissions__isnull=False).count()
    followups_today = Enquiry.objects.filter(next_followup=today).exclude(student__admissions__isnull=False).count()
    fees_qs = Admission.objects.all()
    if start_date and end_date:
        fees_qs = fees_qs.filter(admission_date__gte=start_date, admission_date__lte=end_date)
    total_fees = fees_qs.aggregate(t=Sum('total_fee'))['t'] or 0
    payments_qs = Payment.objects.filter(is_voided=False)
    if start_date and end_date:
        payments_qs = payments_qs.filter(payment_date__gte=start_date, payment_date__lte=end_date)
    total_paid = payments_qs.aggregate(t=Sum('amount'))['t'] or 0
    pending_fees = total_fees - total_paid
    today_admissions = Admission.objects.filter(admission_date=today).count()
    uni_stats = Admission.objects.values('university__name').annotate(count=Count('id')).order_by('-count')[:5]
    uni_labels = [s['university__name'] or 'Unknown' for s in uni_stats]
    uni_values = [s['count'] for s in uni_stats]
    course_stats = Admission.objects.values('course__name').annotate(count=Count('id')).order_by('-count')[:5]
    course_labels = [s['course__name'] or 'Unknown' for s in course_stats]
    course_values = [s['count'] for s in course_stats]
    counsellor_stats = Admission.objects.filter(counsellor__isnull=False).values('counsellor__first_name', 'counsellor__last_name', 'counsellor__username').annotate(count=Count('id')).order_by('-count')
    counsellor_labels = []
    counsellor_values = []
    for s in counsellor_stats:
        name = f"{s['counsellor__first_name']} {s['counsellor__last_name']}".strip()
        counsellor_labels.append(name or s['counsellor__username'])
        counsellor_values.append(s['count'])

    uni_overview = []
    for uni in University.objects.filter(is_active=True).order_by('name'):
        uni_admissions = Admission.objects.filter(university=uni)
        adm_count = uni_admissions.count()
        student_count = uni_admissions.values('student').distinct().count()
        fees = uni_admissions.aggregate(t=Sum('total_fee'))['t'] or 0
        collected = Payment.objects.filter(is_voided=False, admission__university=uni).aggregate(t=Sum('amount'))['t'] or 0
        uni_overview.append({
            'id': uni.id,
            'name': uni.name,
            'admissions': adm_count,
            'students': student_count,
            'fees': fees,
            'collected': collected,
            'pending': fees - collected,
        })
    pending_docs_count = Admission.objects.filter(status__in=['documents_pending', 'fee_pending']).count()
    pending_fee_admissions = Admission.objects.filter(status__in=['active', 'fee_pending']).count()
    overdue_followups = Enquiry.objects.filter(next_followup__lt=today).exclude(status__in=['converted', 'lost']).exclude(student__admissions__isnull=False).count()
    recent_enquiries = Enquiry.objects.filter(status='new').exclude(student__admissions__isnull=False).order_by('-created_at')[:5]
    recent_students = Student.objects.filter(enquiries__isnull=True).order_by('-created_at')[:5]
    total_universities = University.objects.count()
    total_courses = Course.objects.count()

    from fees.models import Semester
    from datetime import timedelta as td
    today_date = date.today()

    def format_days_remaining(due_date):
        delta = due_date - today_date
        days = delta.days
        if days == 0:
            return "Today"
        months = days // 30
        weeks = (days % 30) // 7
        rem_days = days % 7
        parts = []
        if months > 0:
            parts.append(f"{months} month{'s' if months > 1 else ''}")
        if weeks > 0:
            parts.append(f"{weeks} week{'s' if weeks > 1 else ''}")
        if rem_days > 0:
            parts.append(f"{rem_days} day{'s' if rem_days > 1 else ''}")
        return ' '.join(parts) if parts else f"{days} days"

    overdue_qs = Semester.objects.filter(due_date__lt=today_date, is_active=True).select_related('course').order_by('due_date')
    upcoming_qs = Semester.objects.filter(due_date__gte=today_date, due_date__lte=today_date + td(days=90), is_active=True).select_related('course').order_by('due_date')[:5]

    overdue_names = [f"{s.name} ({s.course.code})" for s in overdue_qs]
    upcoming_list = []
    for s in upcoming_qs:
        upcoming_list.append(f"{s.name} ({s.course.code}) - {format_days_remaining(s.due_date)}")

    from datetime import datetime
    import calendar
    monthly_data = []
    monthly_labels = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30)
        month_start = d.replace(day=1)
        if d.month == 12:
            month_end = d.replace(year=d.year+1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = d.replace(month=d.month+1, day=1) - timedelta(days=1)
        count = Admission.objects.filter(admission_date__gte=month_start, admission_date__lte=month_end).count()
        monthly_data.append(count)
        monthly_labels.append(calendar.month_abbr[d.month])

    enquiry_stats = Enquiry.objects.values('status').annotate(count=Count('id'))
    enquiry_status_labels = [s['status'] for s in enquiry_stats]
    enquiry_status_values = [s['count'] for s in enquiry_stats]

    student_stats = Student.objects.values('status').annotate(count=Count('id'))
    student_status_labels = [s['status'] for s in student_stats]
    student_status_values = [s['count'] for s in student_stats]

    fee_monthly_data = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=i*30)
        month_start = d.replace(day=1)
        if d.month == 12:
            month_end = d.replace(year=d.year+1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = d.replace(month=d.month+1, day=1) - timedelta(days=1)
        amount = Payment.objects.filter(is_voided=False, payment_date__gte=month_start, payment_date__lte=month_end).aggregate(t=Sum('amount'))['t'] or 0
        fee_monthly_data.append(float(amount))

    return render(request, 'dashboard.html', {
        'total_students': total_students,
        'total_admissions': total_admissions,
        'active_admissions': active_admissions,
        'total_enquiries': total_enquiries,
        'new_enquiries': new_enquiries,
        'followups_today': followups_today,
        'total_fees': total_fees,
        'total_paid': total_paid,
        'pending_fees': pending_fees,
        'today_admissions': today_admissions,
        'uni_labels': uni_labels,
        'uni_values': uni_values,
        'course_labels': course_labels,
        'course_values': course_values,
        'pending_docs_count': pending_docs_count,
        'overdue_followups': overdue_followups,
        'search_results': search_results,
        'q': q,
        'recent_enquiries': recent_enquiries,
        'recent_students': recent_students,
        'total_universities': total_universities,
        'total_courses': total_courses,
        'overdue_names': overdue_names,
        'upcoming_list': upcoming_list,
        'overdue_count': len(overdue_names),
        'upcoming_count': len(upcoming_list),
        'monthly_labels': monthly_labels,
        'monthly_data': monthly_data,
        'enquiry_status_labels': enquiry_status_labels,
        'enquiry_status_values': enquiry_status_values,
        'student_status_labels': student_status_labels,
        'student_status_values': student_status_values,
        'fee_monthly_data': fee_monthly_data,
        'counsellor_labels': counsellor_labels,
        'counsellor_values': counsellor_values,
        'uni_overview': uni_overview,
        'period': period,
        'from_date': from_date,
        'to_date': to_date,
    })


def _counsellor_dashboard(request):
    from attendance.models import StaffAttendance
    today_date = date.today()
    now_time = timezone.localtime().time() if hasattr(timezone, 'localtime') else None
    total_enquiries = Enquiry.objects.filter(assigned_to=request.user).exclude(student__admissions__isnull=False).count()
    new_enquiries = Enquiry.objects.filter(assigned_to=request.user, status='new').exclude(student__admissions__isnull=False).count()
    followups_today = Enquiry.objects.filter(assigned_to=request.user, next_followup=today_date).exclude(student__admissions__isnull=False).count()
    overdue_followups = Enquiry.objects.filter(assigned_to=request.user, next_followup__lt=today_date).exclude(status__in=['converted', 'lost']).exclude(student__admissions__isnull=False).count()
    total_admissions = Admission.objects.filter(counsellor=request.user).count()
    pending_admissions = Admission.objects.filter(counsellor=request.user).exclude(status__in=['active', 'cancelled']).count()
    converted = Enquiry.objects.filter(assigned_to=request.user, status='converted').count()
    recent_enquiries = Enquiry.objects.filter(assigned_to=request.user).exclude(student__admissions__isnull=False).order_by('-created_at')[:10]

    attendance, _ = StaffAttendance.objects.get_or_create(
        staff=request.user, date=today_date,
        defaults={'status': 'present'}
    )
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'checkin' and not attendance.check_in:
            attendance.check_in = timezone.localtime().time()
            attendance.status = 'present'
            attendance.save()
        elif action == 'checkout' and attendance.check_in and not attendance.check_out:
            attendance.check_out = timezone.localtime().time()
            attendance.save()
        return redirect('dashboard')

    return render(request, 'dashboard_counsellor.html', {
        'total_enquiries': total_enquiries,
        'new_enquiries': new_enquiries,
        'followups_today': followups_today,
        'overdue_followups': overdue_followups,
        'total_admissions': total_admissions,
        'pending_admissions': pending_admissions,
        'converted': converted,
        'recent_enquiries': recent_enquiries,
        'attendance': attendance,
        'today_date': today_date,
    })


def _accountant_dashboard(request):
    from attendance.models import StaffAttendance
    from django.db.models.functions import TruncMonth
    today_date = date.today()
    total_fees = Admission.objects.aggregate(t=Sum('total_fee'))['t'] or 0
    total_paid = Payment.objects.filter(is_voided=False).aggregate(t=Sum('amount'))['t'] or 0
    pending_fees = total_fees - total_paid
    today_collection = Payment.objects.filter(is_voided=False, payment_date=today_date).aggregate(t=Sum('amount'))['t'] or 0
    total_payments = Payment.objects.filter(is_voided=False).count()
    pending_students = sum(1 for a in Admission.objects.select_related('student').all() if a.balance_amount > 0)
    recent_payments = Payment.objects.filter(is_voided=False).select_related('admission__student', 'admission__university')[:10]

    monthly_data = (
        Payment.objects.filter(is_voided=False)
        .annotate(month=TruncMonth('payment_date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    chart_months = [item['month'].strftime('%b %Y') for item in monthly_data]
    chart_amounts = [float(item['total']) for item in monthly_data]

    mode_data = (
        Payment.objects.filter(is_voided=False)
        .values('payment_mode')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    chart_modes = [item['payment_mode'].upper() for item in mode_data]
    chart_mode_amounts = [float(item['total']) for item in mode_data]

    uni_data = (
        Payment.objects.filter(is_voided=False)
        .values('admission__university__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    chart_unis = [item['admission__university__name'] for item in uni_data]
    chart_uni_amounts = [float(item['total']) for item in uni_data]

    attendance, _ = StaffAttendance.objects.get_or_create(
        staff=request.user, date=today_date,
        defaults={'status': 'present'}
    )
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'checkin' and not attendance.check_in:
            attendance.check_in = timezone.localtime().time()
            attendance.status = 'present'
            attendance.save()
        elif action == 'checkout' and attendance.check_in and not attendance.check_out:
            attendance.check_out = timezone.localtime().time()
            attendance.save()
        return redirect('dashboard')

    return render(request, 'dashboard_accountant.html', {
        'total_fees': total_fees,
        'total_paid': total_paid,
        'pending_fees': pending_fees,
        'pending_students': pending_students,
        'today_collection': today_collection,
        'total_payments': total_payments,
        'recent_payments': recent_payments,
        'chart_months': chart_months,
        'chart_amounts': chart_amounts,
        'chart_modes': chart_modes,
        'chart_mode_amounts': chart_mode_amounts,
        'chart_unis': chart_unis,
        'chart_uni_amounts': chart_uni_amounts,
        'attendance': attendance,
        'today_date': today_date,
    })
