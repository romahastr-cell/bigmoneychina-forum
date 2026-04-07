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
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Вы зарегистрированы на форум!</title>
</head>
<body style="margin:0;padding:0;background:#0D1B2A;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0D1B2A;padding:40px 20px">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0F3460,#164E63);border-radius:16px 16px 0 0;padding:36px 40px;text-align:center">
            <img src="https://i.ibb.co/dJMk5M1h/40-x-40.png" width="56" height="56" style="margin-bottom:16px;display:block;margin-left:auto;margin-right:auto">
            <div style="font-size:13px;letter-spacing:3px;color:#67E8F9;text-transform:uppercase;margin-bottom:8px">🇨🇳 Добро пожаловать</div>
            <h1 style="margin:0;color:#FFFFFF;font-size:28px;font-weight:700;line-height:1.3">Онлайн-форум<br>«Бизнес с Китаем»</h1>
          </td>
        </tr>

        <!-- Greeting -->
        <tr>
          <td style="background:#FFFFFF;padding:32px 40px">
            <p style="margin:0 0 20px;color:#1E293B;font-size:18px;font-weight:600">Привет, {name}! 👋</p>
            <p style="margin:0 0 16px;color:#475569;font-size:16px;line-height:1.7">
              Вы здесь. Это значит, что вы уже опередили тех, кто «подумает завтра».
              Завтра — слово, которое стоит миллионы упущенных возможностей.
              <strong style="color:#0891B2">Вы выбрали сегодня.</strong>
            </p>
            <p style="margin:0;color:#64748B;font-size:14px">Номер заказа: <strong style="color:#0891B2">#{inv_id}</strong></p>
          </td>
        </tr>

        <!-- Schedule -->
        <tr>
          <td style="background:#F8FAFC;padding:0 40px">
            <div style="border-top:2px solid #E2E8F0;padding:28px 0">
              <h2 style="margin:0 0 20px;color:#0F172A;font-size:18px;font-weight:700;letter-spacing:-0.3px">📅 РАСПИСАНИЕ</h2>

              <!-- Day 1 -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px">
                <tr>
                  <td style="background:#ECFEFF;border-left:4px solid #0891B2;border-radius:0 12px 12px 0;padding:16px 20px">
                    <div style="color:#0891B2;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px">День 1 · 21 апреля · 11:00–12:00 МСК</div>
                    <div style="color:#0F172A;font-size:16px;font-weight:600">«Почему Китай. И почему именно сейчас»</div>
                  </td>
                </tr>
              </table>

              <!-- Day 2 -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px">
                <tr>
                  <td style="background:#F0FDF4;border-left:4px solid #059669;border-radius:0 12px 12px 0;padding:16px 20px">
                    <div style="color:#059669;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px">День 2 · 22 апреля · 11:00–12:10 МСК</div>
                    <div style="color:#0F172A;font-size:16px;font-weight:600">«Технологии, которые нарушили старые правила»</div>
                  </td>
                </tr>
              </table>

              <!-- Day 3 -->
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#FFF7ED;border-left:4px solid #F59E0B;border-radius:0 12px 12px 0;padding:16px 20px">
                    <div style="color:#D97706;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px">День 3 · 23 апреля · 11:00–12:20 МСК</div>
                    <div style="color:#0F172A;font-size:16px;font-weight:600">«День денег»</div>
                  </td>
                </tr>
              </table>

              <p style="margin:20px 0 0;color:#64748B;font-size:14px;line-height:1.6">
                Каждый эфир — 60–75 минут концентрированной информации. Без воды, без мотивашек на полчаса. Только то, что меняет понимание бизнеса.
              </p>
            </div>
          </td>
        </tr>

        <!-- Rules -->
        <tr>
          <td style="background:#FFFFFF;padding:28px 40px">
            <h2 style="margin:0 0 20px;color:#0F172A;font-size:18px;font-weight:700">⚡ ТРИ ПРАВИЛА УЧАСТНИКА</h2>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:14px">
              <tr>
                <td width="36" style="vertical-align:top;padding-top:2px">
                  <div style="background:#0891B2;color:#fff;width:26px;height:26px;border-radius:50%;text-align:center;line-height:26px;font-weight:700;font-size:14px">1</div>
                </td>
                <td style="padding-left:14px;color:#374151;font-size:15px;line-height:1.6">
                  <strong>Проверьте почту за 15–30 минут до старта.</strong> Ссылка на эфир придёт прямо сюда — на ваш email. Пропустите — догнать будет сложно.
                </td>
              </tr>
            </table>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:14px">
              <tr>
                <td width="36" style="vertical-align:top;padding-top:2px">
                  <div style="background:#059669;color:#fff;width:26px;height:26px;border-radius:50%;text-align:center;line-height:26px;font-weight:700;font-size:14px">2</div>
                </td>
                <td style="padding-left:14px;color:#374151;font-size:15px;line-height:1.6">
                  <strong>Приходите к 11:00, а не к 11:15.</strong> Те, кто опаздывают, всегда упускают ключевую мысль, на которой строится весь день.
                </td>
              </tr>
            </table>

            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="36" style="vertical-align:top;padding-top:2px">
                  <div style="background:#F59E0B;color:#fff;width:26px;height:26px;border-radius:50%;text-align:center;line-height:26px;font-weight:700;font-size:14px">3</div>
                </td>
                <td style="padding-left:14px;color:#374151;font-size:15px;line-height:1.6">
                  <strong>Блокнот и ручка.</strong> Серьёзно. На этих цифрах, связях и стратегиях вы не найдёте ни одного открытого источника. Записывайте.
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Links notice -->
        <tr>
          <td style="background:linear-gradient(135deg,#0F3460,#164E63);padding:28px 40px;text-align:center">
            <p style="margin:0 0 8px;color:#67E8F9;font-size:14px;font-weight:600;letter-spacing:1px;text-transform:uppercase">🔗 Ссылки на эфиры</p>
            <p style="margin:0;color:#E0F2FE;font-size:16px;line-height:1.6">
              Ссылки на каждый день форума придут на этот email<br>
              <strong style="color:#FFFFFF">за 30 и за 15 минут до начала.</strong><br>
              Обязательно проверьте папку «Спам», если не увидите письмо.
            </p>
          </td>
        </tr>

        <!-- Support -->
        <tr>
          <td style="background:#F8FAFC;padding:24px 40px;border-radius:0 0 16px 16px">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="color:#64748B;font-size:14px;line-height:1.7">
                  <strong style="color:#374151">Служба заботы:</strong><br>
                  📱 Telegram: <a href="https://t.me/rezzotech" style="color:#0891B2;text-decoration:none">@rezzotech</a><br>
                  📧 Email: <a href="mailto:info@bigmoneychina.tech" style="color:#0891B2;text-decoration:none">info@bigmoneychina.tech</a>
                </td>
                <td align="right" style="vertical-align:middle">
                  <img src="https://i.ibb.co/dJMk5M1h/40-x-40.png" width="40" height="40">
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px;text-align:center">
            <p style="margin:0;color:#64748B;font-size:12px">
              © 2026 Big Money China · ИП Неретина Л.В.<br>
              Вы получили это письмо, так как зарегистрировались на форум.<br>
              <a href="https://bigmoneychina.tech" style="color:#0891B2;text-decoration:none">bigmoneychina.tech</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


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
