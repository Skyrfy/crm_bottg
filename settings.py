import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "9wuyl2!ah&w2hjc28hijiko2hrp&h^bw7m_t208-&_=lpea")

DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"  
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Наши приложения
    "apps.students",
    "apps.deadlines",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Telegram настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Исправлено: получаем ID менторов из переменных .env
MENTOR_IDS = []
mentor_id = os.getenv("MENTOR_TELEGRAM_ID", "")
if mentor_id and mentor_id.isdigit():
    MENTOR_IDS.append(int(mentor_id))

# Если нужна поддержка нескольких менторов через запятую
# MENTOR_IDS = [
#     int(x.strip())
#     for x in os.getenv("MENTOR_IDS", os.getenv("MENTOR_TELEGRAM_ID", "")).split(",")
#     if x.strip().isdigit()
# ]

MENTOR_USERNAME = os.getenv("MENTOR_USERNAME", "Ed_Paul")