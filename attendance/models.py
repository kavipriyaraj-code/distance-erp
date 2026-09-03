from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class AttendanceSettings(models.Model):
    total_working_days = models.IntegerField(default=26, help_text='Default working days per month')
    half_day_deduct_unpaid = models.BooleanField(default=False, help_text='Count half day as 0.5 unpaid leave')
    absent_as_unpaid = models.BooleanField(default=True, help_text='Treat absent as unpaid leave for deduction')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Attendance Settings'
        verbose_name_plural = 'Attendance Settings'

    def __str__(self):
        return f'Settings ({self.total_working_days} working days/month)'

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class StaffAttendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('paid_leave', 'Paid Leave'),
        ('unpaid_leave', 'Unpaid Leave'),
        ('holiday', 'Holiday'),
    ]

    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=timezone.localdate)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    working_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='present')
    admin_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'staff__first_name']
        unique_together = ['staff', 'date']
        verbose_name_plural = 'Staff Attendances'

    def __str__(self):
        return f'{self.staff.username} - {self.date} - {self.get_status_display()}'

    def clean(self):
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValidationError('Check-out time must be after check-in time.')

    def save(self, *args, **kwargs):
        if self.check_in and self.check_out:
            from datetime import datetime
            dt_in = datetime.combine(self.date, self.check_in)
            dt_out = datetime.combine(self.date, self.check_out)
            delta = dt_out - dt_in
            self.working_hours = round(delta.total_seconds() / 3600, 2)
        super().save(*args, **kwargs)

    @property
    def check_in_display(self):
        return self.check_in.strftime('%I:%M %p') if self.check_in else '-'

    @property
    def check_out_display(self):
        return self.check_out.strftime('%I:%M %p') if self.check_out else '-'

    @property
    def status_badge_class(self):
        return {
            'present': 'bg-success',
            'absent': 'bg-danger',
            'half_day': 'bg-warning text-dark',
            'paid_leave': 'bg-info',
            'unpaid_leave': 'bg-secondary',
            'holiday': 'bg-primary',
        }.get(self.status, 'bg-secondary')
