from django.db import models
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from two_factor.views.core import LoginView as TFLoginView
from django_otp.plugins.otp_totp.models import TOTPDevice
from .forms import (
    UserRegistrationForm,
    EmailAuthenticationForm,
    AuthenticationForm,
    UserSettingsForm,
    AccountDeleteForm,
    NewListingForm,
    DirectMessageForm,
)
from .models import Profile, Listing, DirectMessage
import secrets
import requests
from django import forms

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

def get_or_create_profile(user):
    defaults = {'nickname': Profile.generate_unique_nickname(user)}
    profile, _ = Profile.objects.get_or_create(user=user, defaults=defaults)
    if not profile.nickname:
        profile.nickname = Profile.generate_unique_nickname(user)
        profile.save(update_fields=['nickname'])
    return profile

def _hp_name(request):
    if "hp_name" not in request.session:
        request.session["hp_name"] = f"hp_{secrets.token_hex(8)}"
    return request.session["hp_name"]

class SecureTwoFactorLoginView(TFLoginView):
    template_name = "users/login.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["hp_name"] = _hp_name(self.request)
        ctx["RECAPTCHA_SITE_KEY"] = getattr(settings, "RECAPTCHA_SITE_KEY", "")
        return ctx

    def get(self, request, *args, **kwargs):
        # If you previously added an unconditional reset() here, REMOVE it.
        # Resetting here would kick you back to the auth step after any redirect.
        _hp_name(request)  # just ensure a honeypot name exists
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Determine the current wizard step
        try:
            current_step = self.steps.current  # WizardView API
        except Exception:
            current_step = None

        # Run bot checks ONLY on the username/password step
        # BAA = Bot Attack Prevention. These checks are NOT 2FA checks, and should NOT run on the OTP step.
        if current_step == 'auth':
            hp_name = request.session.get("hp_name", "hp_fallback")
            if request.POST.get(hp_name):
                messages.error(request, "Bad Authentication Attempt. Please try again.")
                return redirect('login')

            try:
                elapsed = float(request.POST.get("elapsed", 0))
                if elapsed < 1.5:
                    messages.error(request, "Please wait a moment before submitting.")
                    return redirect('login')
            except (TypeError, ValueError):
                pass

            token = request.POST.get("recaptcha-token")
            if getattr(settings, "RECAPTCHA_SECRET_KEY", None):
                try:
                    r = requests.post(
                        RECAPTCHA_VERIFY_URL,
                        data={
                            "secret": settings.RECAPTCHA_SECRET_KEY,
                            "response": token,
                            "remoteip": request.META.get("REMOTE_ADDR"),
                        },
                        timeout=3.0,
                    )
                    rc = r.json()
                except requests.RequestException:
                    rc = {"success": False}

                ok = rc.get("success", False)
                score = rc.get("score")
                if not ok or (score is not None and score < 0.5):
                    messages.error(request, "reCAPTCHA validation failed. Please try again.")
                    return redirect('login')

        # For the OTP step, do NOT run any of the above checks.
        # Let two-factor handle the token validation.
        return super().post(request, *args, **kwargs)

def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            form.add_error(field, error)
                else:
                    form.add_error(None, e)
            else:
                messages.success(request, "Your account has been created! You can now log in.")
                return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

@login_required(login_url='login')
def settings_view(request):
    profile = get_or_create_profile(request.user)
    if request.method == 'POST':
        profile_form = UserSettingsForm(request.POST, instance=request.user, profile=profile)
        password_form = PasswordChangeForm(request.user)
        delete_form = AccountDeleteForm(request.POST)

        if 'save_profile' in request.POST and profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Your account settings have been updated.')
            return redirect('users:settings')

        if 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, 'Your password has been updated.')
                return redirect('users:settings')

        if 'delete_account' in request.POST and delete_form.is_valid():
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, 'Your account has been deleted. We are sorry to see you go.')
            return redirect('login')
    else:
        profile_form = UserSettingsForm(instance=request.user, profile=profile)
        password_form = PasswordChangeForm(request.user)
        delete_form = AccountDeleteForm()

    return render(
        request,
        'users/settings.html',
        {
            'profile_form': profile_form,
            'password_form': password_form,
            'delete_form': delete_form,
            'profile': profile,
        },
    )

@login_required(login_url='login')
def newlist(request):
    if request.method == 'POST':
        form = NewListingForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'New listing created successfully.')
            return redirect('users:home')
    else:
        form = NewListingForm(user=request.user)

    return render(request, 'users/newlist.html', {'form': form})

@login_required(login_url='login')
def listings_view(request):
    query = request.GET.get('q', '')
    if query:
        listings = Listing.objects.filter(
            models.Q(title__icontains=query)
            | models.Q(description__icontains=query)
            | models.Q(tags__name__icontains=query)
        ).distinct().order_by('-created_at')
    else:
        listings = Listing.objects.all().order_by('-created_at')
    return render(request, 'users/listings.html', {'listings': listings, 'query': query})

@login_required(login_url='login')
def profile_view(request):
    profile = get_or_create_profile(request.user)
    return render(request, 'users/profile.html', {'profile': profile, 'user': request.user})


