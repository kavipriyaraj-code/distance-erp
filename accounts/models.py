from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('counsellor', 'Counsellor'),
        ('accountant', 'Accountant'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='counsellor')
    phone = models.CharField(max_length=15, blank=True)
    is_active_user = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == 'admin'

    @property
    def is_counsellor_role(self):
        return self.role == 'counsellor'

    @property
    def is_accountant_role(self):
        return self.role == 'accountant'

    @property
    def is_admin_user(self):
        return self.role == 'admin'

    @property
    def is_super_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def is_accounts(self):
        return self.role == 'accountant'


class StaffBankDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bank_details')
    account_holder_name = models.CharField(max_length=150, blank=True)
    bank_name = models.CharField(max_length=150, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    ifsc_code = models.CharField(max_length=15, blank=True)
    branch_name = models.CharField(max_length=150, blank=True)
    upi_id = models.CharField(max_length=50, blank=True)
    pan_number = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bank Details - {self.user.get_full_name() or self.user.username}"
