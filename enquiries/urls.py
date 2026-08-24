from django.urls import path
from . import views

urlpatterns = [
    path('', views.enquiry_list, name='enquiry_list'),
    path('create/', views.enquiry_create, name='enquiry_create'),
    path('<int:pk>/', views.enquiry_detail, name='enquiry_detail'),
    path('<int:pk>/edit/', views.enquiry_edit, name='enquiry_edit'),
    path('<int:pk>/delete/', views.enquiry_delete, name='enquiry_delete'),
    path('<int:pk>/followup/', views.add_followup, name='add_followup'),
    path('<int:pk>/convert/', views.convert_enquiry, name='convert_enquiry'),
    path('api/student-detail/', views.student_detail_api, name='enquiry_student_detail_api'),
]
