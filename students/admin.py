from django.contrib import admin
from .models import Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'name', 'mobile', 'status', 'created_at']
    list_filter = ['status', 'gender']
    search_fields = ['student_id', 'name', 'mobile']
