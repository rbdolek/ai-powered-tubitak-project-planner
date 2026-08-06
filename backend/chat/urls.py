from django.urls import path
from . import views

urlpatterns = [
    # CSRF token için URL ekleyin
    path('csrf-token/', views.get_csrf_token, name='get_csrf_token'),
    
    # Mevcut diğer URL'leriniz...
]