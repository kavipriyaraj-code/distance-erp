from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Course
from .forms import CourseForm
from universities.models import University
from accounts.decorators import admin_required, role_required


@login_required
@role_required('admin', 'counsellor')
def course_list(request):
    if request.method == 'POST' and request.POST.get('action') == 'recreate_all':
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        from fees.models import Semester
        from admissions.models import Admission

        courses = Course.objects.filter(fee_per_year__gt=0)
        total_created = 0
        for course in courses:
            num_years = course.duration_years or 3
            num_semesters = num_years * 2
            fee_per_sem = course.fee_per_year / 2
            start = datetime.now().date().replace(month=1, day=1)

            Semester.objects.filter(course=course).delete()

            for i in range(1, num_semesters + 1):
                due = start + relativedelta(months=6 * (i - 1))
                year = (i - 1) // 2 + 1
                sem_in_year = (i - 1) % 2 + 1
                Semester.objects.create(
                    course=course,
                    name=f'Year {year} Semester {sem_in_year}',
                    semester_number=i,
                    fee_amount=fee_per_sem,
                    due_date=due,
                    description=f'{course.name} - Year {year}, Sem {sem_in_year}',
                )
            total_created += num_semesters
            Admission.objects.filter(course=course).update(total_fee=course.total_fee)

        messages.success(request, f'Recreated {total_created} semesters for {courses.count()} courses. Student admissions updated.')
        return redirect('course_list')

    q = request.GET.get('q', '').strip()
    university_id = request.GET.get('university', '')
    qs = Course.objects.select_related('university').all()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(university__name__icontains=q))
    selected_university = None
    if university_id:
        qs = qs.filter(university_id=university_id)
        selected_university = University.objects.filter(pk=university_id).first()
    universities = University.objects.all()
    return render(request, 'courses/list.html', {'courses': qs, 'q': q, 'universities': universities, 'selected_university': selected_university})


@login_required
@admin_required
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course created.')
            return redirect('course_list')
    else:
        form = CourseForm()
    return render(request, 'courses/form.html', {'form': form, 'title': 'Add Course'})


@login_required
@admin_required
def course_edit(request, pk):
    obj = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated.')
            return redirect('course_list')
    else:
        form = CourseForm(instance=obj)
    return render(request, 'courses/form.html', {'form': form, 'title': 'Edit Course'})


@login_required
@admin_required
def course_delete(request, pk):
    obj = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Course deleted.')
    return redirect('course_list')
