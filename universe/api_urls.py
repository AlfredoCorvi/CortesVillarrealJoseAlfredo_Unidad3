from django.urls import path

from . import api

app_name = 'api'
urlpatterns = [
    path('planetas/', api.planet_list, name='planet_list'),
    path('planetas/<slug:slug>/', api.planet_detail, name='planet_detail'),
]
