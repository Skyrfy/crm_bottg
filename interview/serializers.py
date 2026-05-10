from rest_framework import serializers
from .models import Question, QuestionTopic, StudentInterviewProfile


class QuestionTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionTopic
        fields = ('id', 'language', 'topic')


class QuestionSerializer(serializers.ModelSerializer):
    """Полная карточка вопроса. Используется в списке и в карточке."""
    language = serializers.CharField(source='topic.language', read_only=True)
    topic_name = serializers.CharField(source='topic.topic', read_only=True)

    class Meta:
        model = Question
        fields = (
            'id', 'title', 'company', 'answer',
            'language', 'topic_name', 'topic',
        )


class StudentInterviewProgressSerializer(serializers.ModelSerializer):
    """Прогресс ученика: список ID решённых вопросов + счётчик."""
    solved_question_ids = serializers.SerializerMethodField()
    solved_count = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = StudentInterviewProfile
        fields = ('id', 'student_name', 'solved_count', 'solved_question_ids')

    def get_solved_question_ids(self, obj):
        return list(obj.solved_questions.values_list('id', flat=True))

    def get_solved_count(self, obj):
        return obj.solved_questions.count()