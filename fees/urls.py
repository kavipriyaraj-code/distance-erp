from django.urls import path
from . import views

urlpatterns = [
    path('', views.fee_dashboard, name='fee_dashboard'),
    path('payment/create/<int:admission_id>/', views.payment_create, name='payment_create'),
    path('payment/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payment/<int:pk>/void/', views.payment_void, name='payment_void'),
    path('receipt/<int:pk>/', views.receipt_view, name='receipt_view'),
    path('receipt/<int:pk>/pdf/', views.receipt_pdf, name='receipt_pdf'),
    path('statement/<int:admission_id>/pdf/', views.fee_statement_pdf, name='fee_statement_pdf'),
    path('semesters/', views.semester_list, name='semester_list'),
    path('semesters/add/', views.semester_add, name='semester_add'),
    path('semesters/<int:pk>/edit/', views.semester_edit, name='semester_edit'),
    path('semesters/<int:pk>/delete/', views.semester_delete, name='semester_delete'),
    path('semesters/bulk-create/', views.semester_bulk_create, name='semester_bulk_create'),
    path('student/<int:admission_id>/semesters/', views.student_semester_detail, name='student_semester_detail'),
]
