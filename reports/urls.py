from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('admissions/', views.admission_reports, name='admission_reports'),
    path('admissions/university/<int:university_id>/', views.university_admission_detail, name='university_admission_detail'),
    path('enquiries/', views.enquiry_reports, name='enquiry_reports'),
    path('fees/', views.fee_reports, name='fee_reports'),
    path('payments/', views.payment_reports, name='payment_reports'),
    path('import-students/', views.import_students, name='import_students'),
    path('export-students/', views.export_students_excel, name='export_students_excel'),
]
