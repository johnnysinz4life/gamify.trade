from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from users.models import TradeSession, Listing


class Command(BaseCommand):
    help = "Expire inactive DM trade sessions (7d) and deactivate listings older than 1 year."

    def handle(self, *args, **options):
        now = timezone.now()

        trade_cutoff = now - timedelta(days=7)
        qs = TradeSession.objects.filter(
            status=TradeSession.Status.ACTIVE,
            last_activity_at__lte=trade_cutoff,
        )
        expired = qs.update(status=TradeSession.Status.EXPIRED_INACTIVE)

        listing_cutoff = now - timedelta(days=365)
        Listing.objects.filter(is_active=True, created_at__lte=listing_cutoff).update(is_active=False)

        self.stdout.write(self.style.SUCCESS(
            f"Expired {expired} trade sessions; deactivated old listings if any."
        ))

