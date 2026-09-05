from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import Admission, AcademicSession
from .forms import AdmissionForm
from students.models import Student
from core.audit import log_action
from accounts.decorators import admin_required, role_required


@login_required
def courses_by_university(request):
    university_id = request.GET.get('university_id', '')
    if university_id:
        from courses.models import Course
        courses = list(Course.objects.filter(university_id=university_id, is_active=True).values('id', 'name', 'total_fee'))
        return JsonResponse({'courses': courses})
    return JsonResponse({'courses': []})


@login_required
@role_required('admin', 'counsellor', 'accountant')
def admission_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    qs = Admission.objects.select_related('student', 'university', 'course', 'session').all()
    if q:
        qs = qs.filter(Q(student__mobile__icontains=q) | Q(student__student_id__icontains=q) | Q(admission_number__icontains=q) | Q(student__name__icontains=q))
    if status:
        qs = qs.filter(status=status)
    return render(request, 'admissions/list.html', {'admissions': qs, 'q': q, 'status_filter': status})


@login_required
@role_required('admin', 'counsellor')
def admission_create(request):
    if request.method == 'POST':
        form = AdmissionForm(request.POST)
        if form.is_valid():
            student_id_val = form.cleaned_data.get('student_id_input', '').strip()
            try:
                student = Student.objects.get(student_id=student_id_val)
            except Student.DoesNotExist:
                form.add_error('student_id_input', f'No student found with ID: {student_id_val}')
                return render(request, 'admissions/form.html', {'form': form, 'title': 'New Admission'})
            existing = Admission.objects.filter(student=student).exclude(status='cancelled').exists()
            if existing:
                form.add_error('student_id_input', f'{student.name} already has an admission. Each student can only have one admission.')
                return render(request, 'admissions/form.html', {'form': form, 'title': 'New Admission'})
            admission = form.save(commit=False)
            admission.student = student
            admission.counsellor = request.user
            admission.save()
            log_action(request.user, 'create', 'Admission', admission.pk, admission.admission_number)
            messages.success(request, f'Admission {admission.admission_number} created.')

            if student.email:
                try:
                    import resend
                    from django.conf import settings as conf
                    api_key = getattr(conf, 'RESEND_API_KEY', '')
                    if api_key:
                        resend.api_key = api_key
                        resend.Emails.send({
                            "from": getattr(conf, 'DEFAULT_FROM_EMAIL', 'RENIC ERP <noreply@renictech.com>'),
                            "to": [student.email],
                            "subject": f'Admission Confirmed - RENIC TECH',
                            "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto">
<h2 style="color:#0d6efd">Admission Confirmed</h2>
<p>Dear {student.name},</p>
<p>Your admission has been successfully created.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">Admission No</td><td style="padding:8px;border:1px solid #ddd">{admission.admission_number}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">Course</td><td style="padding:8px;border:1px solid #ddd">{admission.course.name}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">University</td><td style="padding:8px;border:1px solid #ddd">{admission.university.name}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">Total Fee</td><td style="padding:8px;border:1px solid #ddd">₹{admission.total_fee:,.0f}</td></tr>
</table>
<p style="color:#666;font-size:13px">Welcome to RENIC TECH!<br><strong>RENIC TECH</strong></p>
</div>""",
                        })
                except Exception:
                    pass

            return redirect('admission_detail', pk=admission.pk)
    else:
        form = AdmissionForm()
    return render(request, 'admissions/form.html', {'form': form, 'title': 'New Admission'})


@login_required
@role_required('admin', 'counsellor')
def admission_create_from_enquiry(request, enquiry_id):
    from enquiries.models import Enquiry
    enquiry = get_object_or_404(Enquiry, pk=enquiry_id)
    student, _ = Student.objects.get_or_create(
        mobile=enquiry.mobile,
        defaults={'name': enquiry.student_name, 'whatsapp': enquiry.whatsapp, 'email': enquiry.email, 'status': 'applicant'}
    )
    if request.method == 'POST':
        form = AdmissionForm(request.POST)
        if form.is_valid():
            admission = form.save(commit=False)
            admission.student = student
            admission.counsellor = request.user
            admission.save()
            enquiry.status = 'converted'
            enquiry.save()
            log_action(request.user, 'create', 'Admission', admission.pk, admission.admission_number, details=f"From enquiry {enquiry.enquiry_number}")
            messages.success(request, f'Admission {admission.admission_number} created.')

            if student.email:
                try:
                    import resend
                    from django.conf import settings as conf
                    api_key = getattr(conf, 'RESEND_API_KEY', '')
                    if api_key:
                        resend.api_key = api_key
                        resend.Emails.send({
                            "from": getattr(conf, 'DEFAULT_FROM_EMAIL', 'RENIC ERP <noreply@renictech.com>'),
                            "to": [student.email],
                            "subject": f'Admission Confirmed - RENIC TECH',
                            "html": f"""<div style="font-family:sans-serif;max-width:600px;margin:0 auto">
<h2 style="color:#0d6efd">Admission Confirmed</h2>
<p>Dear {student.name},</p>
<p>Your admission has been successfully created.</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">Admission No</td><td style="padding:8px;border:1px solid #ddd">{admission.admission_number}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">Course</td><td style="padding:8px;border:1px solid #ddd">{admission.course.name}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">University</td><td style="padding:8px;border:1px solid #ddd">{admission.university.name}</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;background:#f8f9fa">Total Fee</td><td style="padding:8px;border:1px solid #ddd">₹{admission.total_fee:,.0f}</td></tr>
</table>
<p style="color:#666;font-size:13px">Welcome to RENIC TECH!<br><strong>RENIC TECH</strong></p>
</div>""",
                        })
                except Exception:
                    pass

            return redirect('admission_detail', pk=admission.pk)
    else:
        form = AdmissionForm(initial={
            'student_id_input': student.student_id,
            'university': enquiry.university_id or '',
            'course': enquiry.course_id or '',
        })
    return render(request, 'admissions/form.html', {'form': form, 'title': f'Admission from {enquiry.enquiry_number}', 'from_enquiry': True})


@login_required
@role_required('admin', 'counsellor', 'accountant')
def admission_detail(request, pk):
    admission = get_object_or_404(Admission.objects.select_related('student', 'university', 'course', 'session', 'counsellor'), pk=pk)
    payments = admission.payments.select_related('received_by', 'semester').filter(is_voided=False)
    documents = admission.documents.select_related('document_type').all()
    return render(request, 'admissions/detail.html', {
        'admission': admission, 'payments': payments, 'documents': documents,
    })


@login_required
@admin_required
def admission_edit(request, pk):
    obj = get_object_or_404(Admission, pk=pk)
    if request.method == 'POST':
        form = AdmissionForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            log_action(request.user, 'update', 'Admission', obj.pk, obj.admission_number)
            messages.success(request, 'Admission updated.')
            return redirect('admission_detail', pk=pk)
    else:
        form = AdmissionForm(instance=obj)
    return render(request, 'admissions/form.html', {'form': form, 'title': 'Edit Admission'})


@login_required
@admin_required
def admission_status_update(request, pk):
    obj = get_object_or_404(Admission, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        valid = [s[0] for s in Admission.STATUS_CHOICES]
        if new_status in valid:
            old_status = obj.get_status_display()
            obj.status = new_status
            obj.save()
            log_action(request.user, 'status_change', 'Admission', obj.pk, obj.admission_number, details=f"From {old_status} to {obj.get_status_display()}")
            messages.success(request, f'Status updated to {obj.get_status_display()}.')
    return redirect('admission_detail', pk=pk)


@login_required
@admin_required
def admission_delete(request, pk):
    admission = get_object_or_404(Admission, pk=pk)
    if request.method == 'POST':
        log_action(request.user, 'delete', 'Admission', admission.pk, admission.admission_number)
        admission.delete()
        messages.success(request, 'Admission deleted.')
    return redirect('admission_list')
