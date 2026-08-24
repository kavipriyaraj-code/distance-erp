from django.contrib import admin
from .models import Course

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'university', 'course_type', 'total_fee', 'is_active']
    list_filter = ['course_type', 'is_active', 'university']
    search_fields = ['name', 'code']
