from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from datetime import date, timedelta
from admissions.models import Admission
from enquiries.models import Enquiry
from fees.models import Payment
from students.models import Student
from accounts.models import User

@login_required
def reports_dashboard(request):
    return render(request, 'reports/dashboard.html')

@login_required
def admission_reports(request):
    qs = Admission.objects.select_related('student', 'university', 'course', 'counsellor')
    counsellor_id = request.GET.get('counsellor')
    if counsellor_id:
        qs = qs.filter(counsellor_id=counsellor_id)
    total = qs.count()
    counsellors = User.objects.filter(role__in=['counsellor', 'admin', 'super_admin'])
    return render(request, 'reports/admissions.html', {
        'admissions': qs, 'total': total, 'counsellors': counsellors,
    })

@login_required
def enquiry_reports(request):
    qs = Enquiry.objects.all()
    source = request.GET.get('source')
    status = request.GET.get('status')
    counsellor_id = request.GET.get('counsellor')
    if source:
        qs = qs.filter(source=source)
    if status:
        qs = qs.filter(status=status)
    if counsellor_id:
        qs = qs.filter(assigned_to_id=counsellor_id)
    total = qs.count()
    new_count = qs.filter(status='new').count()
    converted = qs.filter(status='converted').count()
    lost = qs.filter(status='lost').count()
    rate = round(converted / total * 100, 1) if total else 0
    counsellors = User.objects.filter(role__in=['counsellor', 'admin', 'super_admin'])
    return render(request, 'reports/enquiries.html', {
        'enquiries': qs, 'total': total, 'new_count': new_count,
        'converted': converted, 'lost': lost, 'rate': rate, 'counsellors': counsellors,
    })

@login_required
def fee_reports(request):
    payments = Payment.objects.filter(is_voided=False).select_related('admission__student', 'admission__university', 'admission__course', 'received_by')
    total_collected = payments.aggregate(total=Sum('amount'))['total'] or 0
    total_pending = Admission.objects.filter(status__in=['active', 'fee_pending']).aggregate(
        t=Sum('total_fee'))['t'] or 0
    total_paid = Payment.objects.filter(is_voided=False).aggregate(t=Sum('amount'))['t'] or 0
    pending = total_pending - total_paid
    return render(request, 'reports/fees.html', {
        'payments': payments, 'total_collected': total_collected,
        'total_pending': pending,
    })
