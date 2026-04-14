from django.urls import path
from . import views

app_name = 'chipin'

urlpatterns = [
   path("", views.home, name="home"),
]