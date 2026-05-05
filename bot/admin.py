from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'username', 'group', 'is_active', 'created_at')
    list_filter = ('group', 'is_active')
    search_fields = ('full_name', 'username', 'telegram_id')
    list_editable = ('group',)