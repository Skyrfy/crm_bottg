import asyncio
import logging
import os

from bot.scheduler import get_scheduler, restore_jobs_from_db
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command as CommandFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand

from bot.models import Student

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
MENTOR_TELEGRAM_ID = int(os.getenv('MENTOR_TELEGRAM_ID', '0'))

GROUP_LABELS = dict(Student.GROUP_CHOICES)


# ---------- FSM ----------
class BroadcastStates(StatesGroup):
    choosing_group = State()
    writing_text = State()
    confirming = State()


# ---------- Клавиатуры ----------
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✉️ Написать (рассылка)', callback_data='broadcast')],
        [InlineKeyboardButton(text='👥 Нераспределённые ученики', callback_data='unassigned')],
        [InlineKeyboardButton(text='⏰ Дедлайны', callback_data='deadlines')],
    ])


def groups_kb_for_broadcast() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='C++', callback_data='bgroup:cpp'),
         InlineKeyboardButton(text='Python', callback_data='bgroup:python')],
        [InlineKeyboardButton(text='Rust', callback_data='bgroup:rust'),
         InlineKeyboardButton(text='Blockchain', callback_data='bgroup:blockchain')],
        [InlineKeyboardButton(text='📢 Все группы', callback_data='bgroup:all')],
        [InlineKeyboardButton(text='⬅️ Назад', callback_data='main_menu')],
    ])


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='✅ Отправить', callback_data='confirm_send')],
        [InlineKeyboardButton(text='✏️ Переписать', callback_data='broadcast')],
        [InlineKeyboardButton(text='❌ Отмена', callback_data='main_menu')],
    ])


def assign_groups_kb(student_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для распределения конкретного ученика по группам."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='C++', callback_data=f'assign:{student_id}:cpp'),
         InlineKeyboardButton(text='Python', callback_data=f'assign:{student_id}:python')],
        [InlineKeyboardButton(text='Rust', callback_data=f'assign:{student_id}:rust'),
         InlineKeyboardButton(text='Blockchain', callback_data=f'assign:{student_id}:blockchain')],
        [InlineKeyboardButton(text='⬅️ В главное меню', callback_data='main_menu')],
    ])


