from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import University
from .forms import UniversityForm
from accounts.decorators import admin_required, role_required
from core.audit import log_action


@login_required
@role_required('admin', 'counsellor')
def university_list(request):
    q = request.GET.get('q', '').strip()
    qs = University.objects.all()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    return render(request, 'universities/list.html', {'universities': qs, 'q': q})


@login_required
@admin_required
def university_create(request):
    if request.method == 'POST':
        form = UniversityForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'University created.')
            return redirect('university_list')
    else:
        form = UniversityForm()
    return render(request, 'universities/form.html', {'form': form, 'title': 'Add University'})


@login_required
@admin_required
def university_edit(request, pk):
    obj = get_object_or_404(University, pk=pk)
    if request.method == 'POST':
        form = UniversityForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'University updated.')
            return redirect('university_list')
    else:
        form = UniversityForm(instance=obj)
    return render(request, 'universities/form.html', {'form': form, 'title': 'Edit University'})


@login_required
@admin_required
def university_delete(request, pk):
    university = get_object_or_404(University, pk=pk)
    if request.method == 'POST':
        log_action(request.user, 'delete', 'University', university.pk, university.name)
        university.delete()
        messages.success(request, 'University deleted.')
    return redirect('university_list')
