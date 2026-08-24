from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'is_active_user', 'date_joined']
    list_filter = ['role', 'is_active_user']
    fieldsets = UserAdmin.fieldsets + (
        ('Additional', {'fields': ('role', 'phone', 'is_active_user')}),
    )
