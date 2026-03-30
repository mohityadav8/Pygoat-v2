# challenges/urls.py
from django.urls import path
from challenges import views

app_name = 'challenges'

urlpatterns = [
    path('',              views.challenge_list,   name='list'),
    path('<int:challenge_id>/', views.challenge_detail, name='detail'),
    path('<int:challenge_id>/submit/', views.submit_flag,     name='submit'),
    path('<int:challenge_id>/hint/',   views.reveal_hint,     name='hint'),
]
