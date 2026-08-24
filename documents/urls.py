from django.urls import path
from . import views

urlpatterns = [
    path('', views.document_overview, name='document_overview'),
    path('<int:admission_id>/', views.document_list, name='document_list'),
    path('<int:admission_id>/upload/', views.document_upload, name='document_upload'),
    path('<int:pk>/verify/', views.document_verify, name='document_verify'),
    path('<int:pk>/reject/', views.document_reject, name='document_reject'),
]
