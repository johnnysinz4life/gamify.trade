from django.http import HttpResponse 
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django_otp import devices_for_user
from django_otp.decorators import otp_required
from users.views import get_or_create_profile

@otp_required
def sensitive_area(request):
    return render(request, "main/sensitive.html")

def landing(request):
    return render(request, 'main/landing.html')


@login_required(login_url='login')
def home(request):

    # Do they have any OTP device configured?
    has_device = any(devices_for_user(request.user, for_verify=True))

    # Are they verified in THIS session? (True after successful 2FA step)
    is_verified = False
    if hasattr(request.user, "is_verified"):
        try:
            is_verified = bool(request.user.is_verified())
        except TypeError:
            is_verified = bool(request.user.is_verified)

    context = {
        "has_device": has_device,
        "is_verified": is_verified,
        "user": request.user,
        "profile": get_or_create_profile(request.user),
    }
    return render(request, "main/home.html", context)