@login_required(login_url='login')
def listing_detail(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    return render(request, 'users/listing_detail.html', {'listing': listing})


@login_required(login_url='login')
def direct_messages(request):
    """Display the current user's inbox with per-sender threads."""
    # Mark as read when viewing the inbox.
    DirectMessage.objects.filter(recipient=request.user, read=False).update(read=True)

    # Latest message per sender (recipient=request.user)
    latest_qs = (
        DirectMessage.objects.filter(recipient=request.user)
        .values('sender')
        .annotate(last_created_at=models.Max('created_at'))
    )

    sender_ids = [row['sender'] for row in latest_qs]
    latest_messages = (
        DirectMessage.objects.filter(recipient=request.user, sender_id__in=sender_ids)
        .select_related('sender', 'recipient')
        .order_by('-created_at')
    )

    # Keep only the newest message for each sender.
    seen = set()
    threads = []
    for m in latest_messages:
        if m.sender_id in seen:
            continue
        seen.add(m.sender_id)
        threads.append(m)

    return render(request, 'users/direct_messages.html', {'messages': threads})



@login_required(login_url='login')
def contact_user(request, pk):
    """Handle composing and sending a direct message to a listing's seller."""
    listing = get_object_or_404(Listing, pk=pk)
    
    # Prevent users from contacting themselves
    if listing.user == request.user:
        messages.error(request, 'You cannot contact yourself.')
        return redirect('users:listing_detail', pk=pk)
    
    if request.method == 'POST':
        form = DirectMessageForm(request.POST)
        if form.is_valid():
            DirectMessage.objects.create(
                sender=request.user,
                recipient=listing.user,
                content=form.cleaned_data['content']
            )
            messages.success(request, f'Message sent to {listing.user.get_full_name() or listing.user.username}!')
            return redirect('users:listing_detail', pk=pk)
    else:
        form = DirectMessageForm()
    
    return render(request, 'users/contact_user.html', {
        'form': form,
        'listing': listing,
    })


@login_required(login_url='login')
def reply_user(request, user_id):
    """Reply to a user and show message history between the two users."""
    other_user = get_object_or_404(User, pk=user_id)

    # Message history for the conversation between the two users.
    conversation = (
        DirectMessage.objects.filter(
            models.Q(sender=request.user, recipient=other_user)
            | models.Q(sender=other_user, recipient=request.user)
        )
        .select_related('sender', 'recipient')
        .order_by('created_at')
    )

    # Mark messages from other_user as read when viewing reply thread.
    DirectMessage.objects.filter(recipient=request.user, sender=other_user, read=False).update(read=True)

    if request.method == 'POST':
        form = DirectMessageForm(request.POST)
        if form.is_valid():
            DirectMessage.objects.create(
                sender=request.user,
                recipient=other_user,
                content=form.cleaned_data['content'],
            )
            messages.success(request, f'Reply sent to {other_user.get_full_name() or other_user.username}!')
            return redirect('users:reply_user', user_id=other_user.pk)
    else:
        form = DirectMessageForm()

    return render(
        request,
        'users/reply_user.html',
        {
            'form': form,
            'recipient': other_user,
            'conversation': conversation,
        },
    )



@login_required(login_url='login')
def grant_xp(request):
    """Placeholder endpoint to add XP to the logged-in user's profile.

    Accepts POST with an `amount` field (expected integers like 10 or 100).
    Redirects back to the main home page with a success or error message.
    """
    if request.method != 'POST':
        return redirect('main:home')

    amount = request.POST.get('amount')
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        messages.error(request, 'Invalid XP amount.')
        return redirect('main:home')

    if amount not in (10, 100):
        messages.error(request, 'XP amount not allowed.')
        return redirect('main:home')

    profile = get_or_create_profile(request.user)
    profile.xp = profile.xp + amount
    profile.save(update_fields=['xp'])
    messages.success(request, f'Added {amount} XP to your profile.')
    return redirect('main:home')

@login_required(login_url='login')
def mainlist(request):
    return redirect('main:home')

@login_required(login_url='login')
def user(request):
    return render(request, "main/home.html")

def logout_view(request):
    logout(request)
    messages.success(request, "Successfully logged out.")
    return redirect('login')

@login_required(login_url='login')
def home(request):
    # Do they have any OTP device configured?
    has_device = TOTPDevice.objects.filter(user=request.user, confirmed=True).exists()

    # Are they verified in THIS session? (True after successful 2FA step)
    is_verified = False
    if hasattr(request.user, "is_verified"):
        try:
            is_verified = bool(request.user.is_verified())
        except TypeError:
            is_verified = bool(request.user.is_verified)

    profile = get_or_create_profile(request.user)

    context = {
        "has_device": has_device,
        "is_verified": is_verified,
        "user": request.user,
        "profile": profile,
    }
    return render(request, "main/home.html", context)

class EmailAuthenticationForm(AuthenticationForm):
    honeypot = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'tabindex': '-1',
            'style': 'position:absolute; left:-9999px; top:0;'
        })
    )

    def clean_honeypot(self):
        value = self.cleaned_data.get('honeypot')
        if value:
            raise forms.ValidationError("Invalid submission.")
        return value