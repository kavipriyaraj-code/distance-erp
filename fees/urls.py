from django.urls import path
from . import views

urlpatterns = [
    path('', views.fee_dashboard, name='fee_dashboard'),
    path('payment/create/<int:admission_id>/', views.payment_create, name='payment_create'),
    path('payment/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payment/<int:pk>/void/', views.payment_void, name='payment_void'),
    path('receipt/<int:pk>/', views.receipt_view, name='receipt_view'),
    path('receipt/<int:pk>/pdf/', views.receipt_pdf, name='receipt_pdf'),
]
