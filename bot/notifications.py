"""Отправка уведомлений в Telegram из Django (вне процесса бота)."""

import asyncio
import logging
import os

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
BOT_USERNAME = os.getenv('BOT_USERNAME', '')
WEBAPP_SHORT_NAME = os.getenv('WEBAPP_SHORT_NAME', '')


def _build_deep_link(deadline_id: int) -> str | None:
    """
    Собирает t.me-ссылку на мини-апп с параметром startapp.
    Возвращает None, если BOT_USERNAME не задан (тогда кнопку не делаем).
    """
    if not BOT_USERNAME:
        return None
    if WEBAPP_SHORT_NAME:
        return f'https://t.me/{BOT_USERNAME}/{WEBAPP_SHORT_NAME}?startapp=deadline_{deadline_id}'
    return f'https://t.me/{BOT_USERNAME}?startapp=deadline_{deadline_id}'


def _open_button(deadline_id: int) -> InlineKeyboardMarkup | None:
    url = _build_deep_link(deadline_id)
    if not url:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📂 Открыть в кабинете', url=url)],
    ])


async def _send(chat_id: int, text: str, reply_markup=None):
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id, text, parse_mode='HTML', reply_markup=reply_markup,
        )
    finally:
        await bot.session.close()


def send_telegram_message(chat_id: int, text: str, reply_markup=None) -> bool:
    if not BOT_TOKEN:
        logger.warning('BOT_TOKEN не задан, пропускаем уведомление')
        return False
    try:
        async_to_sync(_send)(chat_id, text, reply_markup)
        return True
    except Exception as e:
        logger.warning('Не удалось отправить сообщение %s: %s', chat_id, e)
        return False


def _escape(text: str) -> str:
    return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def _preview(text: str, limit: int = 500) -> str:
    text = text or ''
    preview = text[:limit]
    if len(text) > limit:
        preview += '…'
    return _escape(preview)


# ---------- Уведомления ----------

def notify_new_deadline(deadline, assignments):
    """Каждому назначенному ученику — сообщение о новом дедлайне."""
    due_str = deadline.due_at.strftime('%d.%m.%Y %H:%M')
    description = f'\n\n{_escape(deadline.description)}' if deadline.description else ''
    text = (
        f'📌 <b>Новый дедлайн</b>\n\n'
        f'<b>Тема:</b> {_escape(deadline.topic)}\n'
        f'<b>Срок:</b> до {due_str}'
        f'{description}'
    )
    markup = _open_button(deadline.id)
    for assignment in assignments:
        send_telegram_message(assignment.student.telegram_id, text, markup)


def notify_mentor_about_submission(assignment, mentor_telegram_id, submission=None):
    """Ментору — о новом ответе ученика, с превью."""
    text_preview = ''
    if submission and submission.text:
        text_preview = f'\n\n<blockquote>{_preview(submission.text)}</blockquote>'
    text = (
        f'📥 <b>Новый ответ на проверку</b>\n\n'
        f'Ученик: {_escape(assignment.student.full_name)}\n'
        f'Тема: {_escape(assignment.deadline.topic)}'
        f'{text_preview}'
    )
    send_telegram_message(
        mentor_telegram_id, text, _open_button(assignment.deadline.id),
    )


def notify_student_about_mentor_message(assignment, submission):
    """Ученику — о новом комментарии ментора в треде."""
    text = (
        f'💬 <b>Сообщение от ментора</b>\n\n'
        f'Тема: {_escape(assignment.deadline.topic)}\n\n'
        f'<blockquote>{_preview(submission.text)}</blockquote>'
    )
    send_telegram_message(
        assignment.student.telegram_id, text, _open_button(assignment.deadline.id),
    )


def notify_student_about_review(assignment, status: str, comment: str = ''):
    """Ученику — о результате ревью."""
    if status == 'approved':
        text = (
            f'✅ <b>Работа принята</b>\n\n'
            f'Тема: {_escape(assignment.deadline.topic)}'
        )
    elif status == 'rejected':
        comment_block = f'\n\n<blockquote>{_preview(comment)}</blockquote>' if comment else ''
        text = (
            f'❌ <b>Работа отклонена</b>\n\n'
            f'Тема: {_escape(assignment.deadline.topic)}'
            f'{comment_block}\n\n'
            f'Откройте кабинет, чтобы доработать и отправить новый ответ.'
        )
    else:
        return
    send_telegram_message(
        assignment.student.telegram_id, text, _open_button(assignment.deadline.id),
    )