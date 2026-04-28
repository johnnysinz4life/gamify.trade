from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True, default='')
    location = models.CharField(max_length=100, blank=True, default='')
    xp = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username}'s Profile"
