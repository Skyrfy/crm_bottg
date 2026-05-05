"""Аутентификация по Telegram WebApp initData."""

import hashlib
import hmac
import os
import time
from urllib.parse import parse_qsl

from rest_framework import authentication, exceptions

from .models import Student

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
MENTOR_TELEGRAM_ID = int(os.getenv('MENTOR_TELEGRAM_ID', '0'))

# Сколько секунд считаем initData валидным (защита от replay)
INIT_DATA_MAX_AGE = 60 * 60 * 24  # 24 часа


class MentorUser:
    """Псевдо-пользователь для ментора. Не сохраняется в БД."""

    def __init__(self, telegram_id: int, full_name: str = '', username: str = ''):
        self.telegram_id = telegram_id
        self.full_name = full_name
        self.username = username
        self.is_mentor = True
        self.pk = f'mentor:{telegram_id}'  # уникальный идентификатор для DRF

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return f'Mentor ({self.full_name})'


def _verify_init_data(init_data: str, bot_token: str) -> dict:
    """
    Проверяет подпись Telegram WebApp initData и возвращает словарь полей.
    Бросает ValueError при невалидной подписи или просроченных данных.
    """
    if not init_data:
        raise ValueError('initData отсутствует')

    # Парсим строку как query string
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop('hash', None)
    if not received_hash:
        raise ValueError('hash отсутствует в initData')

    # Собираем data_check_string: все пары key=value, отсортированные по ключу, через \n
    data_check_string = '\n'.join(
        f'{k}={v}' for k, v in sorted(parsed.items())
    )

    # Секретный ключ = HMAC-SHA256(bot_token, key="WebAppData")
    secret_key = hmac.new(
        b'WebAppData', bot_token.encode(), hashlib.sha256
    ).digest()

    # Считаем ожидаемый хэш
    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError('Подпись initData невалидна')

    # Проверка возраста данных
    auth_date = int(parsed.get('auth_date', 0))
    if time.time() - auth_date > INIT_DATA_MAX_AGE:
        raise ValueError('initData устарел')

    return parsed


class TelegramWebAppAuthentication(authentication.BaseAuthentication):
    """
    DRF-аутентификация по заголовку X-Telegram-Init-Data.
    
    Если telegram_id из initData совпадает с MENTOR_TELEGRAM_ID — request.user становится MentorUser.
    Иначе — ищем Student по telegram_id; если не нашли — 403.
    """

    def authenticate(self, request):
        init_data = request.META.get('HTTP_X_TELEGRAM_INIT_DATA')
        if not init_data:
            return None  # пусть DRF выдаст 401 через permission_classes

        try:
            parsed = _verify_init_data(init_data, BOT_TOKEN)
        except ValueError as e:
            raise exceptions.AuthenticationFailed(str(e))

        # Достаём пользователя
        import json
        user_data = json.loads(parsed.get('user', '{}'))
        telegram_id = user_data.get('id')
        if not telegram_id:
            raise exceptions.AuthenticationFailed('user.id отсутствует в initData')

        # Ментор?
        if telegram_id == MENTOR_TELEGRAM_ID:
            mentor = MentorUser(
                telegram_id=telegram_id,
                full_name=f'{user_data.get("first_name", "")} {user_data.get("last_name", "")}'.strip(),
                username=user_data.get('username', ''),
            )
            return (mentor, init_data)

        # Ученик
        try:
            student = Student.objects.get(telegram_id=telegram_id, is_active=True)
        except Student.DoesNotExist:
            raise exceptions.AuthenticationFailed(
                'Ученик не зарегистрирован. Сначала напишите боту /start.'
            )

        return (student, init_data)