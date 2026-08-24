from django.urls import path
from . import views

urlpatterns = [
    path('', views.admission_list, name='admission_list'),
    path('create/', views.admission_create, name='admission_create'),
    path('create/<int:enquiry_id>/', views.admission_create_from_enquiry, name='admission_create_from_enquiry'),
    path('<int:pk>/', views.admission_detail, name='admission_detail'),
    path('<int:pk>/edit/', views.admission_edit, name='admission_edit'),
    path('<int:pk>/status/', views.admission_status_update, name='admission_status_update'),
    path('<int:pk>/delete/', views.admission_delete, name='admission_delete'),
    path('api/courses-by-university/', views.courses_by_university, name='courses_by_university'),
]
