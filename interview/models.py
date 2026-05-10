from django.db import models
from simple_history.models import HistoricalRecords

from bot.models import Student


class ProgrammingLanguage(models.TextChoices):
    """
    Языки программирования. Полный список из проекта-тренажёра.
    Совпадение с группами ученика (cpp/python/rust/blockchain) проверяется
    в логике, а не на уровне БД — потому что ученик из группы Python может
    хотеть тренировать вопросы по JavaScript для расширения кругозора.
    """
    PYTHON = 'Python'
    JAVA = 'Java'
    CPLUSPLUS = 'C++'
    JAVASCRIPT = 'JavaScript'
    RUBY = 'Ruby'
    SWIFT = 'Swift'
    GO = 'Go'
    RUST = 'Rust'
    PHP = 'PHP'
    CSHARP = 'C#'


class QuestionTopic(models.Model):
    language = models.CharField(
        max_length=64, choices=ProgrammingLanguage.choices,
        verbose_name='Язык',
    )
    topic = models.CharField(max_length=256, verbose_name='Тема')

    class Meta:
        db_table = 'question_topic'
        verbose_name = 'Тема вопросов'
        verbose_name_plural = 'Темы вопросов'
        unique_together = ('language', 'topic')

    def __str__(self):
        return f'{self.language} · {self.topic}'


class Question(models.Model):
    title = models.CharField(max_length=1024, verbose_name='Вопрос')
    company = models.CharField(max_length=100, verbose_name='Компания')
    topic = models.ForeignKey(
        QuestionTopic, on_delete=models.CASCADE,
        related_name='questions',
    )
    answer = models.TextField(verbose_name='Эталонный ответ')

    history = HistoricalRecords()

    class Meta:
        unique_together = ('title', 'company')
        db_table = 'question'
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    def __str__(self):
        return f'{self.title[:60]}... ({self.company})'


class StudentInterviewProfile(models.Model):
    """
    Профиль ученика в системе тренажёра.
    Связан с моделью Student твоего проекта; решённые вопросы — M2M.
    
    Это аналог UserProfile из исходного проекта, но привязан к Student
    вместо стандартного User. Поле premium убрано — в нашей системе
    доступ управляется ментором через распределение в группу.
    """
    student = models.OneToOneField(
        Student, on_delete=models.CASCADE,
        related_name='interview_profile',
        verbose_name='Ученик',
    )
    solved_questions = models.ManyToManyField(
        Question, blank=True,
        related_name='solved_by',
        verbose_name='Решённые вопросы',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Профиль тренажёра'
        verbose_name_plural = 'Профили тренажёра'

    def __str__(self):
        return f'Профиль тренажёра: {self.student.full_name}'