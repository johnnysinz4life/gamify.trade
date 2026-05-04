from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True, default='')
    location = models.CharField(max_length=100, blank=True, default='')
    xp = models.PositiveIntegerField(default=0)

    @classmethod
    def generate_unique_nickname(cls, user):
        base = user.username or user.email or f"user{user.pk}"
        candidate = slugify(base).replace('-', '_')[:30]
        if not candidate:
            candidate = f"user{user.pk}"

        suffix = ''
        counter = 1
        while cls.objects.filter(nickname__iexact=f"{candidate}{suffix}").exists():
            suffix = f"_{counter}"
            candidate = candidate[:30 - len(suffix)]
            counter += 1
        return f"{candidate}{suffix}"

    def __str__(self):
        return f"{self.user.username}'s Profile"

class Listing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
