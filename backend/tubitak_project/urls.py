# tubitak_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

from chat.views import (
    get_csrf_token,
    ChatSessionViewSet,
    cleanup_chat_sessions,
    fon_listesi,
    lstm_predict,
    feedback,
    plan_feedback,
    generate_plan_doc,
)
from users.views import UserViewSet, login_view, logout_view
from project_planning.views import ProjectViewSet, FundDurationViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'chat_sessions', ChatSessionViewSet, basename='chat_session')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'fund_durations', FundDurationViewSet, basename='fundduration')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth & CSRF
    path('api/csrf-token/', get_csrf_token, name='csrf-token'),
    path('api/users/login/',  login_view,  name='user-login'),
    path('api/users/logout/', logout_view, name='user-logout'),

    # Chat session utilities
    path('api/chat_sessions/cleanup/', cleanup_chat_sessions, name='cleanup_chat_sessions'),
    path('api/fonlar/',       fon_listesi,        name='fon_listesi'),
    path('api/lstm_predict/', lstm_predict,       name='lstm_predict'),
    path('api/feedback/',     feedback,           name='feedback'),
    path('api/plan_feedback/', plan_feedback,     name='plan_feedback'),

   


    path('api/chat_sessions/<int:pk>/generate_doc/', generate_plan_doc, name='generate_plan_doc'),
    path('api/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
