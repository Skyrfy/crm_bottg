from django.contrib import admin
from django.conf import settings
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('bot.api_urls')),

    # Mini App: главная и явные страницы
    path('', TemplateView.as_view(template_name='index.html'), name='webapp_index'),
    path('mentor/', TemplateView.as_view(template_name='mentor.html'), name='webapp_mentor'),
    path('student/', TemplateView.as_view(template_name='student.html'), name='webapp_student'),
]

# Раздача css/js/файлов webapp в DEBUG-режиме
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^(?P<path>(css|js)/.*)$', serve, {'document_root': settings.WEBAPP_DIR}),
    ]
