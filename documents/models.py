from django.db import models
from django.conf import settings
from admissions.models import Admission

class DocumentType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class StudentDocument(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('uploaded', 'Uploaded'), ('verified', 'Verified'), ('rejected', 'Rejected')]
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='documents')
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, related_name='student_documents')
    file = models.FileField(upload_to='documents/%Y/%m/', blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_documents')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['document_type']
        unique_together = ['admission', 'document_type']

    def __str__(self):
        return f"{self.document_type.name} - {self.admission.admission_number}"
