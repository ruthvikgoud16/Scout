"""Resend email helpers — non-blocking sends."""
import os
import asyncio
import logging
import resend

logger = logging.getLogger(__name__)

RESEND_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
SENDER_NAME = os.environ.get("SENDER_NAME", "HackTrack")

if RESEND_KEY:
    resend.api_key = RESEND_KEY


async def send_email(to: str, subject: str, html: str) -> bool:
    if not RESEND_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email")
        return False
    params = {
        "from": f"{SENDER_NAME} <{SENDER_EMAIL}>",
        "to": [to],
        "subject": subject,
        "html": html,
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {to}: {result.get('id')}")
        return True
    except Exception as e:
        logger.exception(f"Resend send failed: {e}")
        return False


def reminder_html(user_name: str, event_title: str, company: str,
                  deadline_str: str, event_url: str, register_url: str) -> str:
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#fafafa;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;color:#0a0a0a">
<table cellpadding="0" cellspacing="0" width="100%" style="padding:32px 16px">
  <tr><td align="center">
    <table cellpadding="0" cellspacing="0" width="560" style="background:#fff;border:1px solid #e4e4e7">
      <tr><td style="padding:32px">
        <div style="font-size:11px;letter-spacing:.2em;color:#52525b;text-transform:uppercase;font-weight:700">⏰ Deadline in 24h</div>
        <h1 style="font-size:28px;font-weight:800;letter-spacing:-.02em;margin:12px 0 8px;line-height:1.1">{event_title}</h1>
        <div style="font-size:13px;color:#52525b;margin-bottom:24px">by {company}</div>
        <p style="font-size:15px;line-height:1.6;color:#27272a">Hey {user_name},</p>
        <p style="font-size:15px;line-height:1.6;color:#27272a">Quick reminder — registration for <strong>{event_title}</strong> closes on <strong>{deadline_str}</strong>. Don't miss it!</p>
        <table cellpadding="0" cellspacing="0" style="margin:24px 0">
          <tr>
            <td style="background:#0a0a0a;padding:14px 22px"><a href="{register_url}" style="color:#fff;text-decoration:none;font-weight:600;font-size:14px">Register now →</a></td>
            <td style="padding-left:8px"><a href="{event_url}" style="color:#0a0a0a;text-decoration:none;font-weight:600;font-size:14px;padding:14px 22px;border:1px solid #d4d4d8;display:inline-block">View prep guide</a></td>
          </tr>
        </table>
        <hr style="border:0;border-top:1px solid #e4e4e7;margin:24px 0">
        <p style="font-size:12px;color:#71717a">You're getting this because you bookmarked this opportunity on OpportunityOS. <a href="{event_url}" style="color:#2962FF">Manage reminders</a></p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""
