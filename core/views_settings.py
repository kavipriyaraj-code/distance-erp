from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import User


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
    })
