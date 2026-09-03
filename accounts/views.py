from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseForbidden
from .models import User
from .forms import LoginForm, UserForm, UserCreateForm, ProfileForm, ChangePasswordForm, StaffBankDetailsForm
from .decorators import admin_required, role_required
from .models import StaffBankDetails
from core.audit import log_action


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    return redirect('dashboard_view')


@login_required
@admin_required
def user_list(request):
    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '').strip()
    users = User.objects.all()
    if q:
        users = users.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(email__icontains=q))
    if role_filter:
        users = users.filter(role=role_filter)
    return render(request, 'accounts/user_list.html', {'users': users, 'q': q, 'role_filter': role_filter})


@login_required
@admin_required
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_action(request.user, 'create', 'User', user.pk, user.username)
            messages.success(request, 'User created successfully.')
            return redirect('user_list')
    else:
        form = UserCreateForm()
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User'})


@login_required
@admin_required
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('user_list')
    else:
        form = UserForm(instance=user_obj)
    return render(request, 'accounts/user_form.html', {'form': form, 'title': f'Edit {user_obj.username}', 'edit_user': user_obj})


@login_required
@admin_required
def user_delete(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    if request.method == 'POST':
        log_action(request.user, 'delete', 'User', user_obj.pk, user_obj.username)
        user_obj.delete()
        messages.success(request, 'User deleted.')
        return redirect('user_list')
    return render(request, 'accounts/confirm_delete.html', {'user_obj': user_obj})


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['new_password'])
            request.user.save()
            messages.success(request, 'Password changed. Please login again.')
            return redirect('login')
    else:
        form = ChangePasswordForm()
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
@admin_required
def staff_bank_details(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    bank_details, created = StaffBankDetails.objects.get_or_create(user=user_obj)
    if request.method == 'POST':
        form = StaffBankDetailsForm(request.POST, instance=bank_details)
        if form.is_valid():
            form.save()
            messages.success(request, f'Bank details saved for {user_obj.get_full_name() or user_obj.username}.')
            return redirect('user_list')
    else:
        form = StaffBankDetailsForm(instance=bank_details)
    return render(request, 'accounts/staff_bank_details.html', {'form': form, 'staff_user': user_obj, 'bank_details': bank_details})
