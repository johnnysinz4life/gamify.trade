from django.urls import path
from . import views

app_name = 'main'
urlpatterns = [
   path("", views.landing, name="landing"),
   path('sensitive/', views.sensitive_area, name='sensitive'), 
   path('home/', views.home, name='home'),

]

