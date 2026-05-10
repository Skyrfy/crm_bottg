from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Question, QuestionTopic, StudentInterviewProfile


@admin.register(QuestionTopic)
class QuestionTopicAdmin(admin.ModelAdmin):
    list_display = ('language', 'topic')
    list_filter = ('language',)
    search_fields = ('topic',)


@admin.register(Question)
class QuestionAdmin(SimpleHistoryAdmin):
    list_display = ('title_short', 'company', 'topic')
    list_filter = ('topic__language', 'company')
    search_fields = ('title', 'company', 'answer')
    autocomplete_fields = ('topic',)

    def title_short(self, obj):
        return obj.title[:80] + ('...' if len(obj.title) > 80 else '')
    title_short.short_description = 'Вопрос'


@admin.register(StudentInterviewProfile)
class StudentInterviewProfileAdmin(admin.ModelAdmin):
    list_display = ('student', 'solved_count', 'created_at')
    raw_id_fields = ('student',)
    filter_horizontal = ('solved_questions',)

    def solved_count(self, obj):
        return obj.solved_questions.count()
    solved_count.short_description = 'Решено'