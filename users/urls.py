from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import SecureTwoFactorLoginView

urlpatterns = [
    path("login", SecureTwoFactorLoginView.as_view(), name="login"), # Login path, with 2FA incorporated into it.
    path('logout/', LogoutView.as_view(next_page='two_factor:login'), name='logout'), # Logout path, with 2FA incorporated into it.
    path('register/', views.register, name='register'), # Registeration page URL
    path('settings/', views.settings_view, name='settings'), # User settings page URL
    path('home/', views.home, name='home'), # Home page URL (after login)
    path('newlist/', views.newlist, name='newlist'), # New listing page URL
    path('mainlist/', views.mainlist, name='mainlist'), # Main list page URL (after login)
]