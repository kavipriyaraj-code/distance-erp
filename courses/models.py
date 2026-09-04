from django.db import models
from universities.models import University

class Course(models.Model):
    TYPE_CHOICES = [('UG', 'UG'), ('PG', 'PG'), ('Diploma', 'Diploma'), ('Certificate', 'Certificate'), ('Other', 'Other')]
    CATEGORY_CHOICES = [
        ('Engineering', 'Engineering'),
        ('Science', 'Science'),
        ('Arts', 'Arts'),
        ('Commerce', 'Commerce'),
        ('Management', 'Management'),
        ('Computer Applications', 'Computer Applications'),
        ('Other', 'Other'),
    ]
    DURATION_YEARS = [(1, '1 Year'), (2, '2 Years'), (3, '3 Years'), (4, '4 Years')]

    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=30)
    course_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='UG')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='Other')
    duration = models.CharField(max_length=50, blank=True)
    duration_years = models.PositiveIntegerField(default=3, choices=DURATION_YEARS, help_text='Number of years for this course')
    eligibility = models.TextField(blank=True)
    fee_per_year = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Fee per year - total fee is auto-calculated')
    total_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Auto-calculated: fee_per_year × duration_years')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['university', 'name']
        unique_together = ['university', 'code']

    def __str__(self):
        return f"{self.name} - {self.university.code}"

    def save(self, *args, **kwargs):
        if self.fee_per_year and self.duration_years:
            self.total_fee = self.fee_per_year * self.duration_years
        if self.duration_years and not self.duration:
            self.duration = f'{self.duration_years} Years'
        super().save(*args, **kwargs)
