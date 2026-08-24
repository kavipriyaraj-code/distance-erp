from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import User
from .forms import LoginForm, UserForm, UserCreateForm, ProfileForm, ChangePasswordForm
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
def user_list(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    q = request.GET.get('q', '').strip()
    users = User.objects.all()
    if q:
        users = users.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(email__icontains=q))
    return render(request, 'accounts/user_list.html', {'users': users, 'q': q})

@login_required
def user_create(request):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
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
def user_edit(request, pk):
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
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
def user_delete(request, pk):
    if not request.user.is_super_admin:
        messages.error(request, 'Only super admin can delete users.')
        return redirect('user_list')
    user_obj = get_object_or_404(User, pk=pk)
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
