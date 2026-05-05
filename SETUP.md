# Запуск проекта — Этап 1

## 1. Установка зависимостей

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

## 2. Настройка .env

```bash
cp .env.example .env
# Отредактируйте .env — вставьте BOT_TOKEN, DB_PASSWORD, SECRET_KEY, MENTOR_IDS
```

Ваш Telegram ID можно узнать написав боту @userinfobot.

## 3. Создание базы данных PostgreSQL

```bash
psql -U postgres
CREATE DATABASE mentor_bot;
\q
```

## 4. Применение миграций

```bash
python manage.py makemigrations students deadlines
python manage.py migrate
```

## 5. Создание суперпользователя Django admin

```bash
python manage.py createsuperuser
```

## 6. Запуск Django (для проверки admin)

```bash
python manage.py runserver
# Открыть: http://127.0.0.1:8000/admin/
```

В Django admin вы можете:
- Добавлять учеников вручную (без Telegram)
- Видеть всех зарегистрировавшихся через бота
- Управлять дедлайнами и ответами

---

## Что будет дальше

**Этап 2** — Telegram-бот: aiogram, главное меню ментора, онбординг ученика (опрос при /start).
