from django.db import models
from django.conf import settings
from universities.models import University
from courses.models import Course
from students.models import Student

class Enquiry(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'), ('contacted', 'Contacted'), ('follow_up', 'Follow-up'),
        ('interested', 'Interested'), ('converted', 'Converted'), ('lost', 'Lost'),
    ]
    SOURCE_CHOICES = [
        ('whatsapp', 'WhatsApp'), ('phone', 'Phone'), ('website', 'Website'),
        ('walk_in', 'Walk-in'), ('referral', 'Referral'), ('advertisement', 'Advertisement'),
        ('social_media', 'Social Media'), ('other', 'Other'),
    ]
    enquiry_number = models.CharField(max_length=20, unique=True)
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='enquiries')
    student_name = models.CharField(max_length=200, blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    whatsapp = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='other')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='enquiries')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    next_followup = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.enquiry_number} - {self.student_name}"

    def save(self, *args, **kwargs):
        if not self.enquiry_number:
            from django.db.models import Max
            last_num = Enquiry.objects.aggregate(
                max_num=Max('enquiry_number')
            )['max_num']
            if last_num:
                try:
                    num = int(last_num.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.enquiry_number = f"ENQ-{num:06d}"
        super().save(*args, **kwargs)


class FollowUp(models.Model):
    enquiry = models.ForeignKey(Enquiry, on_delete=models.CASCADE, related_name='followups')
    counsellor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='followups')
    notes = models.TextField()
    next_followup = models.DateField(null=True, blank=True)
    new_status = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Follow-up: {self.enquiry.enquiry_number}"
