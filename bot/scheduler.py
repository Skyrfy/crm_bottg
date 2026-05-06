"""Планировщик автоматической обработки дедлайнов через APScheduler."""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from asgiref.sync import sync_to_async

from .models import Deadline, DeadlineAssignment

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Возвращает singleton-инстанс планировщика."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone='UTC')
    return _scheduler


# ---------- ORM-обёртки ----------

@sync_to_async
def _process_overdue_assignments(deadline_id: int):
    """
    Помечает просроченные assignment'ы и возвращает список словарей
    для отправки уведомлений (telegram_id, full_name, topic).
    """
    try:
        deadline = Deadline.objects.get(id=deadline_id)
    except Deadline.DoesNotExist:
        return []

    # Просрочены те, кто не отправил ответ — статус всё ещё pending
    overdue = list(
        DeadlineAssignment.objects
        .filter(deadline=deadline, status='pending', overdue_notified=False)
        .select_related('student')
    )

    notifications = []
    for assignment in overdue:
        notifications.append({
            'mentor_text': (
                f'⏰ <b>Просрочен дедлайн</b>\n\n'
                f'Ученик: {assignment.student.full_name}\n'
                f'Тема: {deadline.topic}\n'
                f'Срок был: {deadline.due_at.strftime("%d.%m.%Y %H:%M")}'
            ),
            'student_telegram_id': assignment.student.telegram_id,
            'student_text': (
                f'⏰ <b>Срок сдачи истёк</b>\n\n'
                f'Тема: {deadline.topic}\n\n'
                f'Вы можете всё ещё отправить ответ — он будет отмечен как просроченный, '
                f'но ментор сможет с вами связаться.'
            ),
        })

        assignment.status = 'overdue'
        assignment.overdue_notified = True
        assignment.save(update_fields=['status', 'overdue_notified'])

    return notifications


@sync_to_async
def _get_future_deadlines():
    """Возвращает дедлайны, у которых due_at ещё не наступил."""
    now = datetime.now(tz=timezone.utc)
    return list(
        Deadline.objects
        .filter(due_at__gt=now, assignments__status='pending')
        .distinct()
        .values('id', 'due_at')
    )


@sync_to_async
def _get_pending_overdue_deadlines():
    """
    Дедлайны, у которых due_at уже прошёл, но есть assignments в pending —
    значит, в простое мы их пропустили.
    """
    now = datetime.now(tz=timezone.utc)
    return list(
        Deadline.objects
        .filter(due_at__lte=now, assignments__status='pending')
        .distinct()
        .values('id', 'due_at')
    )

# ---------- Job'ы ----------

async def _send_telegram_async(chat_id: int, text: str):
    """Прямая асинхронная отправка — для использования внутри async-задач."""
    import os
    from aiogram import Bot

    bot_token = os.getenv('BOT_TOKEN', '')
    if not bot_token:
        return

    bot = Bot(token=bot_token)
    try:
        await bot.send_message(chat_id, text, parse_mode='HTML')
    except Exception as e:
        logger.warning('Не удалось отправить %s: %s', chat_id, e)
    finally:
        await bot.session.close()


async def overdue_job(deadline_id: int, mentor_telegram_id: int):
    """Выполняется в момент наступления due_at дедлайна."""
    logger.info('Обработка просрочки для дедлайна %s', deadline_id)
    notifications = await _process_overdue_assignments(deadline_id)

    for n in notifications:
        if mentor_telegram_id:
            await _send_telegram_async(mentor_telegram_id, n['mentor_text'])
        await _send_telegram_async(n['student_telegram_id'], n['student_text'])


# ---------- Регистрация задач ----------

def schedule_deadline_overdue(deadline: Deadline, mentor_telegram_id: int):
    """Регистрирует задачу обработки просрочки для конкретного дедлайна."""
    scheduler = get_scheduler()
    job_id = f'overdue:{deadline.id}'

    # Если такая задача уже есть — заменяем (на случай если due_at изменился)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # Если время дедлайна уже прошло — выполняем немедленно
    now = datetime.now(tz=timezone.utc)
    run_at = deadline.due_at if deadline.due_at > now else now

    scheduler.add_job(
        overdue_job,
        trigger=DateTrigger(run_date=run_at),
        args=[deadline.id, mentor_telegram_id],
        id=job_id,
        replace_existing=True,
    )
    logger.info('Запланирована обработка просрочки %s на %s', job_id, run_at)


async def restore_jobs_from_db(mentor_telegram_id: int):
    """При старте бота: 
    1) обрабатывает дедлайны, чьи сроки истекли в простое;
    2) регистрирует задачи на будущие дедлайны.
    """
    scheduler = get_scheduler()

    # 1. Пропущенные за время простоя — обрабатываем сразу
    missed = await _get_pending_overdue_deadlines()
    for d in missed:
        await overdue_job(d['id'], mentor_telegram_id)
    if missed:
        logger.info('Обработано %d пропущенных дедлайнов', len(missed))

    # 2. Будущие — планируем
    future = await _get_future_deadlines()
    for d in future:
        job_id = f'overdue:{d["id"]}'
        scheduler.add_job(
            overdue_job,
            trigger=DateTrigger(run_date=d['due_at']),
            args=[d['id'], mentor_telegram_id],
            id=job_id,
            replace_existing=True,
        )
    logger.info('Запланировано %d будущих дедлайнов', len(future))
    
async def sync_jobs_with_db(mentor_telegram_id: int):
    """
    Периодически запускается и регистрирует задачи на все дедлайны,
    которые появились в БД, но ещё не запланированы.
    """
    scheduler = get_scheduler()
    deadlines = await _get_future_deadlines()

    added = 0
    for d in deadlines:
        job_id = f'overdue:{d["id"]}'
        if scheduler.get_job(job_id):
            continue
        scheduler.add_job(
            overdue_job,
            trigger=DateTrigger(run_date=d['due_at']),
            args=[d['id'], mentor_telegram_id],
            id=job_id,
            replace_existing=True,
        )
        added += 1

    if added:
        logger.info('Подхвачено %d новых дедлайнов из БД', added)