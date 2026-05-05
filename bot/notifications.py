"""Отправка уведомлений в Telegram из Django (вне процесса бота)."""

import asyncio
import logging
import os

from aiogram import Bot
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '')


async def _send(chat_id: int, text: str, parse_mode: str = 'HTML'):
    """Однократная отправка сообщения. Создаёт временный объект Bot."""
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(chat_id, text, parse_mode=parse_mode)
    finally:
        await bot.session.close()

# async_to_sync нужен потому, что aiogram умеет только асинхронно отправлять, а DRF-вьюхи у нас синхронные. 
# Альтернатива — переписать вьюхи на async, но это лишний шум для одного запроса.
def send_telegram_message(chat_id: int, text: str) -> bool:
    """Синхронная обёртка. Возвращает True при успехе."""
    if not BOT_TOKEN:
        logger.warning('BOT_TOKEN не задан, пропускаем уведомление')
        return False
    try:
        async_to_sync(_send)(chat_id, text)
        return True
    except Exception as e:
        logger.warning('Не удалось отправить сообщение %s: %s', chat_id, e)
        return False


def notify_new_deadline(deadline, assignments):
    """Шлёт каждому назначенному ученику уведомление о новом дедлайне."""
    due_str = deadline.due_at.strftime('%d.%m.%Y %H:%M')
    description = f'\n\n{deadline.description}' if deadline.description else ''
    text = (
        f'📌 <b>Новый дедлайн</b>\n\n'
        f'<b>Тема:</b> {deadline.topic}\n'
        f'<b>Срок:</b> до {due_str}'
        f'{description}\n\n'
        f'Откройте кабинет, чтобы отправить ответ.'
    )
    for assignment in assignments:
        send_telegram_message(assignment.student.telegram_id, text)


def notify_mentor_about_submission(assignment, mentor_telegram_id):
    """Уведомляет ментора о новом ответе ученика."""
    text = (
        f'📥 <b>Новый ответ</b>\n\n'
        f'Ученик: {assignment.student.full_name}\n'
        f'Тема: {assignment.deadline.topic}\n\n'
        f'Откройте кабинет для проверки.'
    )
    send_telegram_message(mentor_telegram_id, text)


def notify_student_about_review(assignment, status: str, comment: str = ''):
    """Уведомляет ученика о результате ревью."""
    if status == 'approved':
        text = (
            f'✅ <b>Работа принята</b>\n\n'
            f'Тема: {assignment.deadline.topic}'
        )
    elif status == 'rejected':
        text = (
            f'❌ <b>Работа отклонена</b>\n\n'
            f'Тема: {assignment.deadline.topic}\n\n'
            f'<b>Комментарий ментора:</b>\n{comment or "(без комментария)"}'
        )
    else:
        return
    send_telegram_message(assignment.student.telegram_id, text)