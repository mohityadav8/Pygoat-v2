# playgrounds/urls.py
from django.urls import path
from playgrounds import views

app_name = 'playgrounds'

urlpatterns = [
    path('ssrf/',            views.ssrf_playground, name='ssrf'),
    path('ssrf/probe/',      views.ssrf_probe,       name='ssrf_probe'),
    path('ssti/',            views.ssti_playground,  name='ssti'),
    path('ssti/evaluate/',   views.ssti_evaluate,    name='ssti_evaluate'),
]
