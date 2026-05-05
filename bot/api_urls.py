from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    StudentViewSet,
    DeadlineViewSet,
    AssignmentViewSet,
    MeView,
)

router = DefaultRouter()
router.register('students', StudentViewSet, basename='students')
router.register('deadlines', DeadlineViewSet, basename='deadlines')
router.register('assignments', AssignmentViewSet, basename='assignments')

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
] + router.urls