from django.contrib import admin
from .models import Student, Deadline, DeadlineAssignment, Submission


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'username', 'group', 'is_active', 'created_at')
    list_filter = ('group', 'is_active')
    search_fields = ('full_name', 'username', 'telegram_id')
    list_editable = ('group',)


class AssignmentInline(admin.TabularInline):
    model = DeadlineAssignment
    extra = 0


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ('topic', 'due_at', 'created_at')
    search_fields = ('topic', 'description')
    inlines = [AssignmentInline]


@admin.register(DeadlineAssignment)
class DeadlineAssignmentAdmin(admin.ModelAdmin):
    list_display = ('deadline', 'student', 'status', 'overdue_notified')
    list_filter = ('status',)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'content_type', 'submitted_at')
    list_filter = ('content_type',)
    readonly_fields = ('submitted_at',)