from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import Enquiry, FollowUp
from .forms import EnquiryForm, FollowUpForm
from core.audit import log_action


@login_required
def enquiry_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    qs = Enquiry.objects.select_related('university', 'course', 'assigned_to').exclude(student__admissions__isnull=False)
    if q:
        qs = qs.filter(mobile__icontains=q)
    if status:
        qs = qs.filter(status=status)
    return render(request, 'enquiries/list.html', {'enquiries': qs, 'q': q, 'status_filter': status})


def student_detail_api(request):
    student_id = request.GET.get('student_id')
    if not student_id:
        return JsonResponse({'error': 'student_id required'}, status=400)
    from students.models import Student
    try:
        s = Student.objects.get(pk=student_id)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)
    return JsonResponse({
        'name': s.name,
        'mobile': s.mobile,
        'whatsapp': s.whatsapp,
        'email': s.email,
        'university': s.university_id or '',
        'course': s.course_id or '',
    })


@login_required
def enquiry_create(request):
    if request.method == 'POST':
        form = EnquiryForm(request.POST)
        if form.is_valid():
            enquiry = form.save(commit=False)
            if not enquiry.assigned_to:
                enquiry.assigned_to = request.user
            enquiry.save()
            log_action(request.user, 'create', 'Enquiry', enquiry.pk, enquiry.enquiry_number)
            messages.success(request, f'Enquiry {enquiry.enquiry_number} created.')
            return redirect('enquiry_detail', pk=enquiry.pk)
    else:
        form = EnquiryForm(initial={'assigned_to': request.user})
    return render(request, 'enquiries/form.html', {'form': form, 'title': 'New Enquiry'})


@login_required
def enquiry_detail(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)
    followups = enquiry.followups.select_related('counsellor').all()
    followup_form = FollowUpForm()
    return render(request, 'enquiries/detail.html', {
        'enquiry': enquiry, 'followups': followups, 'followup_form': followup_form,
    })


@login_required
def enquiry_edit(request, pk):
    obj = get_object_or_404(Enquiry, pk=pk)
    if not request.user.is_admin_user and obj.assigned_to != request.user:
        messages.error(request, 'Access denied.')
        return redirect('enquiry_list')
    if request.method == 'POST':
        form = EnquiryForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            log_action(request.user, 'update', 'Enquiry', obj.pk, obj.enquiry_number)
            messages.success(request, 'Enquiry updated.')
            return redirect('enquiry_detail', pk=pk)
    else:
        form = EnquiryForm(instance=obj)
    return render(request, 'enquiries/form.html', {'form': form, 'title': 'Edit Enquiry'})


@login_required
def add_followup(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)
    if request.method == 'POST':
        form = FollowUpForm(request.POST)
        if form.is_valid():
            fu = form.save(commit=False)
            fu.enquiry = enquiry
            fu.counsellor = request.user
            fu.save()
            log_action(request.user, 'create', 'FollowUp', fu.pk, f"Enquiry {enquiry.enquiry_number}")
            if fu.new_status:
                enquiry.status = fu.new_status
            if fu.next_followup:
                enquiry.next_followup = fu.next_followup
            enquiry.save()
            messages.success(request, 'Follow-up added.')
    return redirect('enquiry_detail', pk=pk)


@login_required
def convert_enquiry(request, pk):
    from students.models import Student
    enquiry = get_object_or_404(Enquiry, pk=pk)
    if request.method == 'POST':
        if enquiry.student:
            student = enquiry.student
        else:
            existing = Student.objects.filter(mobile=enquiry.mobile).first()
            student, created = Student.objects.get_or_create(
                mobile=enquiry.mobile,
                defaults={'name': enquiry.student_name, 'whatsapp': enquiry.whatsapp, 'email': enquiry.email, 'status': 'applicant'}
            )
            if existing and created:
                messages.warning(request, f'A student with mobile {enquiry.mobile} already existed: {existing.student_id}. Used existing record.')
        enquiry.status = 'converted'
        enquiry.save()
        log_action(request.user, 'update', 'Enquiry', enquiry.pk, f"Converted to Student {student.student_id}", details=f"Status: converted")
        messages.success(request, f'Student {student.student_id} created from enquiry.')
        return redirect('admission_create_from_enquiry', enquiry_id=enquiry.pk)
    return redirect('enquiry_detail', pk=pk)


@login_required
def enquiry_delete(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('enquiry_list')
    enquiry = get_object_or_404(Enquiry, pk=pk)
    if request.method == 'POST':
        log_action(request.user, 'delete', 'Enquiry', enquiry.pk, enquiry.enquiry_number)
        enquiry.delete()
        messages.success(request, 'Enquiry deleted.')
    return redirect('enquiry_list')
