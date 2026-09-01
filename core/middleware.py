from django.shortcuts import redirect
from django.urls import resolve, reverse
from .models import get_current_license


class LicenseMiddleware:
    EXEMPT_URLS = [
        'login',
        'logout',
        'home',
        'public_admission',
        'admission_success',
        'password_reset',
        'password_reset_done',
        'password_reset_confirm',
        'password_reset_complete',
    ]

    EXEMPT_PATHS = [
        '/admin/',
        '/static/',
        '/media/',
        '/about/',
        '/services/',
        '/partner-universities/',
        '/success-stories/',
        '/privacy-policy/',
        '/admission/',
        '/accounts/password-reset/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        try:
            match = resolve(request.path)
            url_name = match.url_name
        except Exception:
            url_name = None

        if url_name in self.EXEMPT_URLS:
            return self.get_response(request)

        for path in self.EXEMPT_PATHS:
            if request.path.startswith(path):
                return self.get_response(request)

        if request.user.role == 'admin':
            return self.get_response(request)

        license = get_current_license()
        if license and not license.is_active:
            return redirect('license_expired')

        return self.get_response(request)
