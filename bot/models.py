from django.db import models


class Student(models.Model):
    """Ученик ментора. Регистрируется при первом /start в боте."""

    GROUP_CHOICES = [
        ('cpp', 'C++'),
        ('python', 'Python'),
        ('rust', 'Rust'),
        ('blockchain', 'Blockchain'),
    ]

    telegram_id = models.BigIntegerField(unique=True, verbose_name='Telegram ID')
    username = models.CharField(max_length=64, blank=True, verbose_name='Username')
    full_name = models.CharField(max_length=200, verbose_name='Имя')
    group = models.CharField(
        max_length=20,
        choices=GROUP_CHOICES,
        null=True,
        blank=True,
        verbose_name='Группа',
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлен')

    class Meta:
        verbose_name = 'Ученик'
        verbose_name_plural = 'Ученики'
        ordering = ['-created_at']

    def __str__(self):
        group_label = self.get_group_display() if self.group else 'не распределён'
        return f'{self.full_name} ({group_label})'

    # Минимальный duck-typing под Django auth — чтобы DRF мог считать студента "пользователем"
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class Deadline(models.Model):
    """Задание с дедлайном. Может быть выдано одному или нескольким ученикам."""

    topic = models.CharField(max_length=200, verbose_name='Тема')
    description = models.TextField(blank=True, verbose_name='Описание')
    due_at = models.DateTimeField(verbose_name='Срок сдачи')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Дедлайн'
        verbose_name_plural = 'Дедлайны'
        ordering = ['-due_at']

    def __str__(self):
        return f'{self.topic} (до {self.due_at:%d.%m.%Y %H:%M})'


class DeadlineAssignment(models.Model):
    """Связка дедлайна с конкретным учеником. У каждого ученика свой статус."""

    STATUS_CHOICES = [
        ('pending', 'Ожидает выполнения'),
        ('submitted', 'Отправлен на проверку'),
        ('approved', 'Принят'),
        ('rejected', 'Отклонён, нужна доработка'),
        ('overdue', 'Просрочен'),
    ]

    deadline = models.ForeignKey(
        Deadline, related_name='assignments', on_delete=models.CASCADE
    )
    student = models.ForeignKey(
        Student, related_name='assignments', on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    overdue_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Назначение дедлайна'
        verbose_name_plural = 'Назначения дедлайнов'
        unique_together = ('deadline', 'student')

    def __str__(self):
        return f'{self.student.full_name} — {self.deadline.topic} [{self.get_status_display()}]'


class Submission(models.Model):
    """Сообщение в треде дедлайна. Может быть от ученика (ответ) или от ментора (комментарий)."""

    AUTHOR_CHOICES = [
        ('student', 'Ученик'),
        ('mentor', 'Ментор'),
    ]

    CONTENT_TYPE_CHOICES = [
        ('text', 'Текст'),
        ('document', 'Документ'),
        ('photo', 'Фото'),
    ]

    assignment = models.ForeignKey(
        DeadlineAssignment, related_name='submissions', on_delete=models.CASCADE
    )
    author = models.CharField(
        max_length=10, choices=AUTHOR_CHOICES, default='student',
        verbose_name='Автор сообщения',
    )
    text = models.TextField(blank=True)
    file_id = models.CharField(max_length=255, blank=True, verbose_name='Telegram file_id')
    file_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(
        max_length=20, choices=CONTENT_TYPE_CHOICES, default='text'
    )
    mentor_comment = models.TextField(blank=True, verbose_name='Комментарий ментора (legacy, при reject)')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение в треде'
        verbose_name_plural = 'Сообщения в тредах'
        ordering = ['submitted_at']  # хронологический порядок ленты

    def __str__(self):
        return f'{self.get_author_display()} · {self.assignment.student.full_name} · {self.submitted_at:%d.%m %H:%M}'