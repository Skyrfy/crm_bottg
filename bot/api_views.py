import os

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import MentorUser
from .models import Student, Deadline, DeadlineAssignment, Submission
from .notifications import (
    notify_new_deadline,
    notify_mentor_about_submission,
    notify_student_about_review,
    notify_student_about_mentor_message,
)
from .serializers import (
    StudentSerializer,
    DeadlineListSerializer,
    DeadlineDetailSerializer,
    DeadlineCreateSerializer,
    DeadlineAssignmentSerializer,
    SubmissionSerializer,
)

MENTOR_TELEGRAM_ID = int(os.getenv('MENTOR_TELEGRAM_ID', '0'))


def is_mentor(user) -> bool:
    return isinstance(user, MentorUser)


class IsMentorPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and is_mentor(request.user)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if is_mentor(user):
            return Response({
                'role': 'mentor',
                'telegram_id': user.telegram_id,
                'full_name': user.full_name,
                'username': user.username,
            })
        return Response({
            'role': 'student',
            'id': user.id,
            'telegram_id': user.telegram_id,
            'full_name': user.full_name,
            'username': user.username,
            'group': user.group,
            'group_label': user.get_group_display() if user.group else None,
        })


class StudentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = StudentSerializer
    permission_classes = [IsMentorPermission]
    queryset = Student.objects.filter(is_active=True)


class DeadlineViewSet(viewsets.ModelViewSet):
    queryset = Deadline.objects.all()

    def get_queryset(self):
        user = self.request.user
        if is_mentor(user):
            return Deadline.objects.all().order_by('-due_at')
        return Deadline.objects.filter(assignments__student=user).distinct().order_by('-due_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return DeadlineListSerializer
        if self.action == 'create':
            return DeadlineCreateSerializer
        return DeadlineDetailSerializer

    def get_permissions(self):
        if self.action in ('create', 'destroy'):
            return [IsMentorPermission()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        deadline = serializer.save()
        # Отправляем уведомления всем назначенным ученикам
        assignments = deadline.assignments.select_related('student').all()
        notify_new_deadline(deadline, assignments)


class AssignmentViewSet(viewsets.GenericViewSet):
    queryset = DeadlineAssignment.objects.all()
    serializer_class = DeadlineAssignmentSerializer

    def get_queryset(self):
        user = self.request.user
        if is_mentor(user):
            return DeadlineAssignment.objects.all()
        return DeadlineAssignment.objects.filter(student=user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Ученик отправляет ответ."""
        assignment = self.get_object()
        if assignment.student != request.user:
            return Response({'detail': 'Нельзя отвечать за другого ученика'}, status=403)
        if assignment.status == 'approved':
            return Response(
                {'detail': 'Этот дедлайн уже принят, изменения невозможны.'},
                status=400,
            )

        serializer = SubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save(assignment=assignment, author='student')

        assignment.status = 'submitted'
        assignment.save(update_fields=['status'])

        if MENTOR_TELEGRAM_ID:
            notify_mentor_about_submission(assignment, MENTOR_TELEGRAM_ID, submission)

        return Response(
            SubmissionSerializer(submission).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], permission_classes=[IsMentorPermission])
    def comment(self, request, pk=None):
        """Ментор пишет комментарий ученику в треде дедлайна."""
        assignment = self.get_object()

        serializer = SubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = serializer.save(assignment=assignment, author='mentor')

        notify_student_about_mentor_message(assignment, submission)

        return Response(
            SubmissionSerializer(submission).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], permission_classes=[IsMentorPermission])
    def approve(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = 'approved'
        assignment.save(update_fields=['status'])
        notify_student_about_review(assignment, 'approved')
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsMentorPermission])
    def reject(self, request, pk=None):
        """Отклонение работы. Принимает comment — он становится сообщением в треде."""
        assignment = self.get_object()
        comment_text = (request.data.get('comment') or '').strip()

        assignment.status = 'rejected'
        assignment.save(update_fields=['status'])

        # Сохраняем комментарий как сообщение от ментора
        if comment_text:
            Submission.objects.create(
                assignment=assignment,
                author='mentor',
                text=comment_text,
            )

        notify_student_about_review(assignment, 'rejected', comment_text)
        return Response({'status': 'rejected', 'comment': comment_text})

    @action(detail=True, methods=['post'], permission_classes=[IsMentorPermission])
    def approve(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = 'approved'
        assignment.save(update_fields=['status'])
        notify_student_about_review(assignment, 'approved')
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsMentorPermission])
    def reject(self, request, pk=None):
        assignment = self.get_object()
        comment = request.data.get('comment', '')
        assignment.status = 'rejected'
        assignment.save(update_fields=['status'])
        last = assignment.submissions.first()
        if last:
            last.mentor_comment = comment
            last.save(update_fields=['mentor_comment'])
        notify_student_about_review(assignment, 'rejected', comment)
        return Response({'status': 'rejected', 'comment': comment})