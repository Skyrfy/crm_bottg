from django.urls import path

from .views import (
    QuestionListAPIView,
    QuestionFiltersAPIView,
    StudentProgressAPIView,
)

urlpatterns = [
    path('questions/', QuestionListAPIView.as_view(), name='interview-questions'),
    path('filters/', QuestionFiltersAPIView.as_view(), name='interview-filters'),
    path('progress/', StudentProgressAPIView.as_view(), name='interview-progress'),
]