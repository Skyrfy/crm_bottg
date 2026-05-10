from django.contrib import admin
from django.conf import settings
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('bot.api_urls')),
    path('api/interview/', include('interview.urls')),

    path('', TemplateView.as_view(template_name='index.html'), name='webapp_index'),
    path('mentor/', TemplateView.as_view(template_name='mentor.html'), name='webapp_mentor'),
    path('student/', TemplateView.as_view(template_name='student.html'), name='webapp_student'),
]

if settings.DEBUG:
    urlpatterns += [
        # /interview/  — отдаём index.html сборки тренажёра напрямую
        re_path(
            r'^interview/?$',
            serve,
            {
                'document_root': settings.INTERVIEW_BUILD_DIR,
                'path': 'index.html',
            },
            name='webapp_interview',
        ),
        # Статика твоего кабинета
        re_path(
            r'^(?P<path>(css|js)/.*)$',
            serve, {'document_root': settings.WEBAPP_DIR},
        ),
        # Статика тренажёра
        re_path(
            r'^assets/(?P<path>.*)$',
            serve, {'document_root': settings.INTERVIEW_BUILD_DIR / 'assets'},
        ),
    ]