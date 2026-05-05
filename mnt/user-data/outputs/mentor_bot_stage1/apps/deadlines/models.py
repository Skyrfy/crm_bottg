from django.db import models
from apps.students.models import Student


class DeadlineStatus(models.TextChoices):
    PENDING = "pending", "Ожидает ответа"
    ANSWERED = "answered", "Ученик ответил"
    OVERDUE = "overdue", "Просрочен"
    CLOSED = "closed", "Закрыт"


class Deadline(models.Model):
    """Дедлайн, выставленный ментором ученику."""

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="deadlines",
        verbose_name="Ученик",
    )
    topic = models.CharField(max_length=256, verbose_name="Тема / задание")
    description = models.TextField(
        null=True, blank=True,
        verbose_name="Описание задания",
    )
    due_date = models.DateTimeField(verbose_name="Срок сдачи")
    status = models.CharField(
        max_length=20,
        choices=DeadlineStatus.choices,
        default=DeadlineStatus.PENDING,
        verbose_name="Статус",
    )

    # Уведомления
    student_notified = models.BooleanField(
        default=False,
        verbose_name="Ученик уведомлён",
    )
    mentor_notified_overdue = models.BooleanField(
        default=False,
        verbose_name="Ментор уведомлён о просрочке",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлён")

    class Meta:
        verbose_name = "Дедлайн"
        verbose_name_plural = "Дедлайны"
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.student.full_name} — {self.topic} (до {self.due_date:%d.%m.%Y})"

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.due_date < timezone.now() and self.status == DeadlineStatus.PENDING


class DeadlineAnswer(models.Model):
    """Ответ ученика на дедлайн."""

    deadline = models.OneToOneField(
        Deadline,
        on_delete=models.CASCADE,
        related_name="answer",
        verbose_name="Дедлайн",
    )
    text = models.TextField(null=True, blank=True, verbose_name="Текст ответа")

    # Если ученик прислал файл/ссылку — сохраняем file_id из Telegram
    telegram_file_id = models.CharField(
        max_length=256,
        null=True, blank=True,
        verbose_name="Telegram file_id (документ/фото)",
    )
    file_type = models.CharField(
        max_length=20,
        null=True, blank=True,
        verbose_name="Тип файла (document/photo)",
    )

    # Флаг — ментор уже получил уведомление об этом ответе
    mentor_notified = models.BooleanField(default=False, verbose_name="Ментор уведомлён")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата ответа")

    class Meta:
        verbose_name = "Ответ на дедлайн"
        verbose_name_plural = "Ответы на дедлайны"

    def __str__(self):
        return f"Ответ: {self.deadline}"
