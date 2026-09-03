from django.db import models
from django.conf import settings
from students.models import Student
from universities.models import University
from courses.models import Course

class AcademicSession(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-name']

    def __str__(self):
        return self.name

class Admission(models.Model):
    STATUS_CHOICES = [
        ('application', 'Application'),
        ('documents_pending', 'Documents Pending'),
        ('documents_verified', 'Documents Verified'),
        ('fee_pending', 'Fee Pending'),
        ('submitted', 'Submitted'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
    ]
    admission_number = models.CharField(max_length=25, unique=True, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='admissions')
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    session = models.ForeignKey(AcademicSession, on_delete=models.SET_NULL, null=True, blank=True)
    admission_date = models.DateField(auto_now_add=True)
    counsellor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='admissions')
    total_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    incentive = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Incentive amount for counsellor')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='application')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.admission_number} - {self.student.name}"

    def save(self, *args, **kwargs):
        if not self.admission_number:
            from datetime import date
            year = date.today().year
            last = Admission.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.admission_number = f"RENIC-{year}-{num:06d}"
        if not self.total_fee and self.course:
            self.total_fee = self.course.total_fee
        super().save(*args, **kwargs)

    @property
    def paid_amount(self):
        return sum(p.amount for p in self.payments.filter(is_voided=False))

    @property
    def balance_amount(self):
        return max(self.total_fee - self.paid_amount, 0)
