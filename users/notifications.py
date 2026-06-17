from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model
from notifications.signals import notify


User = get_user_model()


def notify_dm_received(*, sender, recipient, content: str) -> None:
    notify.send(
        sender=sender,
        recipient=recipient,
        verb="Someone sent you a direct message!",
        description=content[:200],
    )


def notify_xp_awarded(*, sender, recipient, amount: int, reason: Optional[str] = None) -> None:

    """Notify a user they received XP."""
    reason_text = f" ({reason})" if reason else ""
    notify.send(
        sender=sender,
        recipient=recipient,
        verb="received XP",
        description=f"You gained {amount} XP{reason_text}",
        target=recipient.username,
    )

