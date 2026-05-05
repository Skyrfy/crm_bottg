from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .auth import MentorUser
from .models import Student, Deadline, DeadlineAssignment, Submission
from .serializers import (
    StudentSerializer,
    DeadlineListSerializer,
    DeadlineDetailSerializer,
    DeadlineCreateSerializer,
    DeadlineAssignmentSerializer,
    SubmissionSerializer,
)


def is_mentor(user) -> bool:
    return isinstance(user, MentorUser)


class IsMentorPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and is_mentor(request.user)


class StudentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Только ментор может видеть полный список учеников (для выбора при создании дедлайна)."""
    serializer_class = StudentSerializer
    permission_classes = [IsMentorPermission]
    queryset = Student.objects.filter(is_active=True)


class DeadlineViewSet(viewsets.ModelViewSet):
    """
    GET /api/deadlines/        — список (для ментора все, для ученика только его)
    POST /api/deadlines/       — создание (только ментор)
    GET /api/deadlines/{id}/   — детали
    DELETE /api/deadlines/{id}/ — удаление (только ментор)
    """
    queryset = Deadline.objects.all()

    def get_queryset(self):
        user = self.request.user
        if is_mentor(user):
            return Deadline.objects.all().order_by('-due_at')
        # Ученик видит только дедлайны, на которые он назначен
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


class AssignmentViewSet(viewsets.GenericViewSet):
    """
    Действия над конкретным assignment'ом — отправка ответа учеником, ревью ментором.
    """
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

        serializer = SubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(assignment=assignment)

        assignment.status = 'submitted'
        assignment.save(update_fields=['status'])

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsMentorPermission])
    def approve(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = 'approved'
        assignment.save(update_fields=['status'])
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'], permission_classes=[IsMentorPermission])
    def reject(self, request, pk=None):
        assignment = self.get_object()
        comment = request.data.get('comment', '')
        assignment.status = 'rejected'
        assignment.save(update_fields=['status'])
        # Сохраняем комментарий в последнем submission (если есть)
        last = assignment.submissions.first()
        if last:
            last.mentor_comment = comment
            last.save(update_fields=['mentor_comment'])
        return Response({'status': 'rejected', 'comment': comment})
    
from rest_framework.views import APIView


class MeView(APIView):
    """Возвращает информацию о текущем пользователе (ментор или ученик)."""
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