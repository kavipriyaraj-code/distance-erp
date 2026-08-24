from django.contrib import admin
from .models import Enquiry, FollowUp

class FollowUpInline(admin.TabularInline):
    model = FollowUp
    extra = 0

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ['enquiry_number', 'student_name', 'mobile', 'status', 'source', 'assigned_to', 'next_followup']
    list_filter = ['status', 'source']
    search_fields = ['student_name', 'mobile', 'enquiry_number']
    inlines = [FollowUpInline]
