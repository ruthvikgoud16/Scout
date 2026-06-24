"""Background scheduler — auto-refresh + reminder cron jobs."""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


def start_scheduler(db, refresh_fn, send_email_fn, reminder_html_fn):
    sched = AsyncIOScheduler(timezone="UTC")

    async def auto_refresh():
        logger.info("[cron] auto-refresh starting")
        try:
            await refresh_fn()
            logger.info("[cron] auto-refresh done")
        except Exception:
            logger.exception("[cron] auto-refresh failed")

    async def send_reminders():
        logger.info("[cron] reminder scan starting")
        try:
            now = datetime.now(timezone.utc)
            window_end = now + timedelta(hours=24)
            # find events whose deadline is between now and 24h ahead
            cursor = db.hackathons.find(
                {"registration_deadline": {"$ne": None}}, {"_id": 0}
            )
            sent_count = 0
            async for h in cursor:
                ddl = h.get("registration_deadline")
                if not ddl:
                    continue
                try:
                    dt = datetime.fromisoformat(ddl.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if not (now <= dt <= window_end):
                    continue
                # find users who bookmarked this hackathon with reminders on
                async for user in db.users.find(
                    {"bookmarks": h["id"], "email_notify": True},
                    {"_id": 0, "password_hash": 0},
                ):
                    sent_key = f"{user['user_id']}:{h['id']}"
                    if await db.email_log.find_one({"key": sent_key}):
                        continue
                    base = "https://recruit-pulse-9.preview.emergentagent.com"
                    html = reminder_html_fn(
                        user.get("name") or "there",
                        h.get("title", ""),
                        h.get("company", ""),
                        dt.strftime("%a %d %b %Y · %H:%M UTC"),
                        f"{base}/hackathons/{h['id']}",
                        h.get("registration_link") or f"{base}/hackathons/{h['id']}",
                    )
                    ok = await send_email_fn(
                        user["email"],
                        f"⏰ {h['title']} closes in <24h",
                        html,
                    )
                    if ok:
                        await db.email_log.insert_one(
                            {
                                "key": sent_key,
                                "sent_at": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                        sent_count += 1
            logger.info(f"[cron] reminders sent: {sent_count}")
        except Exception:
            logger.exception("[cron] reminder scan failed")

    sched.add_job(auto_refresh, "interval", hours=6, id="auto_refresh", next_run_time=None)
    sched.add_job(send_reminders, "interval", hours=1, id="reminders", next_run_time=datetime.now(timezone.utc) + timedelta(seconds=60))
    sched.start()
    logger.info("Scheduler started — auto-refresh every 6h, reminder scan every 1h")
    return sched
