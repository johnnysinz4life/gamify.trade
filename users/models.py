from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True, default='')
    location = models.CharField(max_length=100, blank=True, default='')
    xp = models.PositiveIntegerField(default=0)
    # keep this field for compatibility with existing migration 0005_profile_classrank
    classRank = models.CharField(max_length=17, default='Unranked')

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

    @property
    def rank(self):
        """Return the ClassRank instance that matches this profile's XP.

        Falls back to a simple object with `name='Unranked'` if no ranks are defined.
        """
        try:
            rank_obj = ClassRank.get_for_xp(self.xp)
        except Exception:
            rank_obj = None

        if rank_obj:
            return rank_obj

        class _Fallback:
            def __init__(self, name):
                self.name = name

        return _Fallback(getattr(self, 'classRank', 'Unranked'))

class ClassRank(models.Model):
    name = models.CharField(max_length=50, unique=True)
    xp_threshold = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-xp_threshold']

    def __str__(self):
        return self.name

    @classmethod
    def get_for_xp(cls, xp: int):
        """Return the highest ClassRank whose xp_threshold <= xp.

        Returns None if no ClassRank rows exist.
        """
        try:
            return cls.objects.filter(xp_threshold__lte=xp).order_by('-xp_threshold').first()
        except Exception:
            return None
        
class Tag(models.Model):
    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=40, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Listing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='listings')

class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='listing_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


