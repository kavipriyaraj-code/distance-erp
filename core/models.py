from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('status_change', 'Status Changed'),
        ('upload', 'Document Uploaded'),
        ('verify', 'Document Verified'),
        ('reject', 'Document Rejected'),
        ('payment', 'Payment Recorded'),
        ('void', 'Payment Voided'),
        ('delete', 'Deleted'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=50)
    entity_id = models.IntegerField()
    entity_str = models.CharField(max_length=200, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.get_action_display()} {self.entity_type} #{self.entity_id}"
