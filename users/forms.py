from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Profile

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=30, required=True)
    surname = forms.CharField(max_length=30, required=True, label="Last name")
    nickname = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        # No 'username' here — we set it from email in save()
        fields = ['email', 'password1', 'password2', 'first_name']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        # since username = email, ensure no existing username/email matches
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_nickname(self):
        nick = self.cleaned_data.get("nickname", "").strip()
        if not nick:
            raise forms.ValidationError("Nickname is required.")
        from .models import Profile
        if Profile.objects.filter(nickname__iexact=nick).exists():
            raise forms.ValidationError("This nickname is already taken.")
        return nick

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email'].strip().lower()
        user.username = email            # username mirrors email
        user.email = email
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['surname']

        if commit:
            user.save()
            # ensure profile & nickname
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.nickname = self.cleaned_data['nickname']
            profile.save(update_fields=['nickname'])
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True})
    )

# Profile editing data for settings page
class UserSettingsForm(forms.ModelForm):
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        label='Profile description',
    )
    location = forms.CharField(
        required=False,
        max_length=100,
        label='General location',
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']

    def __init__(self, *args, profile=None, **kwargs):
        self.profile = profile
        super().__init__(*args, **kwargs)
        if profile is not None:
            self.fields['description'].initial = profile.description
            self.fields['location'].initial = profile.location

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(username__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].strip().lower()
        user.username = user.email
        if commit:
            user.save()
            profile = self.profile
            if profile is not None:
                profile.description = self.cleaned_data.get('description', '').strip()
                profile.location = self.cleaned_data.get('location', '').strip()
                profile.save(update_fields=['description', 'location'])
        return user


class AccountDeleteForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        label='I understand that deleting my account will remove my data permanently.',
    )