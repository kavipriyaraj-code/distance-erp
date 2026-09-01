from django.db import models
from django.conf import settings
from admissions.models import Admission
from courses.models import Course


class Semester(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='semesters')
    name = models.CharField(max_length=100)
    semester_number = models.PositiveIntegerField()
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['course', 'semester_number']
        unique_together = ['course', 'semester_number']

    def __str__(self):
        return f"{self.course.name} - {self.name}"

    @property
    def is_overdue(self):
        from django.utils import timezone
        return timezone.localdate() > self.due_date

    @property
    def days_until_due(self):
        from django.utils import timezone
        delta = self.due_date - timezone.localdate()
        return delta.days


class Payment(models.Model):
    MODE_CHOICES = [('cash', 'Cash'), ('upi', 'UPI'), ('bank_transfer', 'Bank Transfer'), ('card', 'Card'), ('other', 'Other')]
    receipt_number = models.CharField(max_length=20, unique=True, editable=False)
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='payments')
    semester = models.ForeignKey(Semester, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    payment_mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='cash')
    transaction_ref = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    is_voided = models.BooleanField(default=False)
    voided_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"{self.receipt_number} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            last = Payment.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.receipt_number = f"RCP-{num:06d}"
        super().save(*args, **kwargs)
