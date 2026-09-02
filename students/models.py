from django.db import models

class Student(models.Model):
    STATUS_CHOICES = [
        ('prospect', 'Prospect'), ('applicant', 'Applicant'),
        ('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ]
    student_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=200)
    photo = models.ImageField(upload_to='students/photos/', blank=True, null=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True)
    mobile = models.CharField(max_length=15)
    whatsapp = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    aadhaar_number = models.CharField(max_length=12, blank=True)
    emergency_contact = models.CharField(max_length=15, blank=True)
    university = models.ForeignKey('universities.University', on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True)
    registration_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='prospect')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student_id} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.student_id:
            last = Student.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.student_id = f"STU-{num:06d}"
        super().save(*args, **kwargs)
