from django.urls import path
from . import views

urlpatterns = [
    path('', views.university_list, name='university_list'),
    path('create/', views.university_create, name='university_create'),
    path('<int:pk>/edit/', views.university_edit, name='university_edit'),
    path('<int:pk>/delete/', views.university_delete, name='university_delete'),
]
