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
    is_active = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='listings')


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='listing_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class DirectMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username}"


class TradeSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        CLOSED_PRE_TRADE = 'CLOSED_PRE_TRADE', 'Closed (pre-trade)'
        CONCLUDED_AWAITING_RATING = 'CONCLUDED_AWAITING_RATING', 'Concluded (awaiting rating)'
        CONCLUDED_FINAL = 'CONCLUDED_FINAL', 'Concluded (final)'
        EXPIRED_INACTIVE = 'EXPIRED_INACTIVE', 'Expired (inactive)'

    class Rating(models.TextChoices):
        GOOD = 'GOOD', 'Good'
        GREAT = 'GREAT', 'Great'
        BAD = 'BAD', 'Bad'
        TERRIBLE = 'TERRIBLE', 'Terrible'

    user_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trade_sessions_a')
    user_b = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trade_sessions_b')

    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)

    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    close_a_confirmed = models.BooleanField(default=False)
    close_b_confirmed = models.BooleanField(default=False)
    close_confirmed_at = models.DateTimeField(null=True, blank=True)

    conclude_a_confirmed = models.BooleanField(default=False)
    conclude_b_confirmed = models.BooleanField(default=False)
    conclude_confirmed_at = models.DateTimeField(null=True, blank=True)

    a_rating = models.CharField(max_length=16, choices=Rating.choices, null=True, blank=True)
    b_rating = models.CharField(max_length=16, choices=Rating.choices, null=True, blank=True)

    xp_awarded_a_to_other = models.BooleanField(default=False)  # awarded XP to the *other* party after A rates
    xp_awarded_b_to_other = models.BooleanField(default=False)

    concluded_final_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user_a', 'user_b'], name='unique_trade_session_per_pair_unordered'),
            models.CheckConstraint(check=~models.Q(user_a=models.F('user_b')), name='trade_users_must_be_different'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"TradeSession({self.user_a_id}, {self.user_b_id}) - {self.status}"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def participants(self):
        return (self.user_a, self.user_b)

    def other_of(self, user):
        if user_id := getattr(user, 'id', None):
            if user_id == self.user_a_id:
                return self.user_b
            if user_id == self.user_b_id:
                return self.user_a
        return None

    def mark_close_confirmed(self, user):
        if self.status != self.Status.ACTIVE:
            return False
        if user.id == self.user_a_id:
            self.close_a_confirmed = True
        elif user.id == self.user_b_id:
            self.close_b_confirmed = True
        else:
            return False

        if self.close_a_confirmed and self.close_b_confirmed:
            self.status = self.Status.CLOSED_PRE_TRADE
            from django.utils import timezone
            self.close_confirmed_at = timezone.now()
            return True
        return False

    def mark_conclude_confirmed(self, user):
        if self.status != self.Status.ACTIVE:
            return False
        if user.id == self.user_a_id:
            self.conclude_a_confirmed = True
        elif user.id == self.user_b_id:
            self.conclude_b_confirmed = True
        else:
            return False

        if self.conclude_a_confirmed and self.conclude_b_confirmed:
            self.status = self.Status.CONCLUDED_AWAITING_RATING
            from django.utils import timezone
            self.conclude_confirmed_at = timezone.now()
            return True
        return False

    def can_rate(self):
        return self.status == self.Status.CONCLUDED_AWAITING_RATING

    @classmethod
    def any_unrated_concluded_for_user(cls, user):
        """Prevent users from starting a new trade before grading the previous one."""
        # When the user has any concluded trade waiting for rating,
        # block starting new trades.
        return cls.objects.filter(
            models.Q(status=cls.Status.CONCLUDED_AWAITING_RATING) & (
                models.Q(user_a=user, a_rating__isnull=True)
                | models.Q(user_b=user, b_rating__isnull=True)
            )
        ).exists()




