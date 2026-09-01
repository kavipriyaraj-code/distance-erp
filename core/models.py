from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, date


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
        return f"{self.action} {self.entity_type} #{self.entity_id}"


class License(models.Model):
    LICENSE_TYPES = [
        ('yearly', 'Yearly'),
        ('monthly', 'Monthly'),
    ]
    license_key = models.CharField(max_length=100, unique=True)
    license_type = models.CharField(max_length=20, choices=LICENSE_TYPES, default='yearly')
    start_date = models.DateField()
    expiry_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.license_key} ({self.get_status()})"

    @property
    def is_active(self):
        return date.today() <= self.expiry_date

    @property
    def is_expiring_soon(self):
        return 0 < self.days_remaining <= 30

    @property
    def days_remaining(self):
        today = date.today()
        if today > self.expiry_date:
            return 0
        return (self.expiry_date - today).days

    def get_status(self):
        today = date.today()
        if today > self.expiry_date:
            return 'EXPIRED'
        elif self.days_remaining <= 30:
            return 'EXPIRING_SOON'
        return 'ACTIVE'

    def save(self, *args, **kwargs):
        if not self.expiry_date and self.start_date:
            self.expiry_date = self.start_date + timedelta(days=365)
        super().save(*args, **kwargs)


def get_current_license():
    return License.objects.order_by('-start_date').first()


def is_license_active():
    lic = get_current_license()
    if not lic:
        return True
    return lic.is_active


def get_license_status():
    lic = get_current_license()
    if not lic:
        return 'ACTIVE', 999, None
    return lic.get_status(), lic.days_remaining, lic
