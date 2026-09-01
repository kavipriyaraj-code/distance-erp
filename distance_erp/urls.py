from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views
from core.views_public import public_admission, admission_success
from core.views_settings import settings_view, license_expired_view, license_renew_view, license_payment_view
from core import views_pages

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.home_view, name='home'),
    path('admission/', public_admission, name='public_admission'),
    path('admission/success/<int:pk>/', admission_success, name='admission_success'),
    path('about/', views_pages.about_view, name='about'),
    path('services/', views_pages.services_view, name='services'),
    path('services/university-selection/', views_pages.service_university_view, name='service_university'),
    path('services/application-assistance/', views_pages.service_application_view, name='service_application'),
    path('services/scholarship-guidance/', views_pages.service_scholarship_view, name='service_scholarship'),
    path('services/distance-education/', views_pages.service_distance_view, name='service_distance'),
    path('success-stories/', views_pages.success_stories_view, name='success_stories'),
    path('partner-universities/', views_pages.universities_view, name='partner_universities'),
    path('privacy-policy/', views_pages.privacy_view, name='privacy_policy'),
    path('', include('accounts.urls')),
    path('dashboard/', core_views.dashboard_view, name='dashboard'),
    path('universities/', include('universities.urls')),
    path('courses/', include('courses.urls')),
    path('enquiries/', include('enquiries.urls')),
    path('students/', include('students.urls')),
    path('admissions/', include('admissions.urls')),
    path('documents/', include('documents.urls')),
    path('fees/', include('fees.urls')),
    path('reports/', include('reports.urls')),
    path('finance/', include('finance.urls')),
    path('settings/', settings_view, name='settings'),
    path('settings/renew/', license_renew_view, name='license_renew'),
    path('settings/payment/', license_payment_view, name='license_payment'),
    path('license-expired/', license_expired_view, name='license_expired'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
