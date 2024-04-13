# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('image_to_table/', views.image_to_table, name='image_to_table'),
]
