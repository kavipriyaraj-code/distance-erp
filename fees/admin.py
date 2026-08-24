from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'admission', 'amount', 'payment_mode', 'payment_date', 'is_voided']
    list_filter = ['payment_mode', 'is_voided']
    search_fields = ['receipt_number', 'admission__admission_number']
