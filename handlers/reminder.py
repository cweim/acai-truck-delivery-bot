"""Automated delivery reminder — fires ~1 hour before each delivery session."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from zoneinfo import ZoneInfo
    _SGT = ZoneInfo("Asia/Singapore")
except ImportError:
    ZoneInfo = None
    _SGT = None

DEFAULT_REMINDER_MESSAGE = (
    "Hi {customer_name}! 🍧 Your acai order is arriving in about 1 hour. "
    "Get ready — see you soon!"
)


def _now_sgt() -> datetime:
    return datetime.now(_SGT) if _SGT else datetime.now()


def _parse_dt(raw: str) -> datetime:
    """Parse ISO datetime string into a timezone-aware datetime."""
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None and _SGT:
        dt = dt.replace(tzinfo=_SGT)
    return dt


async def send_delivery_reminders(context):
    """
    JobQueue callback — runs every 5 minutes.
    Sends reminder messages to all customers in sessions that are ~1 hour away.
    """
    from database.supabase_client import get_db

    try:
        db = get_db()
        now = _now_sgt()

        # Fetch all sessions (open AND closed — cutoff may have passed but delivery hasn't yet)
        sessions = db.get_delivery_sessions(status="")

        for session in sessions:
            session_id = session.get("id")  # integer PK used by get_delivery_session_users
            delivery_dt_str = session.get("delivery_datetime")
            if not session_id or not delivery_dt_str:
                continue

            try:
                delivery_dt = _parse_dt(delivery_dt_str)
                # Normalise timezone comparison
                if delivery_dt.tzinfo and now.tzinfo is None:
                    now_cmp = now.replace(tzinfo=delivery_dt.tzinfo)
                elif delivery_dt.tzinfo is None and now.tzinfo:
                    now_cmp = now.replace(tzinfo=None)
                else:
                    now_cmp = now
                minutes_away = (delivery_dt - now_cmp).total_seconds() / 60
            except Exception as exc:
                logger.warning("Cannot parse delivery_datetime for session %s: %s", session_id, exc)
                continue

            # Fire window: 55–65 minutes before delivery (handles 5-min polling interval)
            if not (55 <= minutes_away <= 65):
                continue

            # Skip if already sent
            if db.get_reminder_sent(session_id):
                logger.info("Reminder already sent for session %s — skipping.", session_id)
                continue

            # Load per-session config (falls back to default if not set)
            config = db.get_reminder_config(session_id)
            message_template = config.get("message") or DEFAULT_REMINDER_MESSAGE
            image_url = config.get("image_url") or None

            users = db.get_delivery_session_users(session_id)
            sent = 0
            for user in users:
                telegram_id = user.get("telegram_user_id")
                if not telegram_id:
                    continue
                customer_name = user.get("name") or user.get("telegram_handle") or "Customer"
                personalized = message_template.replace("{customer_name}", customer_name)
                try:
                    if image_url:
                        await context.bot.send_photo(
                            chat_id=telegram_id,
                            photo=image_url,
                            caption=personalized,
                            parse_mode="HTML",
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=telegram_id,
                            text=personalized,
                            parse_mode="HTML",
                        )
                    sent += 1
                except Exception as exc:
                    logger.warning("Failed to send reminder to user %s: %s", telegram_id, exc)

            # Mark sent regardless of individual failures to prevent reminder spam
            db.mark_reminder_sent(session_id)
            logger.info(
                "✅ Reminder sent for session %s (%s): %d/%d customers",
                session_id,
                session.get("location", ""),
                sent,
                len(users),
            )

    except Exception as exc:
        logger.error("❌ Error in send_delivery_reminders job: %s", exc)
