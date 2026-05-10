"""
Импортирует вопросы для тренажёра из CSV-файлов ментора.

Поддерживает два формата:
1. Стандартный CSV: language,topic,title,company,answer
2. Формат от ментора: 15 колонок с заголовком "Дата собеса","Компания","Вакансия",
   "Вопрос","Тема","Рекомендованный ответ (как нужно)" и др.
   — допускается обёртка ```csv ... ``` (как у ChatGPT-экспорта)

Использование:
    python manage.py import_questions interview_data/file.csv
    python manage.py import_questions interview_data/   # обработать всю папку
    python manage.py import_questions interview_data/ --dry-run
"""

import csv
import io
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from interview.models import Question, QuestionTopic, ProgrammingLanguage


# Шаблоны для распознавания языка по строке вакансии
LANGUAGE_PATTERNS = [
    (r'\bC\+\+', 'C++'),
    (r'\bPython\b', 'Python'),
    (r'\bJava(?!Script)\b', 'Java'),
    (r'\bJavaScript\b', 'JavaScript'),
    (r'\bRust\b', 'Rust'),
    (r'\bGo(?:lang)?\b', 'Go'),
    (r'\bC#\b|\bCSharp\b', 'C#'),
    (r'\bPHP\b', 'PHP'),
    (r'\bRuby\b', 'Ruby'),
    (r'\bSwift\b', 'Swift'),
]


def detect_language(vacancy: str, fallback: str = 'Python') -> str:
    """Определяет язык программирования по строке вакансии."""
    if not vacancy:
        return fallback
    for pattern, lang in LANGUAGE_PATTERNS:
        if re.search(pattern, vacancy, re.IGNORECASE):
            return lang
    return fallback


def clean_topic(raw_topic: str) -> str:
    """Очищает значение темы от мусора в скобках."""
    if not raw_topic:
        return 'Общие вопросы'
    # Убираем скобки с уточнениями типа "Базовый (Python)"
    cleaned = re.sub(r'\s*\([^)]*\)\s*', '', raw_topic).strip()
    return cleaned or raw_topic.strip()


def strip_codeblock_wrapper(text: str) -> str:
    """Снимает обёртку ```csv ... ``` если файл экспортирован от AI."""
    text = text.strip()
    if text.startswith('```'):
        # Убираем первую строку с ```csv
        lines = text.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        # Убираем последнюю ```
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines)
    return text


def company_from_filename(path: Path) -> str:
    """Извлекает название компании из имени файла '{name}_qna.csv'."""
    name = path.stem  # без расширения
    # Убираем стандартные суффиксы
    for suffix in ('_qna', '_тех_редакт', '_техничка_редакт2',
                   '___сделано_в_Clipchamp', '_-_тех_-редакт', '_редакт'):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    # Заменяем подчёркивания на пробелы
    return name.replace('_', ' ').strip()


class Command(BaseCommand):
    help = 'Импортирует вопросы для тренажёра из CSV-файлов'

    def add_arguments(self, parser):
        parser.add_argument(
            'path', type=str,
            help='Путь к CSV-файлу или папке с CSV-файлами',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Проверить файлы, ничего не записывая в БД',
        )

    def handle(self, *args, **options):
        path = Path(options['path'])
        if not path.exists():
            raise CommandError(f'Путь не найден: {path}')

        # Собираем список файлов
        if path.is_file():
            files = [path]
        elif path.is_dir():
            files = sorted(path.glob('*.csv'))
            if not files:
                raise CommandError(f'В папке {path} нет CSV-файлов')
        else:
            raise CommandError(f'Не файл и не папка: {path}')

        total_q, total_t, total_skipped = 0, 0, 0
        all_errors = []

        for file_path in files:
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n→ {file_path.name}'))
            stats = self._process_file(file_path, dry_run=options['dry_run'])
            total_q += stats['questions']
            total_t += stats['topics']
            total_skipped += stats['skipped']
            all_errors.extend(stats['errors'])

            self.stdout.write(
                f"  вопросов добавлено: {stats['questions']}, "
                f"тем: {stats['topics']}, пропущено: {stats['skipped']}"
            )

        self.stdout.write(self.style.SUCCESS(
            f'\nИтого: вопросов {total_q}, тем {total_t}, пропущено {total_skipped}'
        ))
        if all_errors:
            self.stdout.write(self.style.WARNING(f'\nПредупреждения ({len(all_errors)}):'))
            for e in all_errors[:30]:
                self.stdout.write(f'  · {e}')
            if len(all_errors) > 30:
                self.stdout.write(f'  ... и ещё {len(all_errors) - 30}')

    def _process_file(self, path: Path, dry_run: bool) -> dict:
        stats = {'questions': 0, 'topics': 0, 'skipped': 0, 'errors': []}

        # Читаем содержимое и снимаем обёртку, если есть
        try:
            raw_text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            raw_text = path.read_text(encoding='utf-8-sig')

        cleaned_text = strip_codeblock_wrapper(raw_text)

        # Парсим как CSV из строки
        reader = csv.DictReader(io.StringIO(cleaned_text))
        if reader.fieldnames is None:
            stats['errors'].append(f'{path.name}: пустой или невалидный CSV')
            return stats

        # Определяем формат: новый (русский, 15 колонок) или старый (5 колонок)
        is_mentor_format = 'Вопрос' in reader.fieldnames and 'Тема' in reader.fieldnames

        # Имя компании из файла — фоллбек когда в данных N/A или пусто
        file_company = company_from_filename(path)
        valid_languages = {choice.value for choice in ProgrammingLanguage}

        for row_num, row in enumerate(reader, start=2):
            try:
                if is_mentor_format:
                    title = (row.get('Вопрос') or '').strip()
                    topic_raw = (row.get('Тема') or '').strip()
                    answer = (row.get('Рекомендованный ответ (как нужно)') or '').strip()
                    company_raw = (row.get('Компания') or '').strip()
                    vacancy = (row.get('Вакансия') or '').strip()

                    # Компания: сначала из колонки, иначе из имени файла
                    if not company_raw or company_raw.upper() == 'N/A':
                        company = file_company
                    else:
                        # Если описание длинное (>40 символов) — используем имя файла
                        company = file_company if len(company_raw) > 40 else company_raw

                    language = detect_language(vacancy, fallback='Python')
                    topic_name = clean_topic(topic_raw)
                else:
                    # Стандартный формат
                    language = (row.get('language') or '').strip()
                    topic_name = (row.get('topic') or '').strip()
                    title = (row.get('title') or '').strip()
                    company = (row.get('company') or '').strip()
                    answer = (row.get('answer') or '').strip()

                if not all([language, topic_name, title, company, answer]):
                    stats['errors'].append(f'{path.name}:{row_num}: пустые поля')
                    stats['skipped'] += 1
                    continue

                if language not in valid_languages:
                    stats['errors'].append(
                        f'{path.name}:{row_num}: неизвестный язык "{language}"'
                    )
                    stats['skipped'] += 1
                    continue

                if dry_run:
                    continue

                topic_obj, topic_created = QuestionTopic.objects.get_or_create(
                    language=language, topic=topic_name,
                )
                if topic_created:
                    stats['topics'] += 1

                _, q_created = Question.objects.get_or_create(
                    title=title, company=company,
                    defaults={'topic': topic_obj, 'answer': answer},
                )
                if q_created:
                    stats['questions'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                stats['errors'].append(f'{path.name}:{row_num}: {e}')
                stats['skipped'] += 1

        return stats