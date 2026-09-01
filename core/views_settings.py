from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User
from core.models import License, get_current_license


@login_required
def settings_view(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    from universities.models import University
    from courses.models import Course
    from admissions.models import AcademicSession
    from students.models import Student
    from enquiries.models import Enquiry
    from documents.models import DocumentType
    from fees.models import Payment
    from finance.models import FinanceSettings
    from django.db.models import Sum

    total_users = User.objects.count()
    total_universities = University.objects.count()
    total_courses = Course.objects.count()
    total_students = Student.objects.count()
    total_enquiries = Enquiry.objects.count()
    total_admissions = __import__('admissions.models', fromlist=['Admission']).Admission.objects.count()
    total_fees = Payment.objects.filter(is_voided=False).aggregate(t=Sum('amount'))['t'] or 0
    sessions = AcademicSession.objects.all()
    doc_types = DocumentType.objects.all()
    current_license = get_current_license()

    semester_start_month = FinanceSettings.get_value('semester_start_month', '1')
    semester_due_day = FinanceSettings.get_value('semester_due_day', '15')
    reminder_days_before = FinanceSettings.get_value('reminder_days_before', '7')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_session':
            name = request.POST.get('name', '').strip()
            if name:
                AcademicSession.objects.get_or_create(name=name, defaults={'is_active': True})
                messages.success(request, f'Session "{name}" created.')
            return redirect('settings')

        if action == 'toggle_session':
            sid = request.POST.get('session_id')
            session = AcademicSession.objects.filter(pk=sid).first()
            if session:
                session.is_active = not session.is_active
                session.save()
                messages.success(request, f'Session "{session.name}" {"activated" if session.is_active else "deactivated"}.')
            return redirect('settings')

        if action == 'add_doc_type':
            name = request.POST.get('doc_name', '').strip()
            if name:
                DocumentType.objects.get_or_create(name=name, defaults={'is_active': True})
                messages.success(request, f'Document type "{name}" created.')
            return redirect('settings')

        if action == 'toggle_doc_type':
            did = request.POST.get('doc_id')
            dt = DocumentType.objects.filter(pk=did).first()
            if dt:
                dt.is_active = not dt.is_active
                dt.save()
                messages.success(request, f'Document type "{dt.name}" {"activated" if dt.is_active else "deactivated"}.')
            return redirect('settings')

        if action == 'delete_session':
            sid = request.POST.get('session_id')
            session = AcademicSession.objects.filter(pk=sid).first()
            if session:
                session.delete()
                messages.success(request, f'Session "{session.name}" deleted.')
            return redirect('settings')

        if action == 'delete_doc_type':
            did = request.POST.get('doc_id')
            dt = DocumentType.objects.filter(pk=did).first()
            if dt:
                dt.delete()
                messages.success(request, f'Document type "{dt.name}" deleted.')
            return redirect('settings')

        if action == 'save_semester_settings':
            FinanceSettings.set_value('semester_start_month', request.POST.get('semester_start_month', '1'), 'Semester start month')
            FinanceSettings.set_value('semester_due_day', request.POST.get('semester_due_day', '15'), 'Semester due day')
            FinanceSettings.set_value('reminder_days_before', request.POST.get('reminder_days_before', '7'), 'Reminder days before due date')
            messages.success(request, 'Semester fee settings updated.')
            return redirect('settings')

        if action == 'renew_license':
            from datetime import date as date_type, timedelta
            import uuid
            new_key = f'RENIC-ERP-{uuid.uuid4().hex[:8].upper()}'
            if current_license:
                new_start = current_license.expiry_date + timedelta(days=1)
                new_expiry = date_type(new_start.year + 1, new_start.month, new_start.day)
                License.objects.create(
                    license_key=new_key,
                    license_type='yearly',
                    start_date=new_start,
                    expiry_date=new_expiry,
                )
                messages.success(request, f'License renewed. New expiry: {new_expiry.strftime("%d %b %Y")}')
            else:
                today = date_type.today()
                new_expiry = date_type(today.year + 1, today.month, today.day)
                License.objects.create(
                    license_key=new_key,
                    license_type='yearly',
                    start_date=today,
                    expiry_date=new_expiry,
                )
                messages.success(request, 'License activated.')
            return redirect('settings')

    return render(request, 'settings.html', {
        'total_users': total_users,
        'total_universities': total_universities,
        'total_courses': total_courses,
        'total_students': total_students,
        'total_enquiries': total_enquiries,
        'total_admissions': total_admissions,
        'total_fees': total_fees,
        'sessions': sessions,
        'doc_types': doc_types,
        'universities': University.objects.all(),
        'courses': Course.objects.select_related('university').all(),
        'users': User.objects.all(),
        'current_license': current_license,
        'semester_start_month': semester_start_month,
        'semester_due_day': semester_due_day,
        'reminder_days_before': reminder_days_before,
    })


@login_required
def license_expired_view(request):
    from core.models import get_current_license
    lic = get_current_license()
    expiry_date = lic.expiry_date.strftime('%d %b %Y') if lic else 'N/A'
    return render(request, 'license_expired.html', {'expiry_date': expiry_date})


@login_required
def license_renew_view(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    from core.models import License, get_current_license
    current_license = get_current_license()

    if request.method == 'POST':
        plan = request.POST.get('plan', 'standard')
        return redirect(f'/settings/payment/?plan={plan}')

    return render(request, 'license_renew.html', {
        'current_license': current_license,
    })


@login_required
def license_payment_view(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    from core.models import License, get_current_license
    from datetime import date as date_type, timedelta
    import uuid

    plan = request.GET.get('plan', 'standard')
    plan_prices = {'basic': 25000, 'standard': 50000, 'premium': 100000}
    plan_names = {'basic': 'Basic', 'standard': 'Standard', 'premium': 'Premium'}

    amount = plan_prices.get(plan, 50000)
    gst = round(amount * 0.18)
    total = amount + gst

    current_license = get_current_license()
    if current_license:
        start_date = current_license.expiry_date + timedelta(days=1)
    else:
        start_date = date_type.today()
    end_date = date_type(start_date.year + 1, start_date.month, start_date.day)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'process_payment':
            new_key = f'RENIC-ERP-{uuid.uuid4().hex[:8].upper()}'
            License.objects.create(
                license_key=new_key,
                license_type='yearly',
                start_date=start_date,
                expiry_date=end_date,
            )
            messages.success(request, f'Payment successful! License activated ({plan_names.get(plan, "Standard")} plan). Expiry: {end_date.strftime("%d %b %Y")}')
            return redirect('settings')

    return render(request, 'license_payment.html', {
        'plan': plan,
        'plan_name': plan_names.get(plan, 'Standard'),
        'amount': amount,
        'gst': gst,
        'total': total,
        'start_date': start_date.strftime('%d %b %Y'),
        'end_date': end_date.strftime('%d %b %Y'),
    })
