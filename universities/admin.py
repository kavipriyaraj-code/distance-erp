from django.contrib import admin
from .models import University

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'phone', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
