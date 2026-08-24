from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
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
    today = date.today()
    q = request.GET.get('q', '').strip()
    search_results = []
    if q:
        search_results = Student.objects.filter(
            Q(mobile__icontains=q)
        )[:10]
    total_students = Student.objects.filter(enquiries__isnull=True).count()
    total_admissions = Admission.objects.count()
    active_admissions = Admission.objects.filter(status='active').count()
    total_enquiries = Enquiry.objects.exclude(student__admissions__isnull=False).count()
    new_enquiries = Enquiry.objects.filter(status='new').exclude(student__admissions__isnull=False).count()
    followups_today = Enquiry.objects.filter(next_followup=today).exclude(student__admissions__isnull=False).count()
    total_fees = Admission.objects.aggregate(t=Sum('total_fee'))['t'] or 0
    total_paid = Payment.objects.filter(is_voided=False).aggregate(t=Sum('amount'))['t'] or 0
    pending_fees = total_fees - total_paid
    today_admissions = Admission.objects.filter(admission_date=today).count()
    uni_stats = Admission.objects.values('university__name').annotate(count=Count('id')).order_by('-count')[:5]
    uni_labels = [s['university__name'] or 'Unknown' for s in uni_stats]
    uni_values = [s['count'] for s in uni_stats]
    course_stats = Admission.objects.values('course__name').annotate(count=Count('id')).order_by('-count')[:5]
    course_labels = [s['course__name'] or 'Unknown' for s in course_stats]
    course_values = [s['count'] for s in course_stats]
    pending_docs_count = Admission.objects.filter(status__in=['documents_pending', 'fee_pending']).count()
    pending_fee_admissions = Admission.objects.filter(status__in=['active', 'fee_pending']).count()
    overdue_followups = Enquiry.objects.filter(next_followup__lt=today).exclude(status__in=['converted', 'lost']).exclude(student__admissions__isnull=False).count()
    recent_enquiries = Enquiry.objects.filter(status='new').exclude(student__admissions__isnull=False).order_by('-created_at')[:5]
    recent_students = Student.objects.filter(enquiries__isnull=True).order_by('-created_at')[:5]
    total_universities = University.objects.count()
    total_courses = Course.objects.count()

    # Monthly admissions trend (last 6 months)
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

    # Enquiry status distribution
    enquiry_stats = Enquiry.objects.values('status').annotate(count=Count('id'))
    enquiry_status_labels = [s['status'] for s in enquiry_stats]
    enquiry_status_values = [s['count'] for s in enquiry_stats]

    # Student status distribution
    student_stats = Student.objects.values('status').annotate(count=Count('id'))
    student_status_labels = [s['status'] for s in student_stats]
    student_status_values = [s['count'] for s in student_stats]

    # Fee collection trend (last 6 months)
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
        'monthly_labels': monthly_labels,
        'monthly_data': monthly_data,
        'enquiry_status_labels': enquiry_status_labels,
        'enquiry_status_values': enquiry_status_values,
        'student_status_labels': student_status_labels,
        'student_status_values': student_status_values,
        'fee_monthly_data': fee_monthly_data,
    })
