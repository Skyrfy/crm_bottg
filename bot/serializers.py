from rest_framework import serializers
from .models import Student, Deadline, DeadlineAssignment, Submission


class StudentSerializer(serializers.ModelSerializer):
    group_label = serializers.CharField(source='get_group_display', read_only=True)

    class Meta:
        model = Student
        fields = ('id', 'telegram_id', 'username', 'full_name', 'group', 'group_label')


class SubmissionSerializer(serializers.ModelSerializer):
    author_label = serializers.CharField(source='get_author_display', read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = ('id', 'author', 'author_label', 'author_name', 'text', 'submitted_at')
        read_only_fields = ('submitted_at', 'author', 'author_label', 'author_name')

    def get_author_name(self, obj):
        if obj.author == 'mentor':
            return 'Ментор'
        return obj.assignment.student.full_name

    def validate_text(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Сообщение не может быть пустым.')
        if len(value) > 4000:
            raise serializers.ValidationError('Сообщение слишком длинное (максимум 4000 символов).')
        return value


class DeadlineAssignmentSerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    submissions = SubmissionSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DeadlineAssignment
        fields = (
            'id', 'student', 'status', 'status_label',
            'submissions', 'created_at',
        )


class DeadlineListSerializer(serializers.ModelSerializer):
    """Краткое представление для списка."""
    assignments_count = serializers.IntegerField(source='assignments.count', read_only=True)

    class Meta:
        model = Deadline
        fields = ('id', 'topic', 'due_at', 'assignments_count', 'created_at')


class DeadlineDetailSerializer(serializers.ModelSerializer):
    """Полная карточка дедлайна со списком ассигнментов."""
    assignments = DeadlineAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Deadline
        fields = ('id', 'topic', 'description', 'due_at', 'created_at', 'assignments')


class DeadlineCreateSerializer(serializers.ModelSerializer):
    """Создание дедлайна: помимо самих полей, ментор передаёт список student_ids."""
    student_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        min_length=1,
    )

    class Meta:
        model = Deadline
        fields = ('id', 'topic', 'description', 'due_at', 'student_ids')

    def create(self, validated_data):
        student_ids = validated_data.pop('student_ids')
        deadline = Deadline.objects.create(**validated_data)

        students = Student.objects.filter(id__in=student_ids, is_active=True)
        DeadlineAssignment.objects.bulk_create([
            DeadlineAssignment(deadline=deadline, student=s) for s in students
        ])
        return deadline