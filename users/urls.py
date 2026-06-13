from django.urls import path
from . import views
from .views import SecureTwoFactorLoginView

urlpatterns = [
    path("login", SecureTwoFactorLoginView.as_view(), name="login"), # Login path, with 2FA incorporated into it.
    path('logout/', views.logout_view, name='logout'), # Logout path
    path('register/', views.register, name='register'), # Registeration page URL
    path('settings/', views.settings_view, name='settings'), # User settings page URL
    path('home/', views.home, name='home'), # Home page URL (after login)
    path('newlist/', views.newlist, name='newlist'), # New listing page URL
    path('listings/', views.listings_view, name='listings'), # Search Listings page URL

    # My Listings
    path('mylistings/', views.view_my_listings, name='view_my_listings'),
    path('mylistings/<int:pk>/edit/', views.edit_listing, name='edit_listing'),
    path('mylistings/<int:pk>/delete/', views.delete_listing_confirm, name='delete_listing_confirm'),

    path('listing/<int:pk>/', views.listing_detail, name='listing_detail'),

    path('listing/<int:pk>/contact/', views.contact_user, name='contact_user'),
    path('messages/', views.direct_messages, name='messages'), # Direct messages page
    path('inbox/', views.inbox_notifications, name='inbox_notifications'), # HQ notifications inbox
    path('reply/<int:user_id>/', views.reply_user, name='reply_user'),


    # Trade controls (DM-based)
    path('reply/<int:user_id>/trade/close/', views.trade_close, name='trade_close'),
    path('reply/<int:user_id>/trade/conclude/', views.trade_conclude, name='trade_conclude'),
    path('reply/<int:user_id>/trade/rate/', views.trade_rate, name='trade_rate'),

    path('profile/', views.profile_view, name='profile'), # Profile page URL

    path('mainlist/', views.mainlist, name='mainlist'), # Main list page URL (after login)
    path('grant_xp/', views.grant_xp, name='grant_xp'), # Placeholder XP grant endpoint

]

