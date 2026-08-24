from django.contrib import admin
from .models import Admission, AcademicSession

@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ['admission_number', 'student', 'university', 'course', 'total_fee', 'status', 'admission_date']
    list_filter = ['status', 'university', 'course']
    search_fields = ['admission_number', 'student__name']

@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