def assign_prompt_kb(student_id: int) -> InlineKeyboardMarkup:
    """Кнопка под уведомлением ментору о новом ученике."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📌 Распределить', callback_data=f'open_assign:{student_id}')],
    ])


# ---------- ORM-обёртки ----------
@sync_to_async
def get_students_by_group(group: str):
    qs = Student.objects.filter(is_active=True)
    if group == 'all':
        qs = qs.exclude(group__isnull=True)  # рассылка только распределённым
    else:
        qs = qs.filter(group=group)
    return list(qs.values_list('telegram_id', flat=True))


@sync_to_async
def upsert_student(telegram_id: int, username: str, full_name: str):
    """Возвращает (student, created)."""
    student, created = Student.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={'username': username, 'full_name': full_name},
    )
    return student, created


@sync_to_async
def get_unassigned_students():
    return list(
        Student.objects.filter(is_active=True, group__isnull=True)
        .order_by('-created_at')
        .values('id', 'full_name', 'username', 'telegram_id')
    )


@sync_to_async
def get_student_by_id(student_id: int):
    return Student.objects.filter(id=student_id).first()


@sync_to_async
def assign_student_group(student_id: int, group: str):
    """Возвращает обновлённого ученика или None, если не найден."""
    student = Student.objects.filter(id=student_id).first()
    if not student:
        return None
    student.group = group
    student.save(update_fields=['group'])
    return student


# ---------- Хендлеры ----------
def is_mentor(user_id: int) -> bool:
    return user_id == MENTOR_TELEGRAM_ID


async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user = message.from_user

    if is_mentor(user.id):
        await message.answer(
            '👋 Главное меню ментора\n\nВыберите действие:',
            reply_markup=main_menu_kb(),
        )
        return

    # Регистрация ученика без группы
    student, created = await upsert_student(
        telegram_id=user.id,
        username=user.username or '',
        full_name=user.full_name,
    )

    if created:
        await message.answer(
            f'Привет, {user.full_name}! Вы добавлены в базу учеников. '
            f'Ментор скоро свяжется с вами и определит группу обучения.'
        )
        # Уведомляем ментора
        username_part = f'@{user.username}' if user.username else '(без username)'
        notification = (
            f'🆕 <b>Новый ученик</b>\n\n'
            f'Имя: {user.full_name}\n'
            f'Username: {username_part}\n'
            f'Telegram ID: <code>{user.id}</code>\n\n'
            f'Нажмите кнопку ниже, чтобы распределить его в группу.'
        )
        try:
            await bot.send_message(
                MENTOR_TELEGRAM_ID,
                notification,
                reply_markup=assign_prompt_kb(student.id),
                parse_mode='HTML',
            )
        except Exception as e:
            logger.warning('Не удалось уведомить ментора: %s', e)
    else:
        await message.answer(f'С возвращением, {user.full_name}!')


async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        '👋 Главное меню ментора\n\nВыберите действие:',
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


# --- Рассылка ---
async def cb_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_mentor(callback.from_user.id):
        await callback.answer('Доступно только ментору', show_alert=True)
        return

    await state.set_state(BroadcastStates.choosing_group)
    await callback.message.edit_text(
        '📨 <b>Рассылка</b>\n\nВыберите группу для рассылки:',
        reply_markup=groups_kb_for_broadcast(),
        parse_mode='HTML',
    )
    await callback.answer()


async def cb_choose_broadcast_group(callback: CallbackQuery, state: FSMContext):
    group = callback.data.split(':', 1)[1]
    await state.update_data(group=group)
    await state.set_state(BroadcastStates.writing_text)

    group_label = 'всем ученикам' if group == 'all' else f'группе «{GROUP_LABELS[group]}»'
    await callback.message.edit_text(
        f'✏️ Напишите текст рассылки {group_label}.\n\n'
        f'Просто отправьте сообщение следующим шагом.'
    )
    await callback.answer()


async def msg_broadcast_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(BroadcastStates.confirming)

    data = await state.get_data()
    group = data['group']
    group_label = 'всем ученикам' if group == 'all' else f'группе «{GROUP_LABELS[group]}»'

    recipients = await get_students_by_group(group)

    await message.answer(
        f'📋 <b>Предпросмотр рассылки</b>\n\n'
        f'Кому: {group_label}\n'
        f'Получателей: {len(recipients)}\n\n'
        f'<b>Текст:</b>\n{message.text}',
        reply_markup=confirm_kb(),
        parse_mode='HTML',
    )


async def cb_confirm_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    group = data.get('group')
    text = data.get('text')

    if not text:
        await callback.answer('Текст не найден', show_alert=True)
        return

    recipients = await get_students_by_group(group)
    sent, failed = 0, 0

    for tg_id in recipients:
        try:
            await bot.send_message(tg_id, text)
            sent += 1
        except Exception as e:
            logger.warning('Не удалось отправить %s: %s', tg_id, e)
            failed += 1

    await state.clear()
    await callback.message.edit_text(
        f'✅ <b>Рассылка выполнена</b>\n\n'
        f'Отправлено: {sent} из {len(recipients)}\n'
        f'Ошибок: {failed}',
        reply_markup=main_menu_kb(),
        parse_mode='HTML',
    )
    await callback.answer()


# --- Распределение учеников ---
async def cb_unassigned_list(callback: CallbackQuery):
    if not is_mentor(callback.from_user.id):
        await callback.answer('Доступно только ментору', show_alert=True)
        return

    students = await get_unassigned_students()

    if not students:
        await callback.message.edit_text(
            '✅ Нет нераспределённых учеников.',
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    keyboard = []
    for s in students:
        username = f'@{s["username"]}' if s['username'] else f'ID {s["telegram_id"]}'
        label = f'{s["full_name"]} ({username})'
        keyboard.append([
            InlineKeyboardButton(text=label, callback_data=f'open_assign:{s["id"]}')
        ])
    keyboard.append([InlineKeyboardButton(text='⬅️ Назад', callback_data='main_menu')])

    await callback.message.edit_text(
        f'👥 <b>Нераспределённые ученики</b> ({len(students)})\n\n'
        f'Выберите ученика, чтобы определить его в группу:',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML',
    )
    await callback.answer()


async def cb_open_assign(callback: CallbackQuery):
    if not is_mentor(callback.from_user.id):
        await callback.answer('Доступно только ментору', show_alert=True)
        return

    student_id = int(callback.data.split(':', 1)[1])
    student = await get_student_by_id(student_id)

    if not student:
        await callback.answer('Ученик не найден', show_alert=True)
        return

    if student.group:
        await callback.message.edit_text(
            f'ℹ️ Ученик <b>{student.full_name}</b> уже распределён '
            f'в группу «{GROUP_LABELS[student.group]}».',
            reply_markup=main_menu_kb(),
            parse_mode='HTML',
        )
        await callback.answer()
        return

    username_part = f'@{student.username}' if student.username else '(без username)'
    await callback.message.edit_text(
        f'📌 <b>Распределение ученика</b>\n\n'
        f'Имя: {student.full_name}\n'
        f'Username: {username_part}\n\n'
        f'Выберите группу:',
        reply_markup=assign_groups_kb(student.id),
        parse_mode='HTML',
    )
    await callback.answer()


async def cb_assign_group(callback: CallbackQuery, bot: Bot):
    if not is_mentor(callback.from_user.id):
        await callback.answer('Доступно только ментору', show_alert=True)
        return

    _, student_id_str, group = callback.data.split(':')
    student_id = int(student_id_str)

    student = await assign_student_group(student_id, group)
    if not student:
        await callback.answer('Ученик не найден', show_alert=True)
        return

    group_label = GROUP_LABELS[group]

    # Уведомляем ученика
    try:
        await bot.send_message(
            student.telegram_id,
            f'📚 Вас определили в группу «{group_label}». '
            f'Скоро ментор свяжется с вами по поводу учебного плана.',
        )
    except Exception as e:
        logger.warning('Не удалось уведомить ученика %s: %s', student.telegram_id, e)

    await callback.message.edit_text(
        f'✅ Ученик <b>{student.full_name}</b> добавлен в группу «{group_label}».',
        reply_markup=main_menu_kb(),
        parse_mode='HTML',
    )
    await callback.answer('Распределено')


# --- Заглушка для дедлайнов ---
async def cb_deadlines_stub(callback: CallbackQuery):
    await callback.answer('Раздел в разработке', show_alert=True)


# ---------- Регистрация ----------
def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, CommandFilter('start'))

    dp.callback_query.register(cb_main_menu, F.data == 'main_menu')

    # Рассылка
    dp.callback_query.register(cb_broadcast, F.data == 'broadcast')
    dp.callback_query.register(cb_choose_broadcast_group, F.data.startswith('bgroup:'))
    dp.callback_query.register(cb_confirm_send, F.data == 'confirm_send')
    dp.message.register(msg_broadcast_text, BroadcastStates.writing_text)

    # Распределение
    dp.callback_query.register(cb_unassigned_list, F.data == 'unassigned')
    dp.callback_query.register(cb_open_assign, F.data.startswith('open_assign:'))
    dp.callback_query.register(cb_assign_group, F.data.startswith('assign:'))

    # Заглушки
    dp.callback_query.register(cb_deadlines_stub, F.data == 'deadlines')


async def run_bot():
    if not BOT_TOKEN:
        raise RuntimeError('BOT_TOKEN не задан в .env')

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    register_handlers(dp)

    from bot.scheduler import get_scheduler, restore_jobs_from_db, sync_jobs_with_db
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = get_scheduler()
    scheduler.start()
    await restore_jobs_from_db(MENTOR_TELEGRAM_ID)

    # Каждую минуту сканируем БД на новые дедлайны
    scheduler.add_job(
        sync_jobs_with_db,
        trigger=IntervalTrigger(minutes=1),
        args=[MENTOR_TELEGRAM_ID],
        id='sync_jobs',
        replace_existing=True,
    )

    logger.info('Бот запущен (long polling)')
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)


class Command(BaseCommand):
    help = 'Запускает Telegram-бота в режиме long polling'

    def handle(self, *args, **options):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        )
        try:
            asyncio.run(run_bot())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Бот остановлен'))