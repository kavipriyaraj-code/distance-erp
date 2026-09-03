from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_attendance_list, name='admin_attendance_list'),
    path('check-in/', views.staff_checkin_view, name='staff_checkin'),
    path('history/', views.staff_attendance_history, name='staff_attendance_history'),
    path('monthly-report/', views.attendance_monthly_report, name='attendance_monthly_report'),
]
