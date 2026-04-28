import secrets, requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from two_factor.views.core import LoginView as TFLoginView
from django_otp.plugins.otp_totp.models import TOTPDevice
from .forms import (
    UserRegistrationForm,
    EmailAuthenticationForm,
    UserSettingsForm,
    AccountDeleteForm,
    NewListingForm,
)
from .models import Profile

RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

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
        if current_step == 'auth':
            hp_name = request.session.get("hp_name", "hp_fallback")
            if request.POST.get(hp_name):
                messages.error(request, "Bot detected.")
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
            form.save()
            messages.success(request, "Your account has been created! You can now log in.")
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

@login_required(login_url='login')
def settings_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
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
        form = NewListingForm(request.POST)
        if form.is_valid():
            messages.success(request, 'New listing created successfully.')
            return redirect('users:home')
    else:
        form = NewListingForm()

    return render(request, 'users/newlist.html', {'form': form})

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

    profile, _ = Profile.objects.get_or_create(user=request.user)

    context = {
        "has_device": has_device,
        "is_verified": is_verified,
        "user": request.user,
        "profile": profile,
    }
    return render(request, "main/home.html", context)