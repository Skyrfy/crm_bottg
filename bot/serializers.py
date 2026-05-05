from rest_framework import serializers
from .models import Student, Deadline, DeadlineAssignment, Submission


class StudentSerializer(serializers.ModelSerializer):
    group_label = serializers.CharField(source='get_group_display', read_only=True)

    class Meta:
        model = Student
        fields = ('id', 'telegram_id', 'username', 'full_name', 'group', 'group_label')


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = (
            'id', 'text', 'file_id', 'file_name', 'content_type',
            'mentor_comment', 'submitted_at',
        )
        read_only_fields = ('submitted_at',)


class DeadlineAssignmentSerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    submissions = SubmissionSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    last_submission = serializers.SerializerMethodField()

    class Meta:
        model = DeadlineAssignment
        fields = (
            'id', 'student', 'status', 'status_label',
            'submissions', 'last_submission', 'created_at',
        )

    def get_last_submission(self, obj):
        last = obj.submissions.first()  # ordering = ['-submitted_at']
        return SubmissionSerializer(last).data if last else None


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