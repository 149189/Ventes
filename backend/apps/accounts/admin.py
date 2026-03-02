from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_verified', 'is_active', 'created_at')
    list_filter = ('role', 'is_verified', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra', {'fields': ('role', 'phone', 'is_verified')}),
    )
