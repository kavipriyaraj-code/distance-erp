from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Course
from .forms import CourseForm
from universities.models import University


@login_required
def course_list(request):
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
def course_create(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('course_list')
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
def course_edit(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('course_list')
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
def course_delete(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('course_list')
    obj = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Course deleted.')
    return redirect('course_list')
