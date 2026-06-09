from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from .models import Profile, Listing, Tag, ListingImage


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    widget = MultiFileInput

    def to_python(self, data):
        if data in self.empty_values:
            return None
        if isinstance(data, list):
            return [super().to_python(item) for item in data]
        return super().to_python(data)

    def validate(self, data):
        if data in self.empty_values:
            return
        if isinstance(data, list):
            for item in data:
                super().validate(item)
        else:
            super().validate(data)

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
# Check if nickname is unique (case-insensitive)
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
            with transaction.atomic():
                user.save()
                try:
                    Profile.objects.create(user=user, nickname=self.cleaned_data['nickname'])
                except IntegrityError:
                    raise ValidationError({'nickname': "This nickname is already taken."})
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

# Account deletion confirmation
class AccountDeleteForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        label='I understand that deleting my account will remove my data permanently.',
    )


class DirectMessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Type your message...'
        }),
        label='Message',
    )


class NewListingForm(forms.ModelForm):
    tag_names = forms.CharField(
        required=False,
        help_text="Comma-separated tags, e.g. art, gaming, rare"
    )
    images = MultiFileField(
        required=False,
        widget=MultiFileInput(attrs={'multiple': True})
    )

    class Meta:
        model = Listing
        fields = ['title', 'description', 'tag_names', 'images']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        listing = super().save(commit=False)
        listing.user = self.user
        if commit:
            listing.save()

        tag_names = self.cleaned_data.get('tag_names', '')
        if tag_names:
            tags = []
            for raw_tag in tag_names.split(','):
                name = raw_tag.strip().lower()
                if not name:
                    continue
                tag, _ = Tag.objects.get_or_create(name=name)
                tags.append(tag)
            listing.tags.set(tags)

        images = self.cleaned_data.get('images')
        if images:
            if not isinstance(images, list):
                images = [images]
            for image_file in images:
                ListingImage.objects.create(listing=listing, image=image_file)

        return listing
    