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