from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def admin_required(view_func):
    return role_required('admin')(view_func)


def counsellor_required(view_func):
    return role_required('admin', 'counsellor')(view_func)


def accountant_required(view_func):
    return role_required('admin', 'accountant')(view_func)


def staff_required(view_func):
    return role_required('admin', 'counsellor', 'accountant')(view_func)
