"""
labs/bola/app.py  (standalone Django + DRF)
────────────────────────────────────────────
Goal 3 / Goal 8 — API Security lab: Broken Object Level Authorisation (BOLA).
Demonstrates DRF endpoint missing object-level permission checks.

A01:2026 candidate category — access any order by incrementing the ID.
Attack: GET /api/orders/43/ as user_a → receives user_b's private order data.
"""

import hashlib
import os
import sys

import django
from django.conf import settings

# ── Minimal Django config for standalone Flask-like run ──────────────────────
if not settings.configured:
    settings.configure(
        SECRET_KEY='bola-lab-dev-secret-key',
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': '/tmp/bola_lab.db',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'rest_framework',
        ],
        ROOT_URLCONF=__name__,
        DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    )
    django.setup()

from django.contrib.auth.models import User
from django.db import models
from django.urls import path
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

LAB_ID = 'bola_a01'
FLAG   = f'FLAG{{{hashlib.sha256(b"pygoat-bola-a01-secret").hexdigest()}}}'


# ── Models ────────────────────────────────────────────────────────────────────

class Order(models.Model):
    user    = models.ForeignKey(User, on_delete=models.CASCADE)
    items   = models.JSONField(default=list)
    total   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    address = models.TextField()

    class Meta:
        app_label = 'bola'


# ── Serialisers ───────────────────────────────────────────────────────────────

class OrderSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model  = Order
        fields = ['id', 'username', 'items', 'total', 'address']


# ── Vulnerable View ───────────────────────────────────────────────────────────

class VulnerableOrderDetail(APIView):
    """
    VULNERABLE — No object-level permission check.
    Any authenticated user can access ANY order by changing the ID.
    
    GET /api/orders/<pk>/ → returns order regardless of ownership
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            # ── VULNERABLE: no filter by request.user ──
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        data = OrderSerializer(order).data
        # If the user accessed someone else's order, include the flag
        if order.user != request.user:
            data['_flag'] = FLAG
        return Response(data)


# ── Secure View ───────────────────────────────────────────────────────────────

class SecureOrderDetail(APIView):
    """
    SECURE — Filters queryset by request.user before fetching by pk.
    Ownership is enforced at the database query level.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            # ── SECURE: filter queryset by owner ──
            order = Order.objects.get(pk=pk, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Not found or not authorised."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(OrderSerializer(order).data)


# ── Health / Reset / Verify (Container API) ───────────────────────────────────

from django.http import JsonResponse as DjJsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


def health(request):
    return DjJsonResponse({"status": "ok", "lab_id": LAB_ID})


@csrf_exempt
def reset(request):
    if request.method == 'POST':
        Order.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()
        # Seed two users
        u1 = User.objects.create_user('user_a', password='pass_a')
        u2 = User.objects.create_user('user_b', password='pass_b')
        Order.objects.create(user=u1, items=['laptop','charger'], total=1299.00, address='1 Main St')
        Order.objects.create(user=u1, items=['book'],             total=29.99,  address='1 Main St')
        Order.objects.create(user=u2, items=['phone','case'],     total=899.00, address='2 Oak Ave')
        Order.objects.create(user=u2, items=['headphones'],       total=199.00, address='2 Oak Ave')
        return DjJsonResponse({"status": "reset", "lab_id": LAB_ID})
    return DjJsonResponse({"error": "POST required"}, status=405)


@csrf_exempt
def verify(request):
    if request.method == 'POST':
        data = json.loads(request.body or '{}')
        submitted = data.get('flag', '')
        if submitted == FLAG:
            return DjJsonResponse({"success": True, "score": 100})
        return DjJsonResponse({"success": False, "score": 0})
    return DjJsonResponse({"error": "POST required"}, status=405)


# ── URL Configuration ─────────────────────────────────────────────────────────

urlpatterns = [
    path('health',              health,                                  name='health'),
    path('reset',               reset,                                   name='reset'),
    path('verify',              verify,                                  name='verify'),
    path('api/orders/<int:pk>/',        VulnerableOrderDetail.as_view(), name='order_detail_vuln'),
    path('api/secure/orders/<int:pk>/', SecureOrderDetail.as_view(),     name='order_detail_secure'),
]


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    from django.core import management
    management.call_command('migrate', '--run-syncdb', verbosity=0)
    # Seed data
    from django.test.utils import setup_test_environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '__main__')
    execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8008'])
