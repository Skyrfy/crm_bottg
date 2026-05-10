from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from bot.auth import MentorUser
from bot.models import Student

from .models import Question, QuestionTopic, StudentInterviewProfile
from .serializers import (
    QuestionSerializer,
    StudentInterviewProgressSerializer,
)


class QuestionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class QuestionListAPIView(generics.ListAPIView):
    """
    GET /api/interview/questions/?language=Python&topic=Декораторы&company=Yandex
    Возвращает список вопросов с пагинацией. Любой авторизованный пользователь
    (ученик или ментор) может получить список.
    """
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = QuestionPagination

    def get_queryset(self):
        queryset = Question.objects.all().select_related('topic')
        language = self.request.query_params.get('language')
        topic = self.request.query_params.get('topic')
        company = self.request.query_params.get('company')

        if language:
            queryset = queryset.filter(topic__language__iexact=language)
        if topic:
            queryset = queryset.filter(topic__topic__iexact=topic)
        if company:
            queryset = queryset.filter(company__iexact=company)
        return queryset.order_by('id')


class QuestionFiltersAPIView(APIView):
    """
    GET /api/interview/filters/
    Возвращает все доступные значения для фильтров: языки, темы, компании.
    Используется фронтом для построения селекторов.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        languages = list(
            QuestionTopic.objects
            .values_list('language', flat=True)
            .distinct().order_by('language')
        )
        topics = list(
            QuestionTopic.objects
            .values_list('topic', flat=True)
            .distinct().order_by('topic')
        )
        companies = list(
            Question.objects
            .values_list('company', flat=True)
            .distinct().order_by('company')
        )
        return Response({
            'languages': languages,
            'topics': topics,
            'companies': companies,
        })


class StudentProgressAPIView(APIView):
    """
    GET  /api/interview/progress/        — мой прогресс (текущий ученик)
    POST /api/interview/progress/        — обновить отметки решённых вопросов
    
    Ментор сюда не ходит — у него нет «своего прогресса». Если зайдёт ментор,
    отдадим 403 с понятным сообщением.
    """
    permission_classes = [IsAuthenticated]

    def _get_or_create_profile(self, student: Student) -> StudentInterviewProfile:
        profile, _ = StudentInterviewProfile.objects.get_or_create(student=student)
        return profile

    def get(self, request):
        if isinstance(request.user, MentorUser):
            return Response(
                {'detail': 'У ментора нет личного прогресса в тренажёре.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        profile = self._get_or_create_profile(request.user)
        serializer = StudentInterviewProgressSerializer(profile)
        return Response(serializer.data)

    def post(self, request):
        """
        Принимает: {"questions": [{"question_id": 1, "is_solved": true}, ...]}
        Помечает вопросы как решённые/нерешённые в одной транзакции.
        """
        if isinstance(request.user, MentorUser):
            return Response(
                {'detail': 'Ментор не может отмечать вопросы.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        questions_data = request.data.get('questions', [])
        if not questions_data:
            return Response(
                {'error': 'Не передано ни одного вопроса.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = self._get_or_create_profile(request.user)

        # Сначала собираем валидные id, потом одним запросом проверяем существование
        to_add, to_remove = [], []
        errors = []
        for item in questions_data:
            qid = item.get('question_id')
            is_solved = item.get('is_solved')
            if qid is None or is_solved is None:
                errors.append(f'Некорректный элемент: {item}')
                continue
            (to_add if is_solved else to_remove).append(qid)

        # Проверяем что все запрошенные вопросы существуют
        all_ids = to_add + to_remove
        existing_ids = set(
            Question.objects.filter(id__in=all_ids).values_list('id', flat=True)
        )
        missing = set(all_ids) - existing_ids
        if missing:
            errors.append(f'Не найдены вопросы: {sorted(missing)}')

        # Применяем изменения только для существующих вопросов
        valid_to_add = [qid for qid in to_add if qid in existing_ids]
        valid_to_remove = [qid for qid in to_remove if qid in existing_ids]

        if valid_to_add:
            profile.solved_questions.add(*valid_to_add)
        if valid_to_remove:
            profile.solved_questions.remove(*valid_to_remove)

        return Response({
            'processed': len(valid_to_add) + len(valid_to_remove),
            'added': len(valid_to_add),
            'removed': len(valid_to_remove),
            'errors': errors,
        })