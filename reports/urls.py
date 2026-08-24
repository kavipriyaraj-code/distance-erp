from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('admissions/', views.admission_reports, name='admission_reports'),
    path('enquiries/', views.enquiry_reports, name='enquiry_reports'),
    path('fees/', views.fee_reports, name='fee_reports'),
]
