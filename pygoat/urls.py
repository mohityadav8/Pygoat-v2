"""PyGoat v2 — Root URL Configuration"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth
    path('', include('django.contrib.auth.urls')),
    path('accounts/', include('allauth.urls')),
    path('register/', core_views.register, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Core — dashboard, lab registry, progress
    path('', core_views.home, name='home'),
    path('dashboard/', core_views.dashboard, name='dashboard'),
    path('labs/', core_views.lab_registry, name='lab_registry'),
    path('labs/<str:lab_id>/', core_views.lab_detail, name='lab_detail'),
    path('labs/<str:lab_id>/reset/', core_views.lab_reset, name='lab_reset'),
    path('labs/<str:lab_id>/verify/', core_views.lab_verify, name='lab_verify'),

    # Challenges
    path('challenges/', include('challenges.urls')),

    # Playgrounds
    path('playground/', include('playgrounds.urls')),

    # OWASP 2026 section
    path('owasp2026/', core_views.owasp2026, name='owasp2026'),

    # Internal API — used by lab containers to report completion
    path('api/lab/health/', core_views.api_lab_health, name='api_lab_health'),
    path('api/progress/', core_views.api_progress, name='api_progress'),

    # Legacy introduction app (kept alive during migration)
    path('intro/', include('introduction.urls')),
]
