"""Email sending via Yandex 360 SMTP"""
import aiosmtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.yandex.ru")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "info@bigmoneychina.tech")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "info@bigmoneychina.tech")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Форум Технологии и Бизнес")

FORUM_NAME = os.getenv("FORUM_NAME", "Технологии и Бизнес 2026")
FORUM_DATES = os.getenv("FORUM_DATES", "21–23 апреля 2026")
MTS_LINK_DAY1 = os.getenv("MTS_LINK_DAY1", "#")
MTS_LINK_DAY2 = os.getenv("MTS_LINK_DAY2", "#")
MTS_LINK_DAY3 = os.getenv("MTS_LINK_DAY3", "#")


async def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send single HTML email"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            use_tls=True,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
        )
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {to_email}: {e}")
        return False


async def send_bulk(emails: List[str], subject: str, html_body: str) -> int:
    """Send email to multiple recipients, returns count sent"""
    count = 0
    for email in emails:
        ok = await send_email(email, subject, html_body)
        if ok:
            count += 1
    return count


def render_confirmation_email(name: str, inv_id: int) -> str:
    """Email sent right after successful payment"""
    return f"""
<!DOCTYPE html><html lang="ru"><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f9f9f9">
<div style="background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
  <img src="https://i.ibb.co/dJMk5M1h/40-x-40.png" width="48" style="margin-bottom:16px">
  <h1 style="color:#164E63;font-size:24px;margin:0 0 8px">Вы зарегистрированы!</h1>
  <p style="color:#475569;font-size:16px">Привет, <strong>{name}</strong>! Ваше место на форуме <strong>«{FORUM_NAME}»</strong> подтверждено.</p>
  <div style="background:#ECFEFF;border-radius:8px;padding:16px;margin:20px 0">
    <p style="margin:0;color:#164E63;font-weight:600">📅 Даты: {FORUM_DATES}</p>
    <p style="margin:8px 0 0;color:#164E63">⏰ Начало: 11:00 МСК каждый день</p>
    <p style="margin:8px 0 0;color:#164E63">🔢 Номер заказа: #{inv_id}</p>
  </div>
  <p style="color:#475569">Ссылки на прямые эфиры придут вам на этот email за 30 минут до начала каждого дня.</p>
  <p style="color:#94A3B8;font-size:14px;margin-top:32px">Если у вас есть вопросы, напишите нам: <a href="mailto:info@bigmoneychina.tech" style="color:#0891B2">info@bigmoneychina.tech</a></p>
</div>
</body></html>"""


def render_reminder_email(name: str, day: int, mts_link: str) -> str:
    """Reminder email with stream link, sent 30min before"""
    date_map = {1: "21 апреля", 2: "22 апреля", 3: "23 апреля"}
    return f"""
<!DOCTYPE html><html lang="ru"><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f9f9f9">
<div style="background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
  <img src="https://i.ibb.co/dJMk5M1h/40-x-40.png" width="48" style="margin-bottom:16px">
  <h1 style="color:#164E63;font-size:24px;margin:0 0 8px">⏰ Форум начинается через 30 минут!</h1>
  <p style="color:#475569;font-size:16px">Привет, <strong>{name}</strong>! День {day} ({date_map.get(day,"")}) форума «{FORUM_NAME}» начинается в <strong>11:00 МСК</strong>.</p>
  <a href="{mts_link}" style="display:inline-block;background:linear-gradient(135deg,#0891B2,#059669);color:#fff;text-decoration:none;padding:16px 32px;border-radius:100px;font-size:18px;font-weight:700;margin:20px 0">
    🎬 Войти в эфир
  </a>
  <p style="color:#94A3B8;font-size:14px;margin-top:32px">Ссылка действительна только для вас. Не передавайте её другим.</p>
</div>
</body></html>"""
