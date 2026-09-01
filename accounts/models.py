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
