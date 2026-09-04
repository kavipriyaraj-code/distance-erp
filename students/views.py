from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Student
from .forms import StudentForm
from core.audit import log_action
from accounts.decorators import admin_required, role_required


@login_required
@role_required('admin', 'counsellor')
def student_list(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    qs = Student.objects.all()
    if q:
        qs = qs.filter(Q(mobile__icontains=q) | Q(student_id__icontains=q) | Q(name__icontains=q))
    if status:
        qs = qs.filter(status=status)
    return render(request, 'students/list.html', {'students': qs, 'q': q, 'status_filter': status})


@login_required
@role_required('admin', 'counsellor')
def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            mobile = form.cleaned_data.get('mobile', '').strip()
            if mobile:
                existing = Student.objects.filter(mobile=mobile).first()
                if existing:
                    messages.warning(request, f'A student with mobile {mobile} already exists: {existing.student_id} - {existing.name}.')
                    return render(request, 'students/form.html', {'form': form, 'title': 'New Student'})
            student = form.save()
            log_action(request.user, 'create', 'Student', student.pk, student.student_id)
            messages.success(request, f'Student {student.student_id} created.')
            return redirect('student_profile', pk=student.pk)
    else:
        form = StudentForm()
    return render(request, 'students/form.html', {'form': form, 'title': 'Add Student'})


@login_required
@role_required('admin', 'counsellor')
def student_profile(request, pk):
    student = get_object_or_404(Student, pk=pk)
    admissions = student.admissions.select_related('university', 'course').all()
    return render(request, 'students/profile.html', {'student': student, 'admissions': admissions})


@login_required
@admin_required
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            student = form.save()
            log_action(request.user, 'update', 'Student', student.pk, student.student_id)
            messages.success(request, 'Student updated.')
            return redirect('student_profile', pk=pk)
    else:
        form = StudentForm(instance=student)
    return render(request, 'students/form.html', {'form': form, 'title': 'Edit Student', 'student': student})


@login_required
@admin_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        log_action(request.user, 'delete', 'Student', student.pk, student.student_id)
        student.delete()
        messages.success(request, 'Student deleted.')
    return redirect('student_list')
