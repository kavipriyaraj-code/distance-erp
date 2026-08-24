from django.contrib import admin
from .models import DocumentType, StudentDocument

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']

@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ['admission', 'document_type', 'status', 'verified_by', 'verified_at']
    list_filter = ['status']
