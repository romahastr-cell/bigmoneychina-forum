"""Telegram bot: admin notifications + email inbox + mailing management"""
import os
import httpx
import asyncio
import imaplib
import email
import json
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SMTP_USER = os.getenv("SMTP_USER", "info@bigmoneychina.tech")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
IMAP_HOST = os.getenv("IMAP_HOST", "imap.hosting.reg.ru")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))

# Bot conversation state
_state: dict = {}
# Store last seen email UIDs to avoid duplicates
_seen_uids: set = set()


async def send_message(chat_id: str, text: str, parse_mode: str = "HTML",
                       reply_markup: dict = None) -> bool:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_URL}/sendMessage", json=payload)
        return r.status_code == 200


async def notify_new_registration(name: str, email: str, phone: str,
                                   inv_id: int, amount: float,
                                   invited_by: Optional[str] = None,
                                   tg_login: Optional[str] = None):
    """Notify admin about new paid registration"""
    invited_str = f"\n👤 Пригласил: <b>{invited_by}</b>" if invited_by else ""
    tg_str = f"\n💬 Telegram: @{tg_login}" if tg_login else ""
    text = (
        f"✅ <b>Новая оплата!</b>\n\n"
        f"👤 Имя: <b>{name}</b>\n"
        f"📧 Email: <code>{email}</code>\n"
        f"📱 Телефон: <code>{phone}</code>"
        f"{invited_str}"
        f"{tg_str}\n"
        f"💰 Сумма: <b>{amount:.0f} ₽</b>\n"
        f"🔢 Заказ: <code>#{inv_id}</code>"
    )
    await send_message(ADMIN_CHAT_ID, text)


def _decode_header_str(h) -> str:
    parts = decode_header(h or "")
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result)


def _get_email_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            pass
    return body[:3000].strip()


async def check_inbox_once(db_session=None) -> list:
    """Check IMAP inbox, return list of new emails"""
    if not SMTP_PASSWORD:
        return []
    new_emails = []
    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        imap.login(SMTP_USER, SMTP_PASSWORD)
        imap.select("INBOX")
        status, data = imap.search(None, "UNSEEN")
        if status != "OK":
            imap.logout()
            return []
        uids = data[0].split()
        for uid in uids[-10:]:  # max 10 at a time
            uid_str = uid.decode()
            if uid_str in _seen_uids:
                continue
            status, msg_data = imap.fetch(uid, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            sender = _decode_header_str(msg.get("From", ""))
            subject = _decode_header_str(msg.get("Subject", "(без темы)"))
            body = _get_email_body(msg)
            new_emails.append({
                "uid": uid_str,
                "from": sender,
                "subject": subject,
                "body": body,
            })
            _seen_uids.add(uid_str)
        imap.logout()
    except Exception as e:
        print(f"[IMAP] Error: {e}")
    return new_emails


async def notify_new_emails():
    """Called periodically — forward new emails to admin TG"""
    new = await check_inbox_once()
    for em in new:
        text = (
            f"📨 <b>Новое письмо!</b>\n"
            f"От: <code>{em['from']}</code>\n"
            f"Тема: <b>{em['subject']}</b>\n\n"
            f"{em['body'][:1500]}"
        )
        keyboard = {
            "inline_keyboard": [[
                {"text": "✉️ Ответить", "callback_data": f"reply:{em['from'].split('<')[-1].strip('>')}"}
            ]]
        }
        await send_message(ADMIN_CHAT_ID, text, reply_markup=keyboard)


async def process_update(update: dict, db_session):
    """Process incoming Telegram update"""
    # Handle callback query (inline button press)
    if "callback_query" in update:
        cq = update["callback_query"]
        chat_id = str(cq["message"]["chat"]["id"])
        data = cq.get("data", "")
        if chat_id != ADMIN_CHAT_ID:
            return
        if data.startswith("reply:"):
            reply_to = data[6:]
            _state[chat_id] = {"step": "reply_text", "reply_to": reply_to}
            await send_message(chat_id,
                f"✉️ Введите текст ответа для <code>{reply_to}</code>:\n\n/cancel — отмена")
        # Acknowledge callback
        async with httpx.AsyncClient() as c:
            await c.post(f"{API_URL}/answerCallbackQuery",
                         json={"callback_query_id": cq["id"]})
        return

    msg = update.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "").strip()

    if chat_id != ADMIN_CHAT_ID:
        await send_message(chat_id, "⛔ Доступ запрещён.")
        return

    # Handle conversation state
    if chat_id in _state:
        state = _state[chat_id]

        if state["step"] == "mail_subject":
            state["subject"] = text
            state["step"] = "mail_body"
            await send_message(chat_id,
                "✉️ Введите текст письма (HTML поддерживается):\n\n/cancel — отмена")
            return

        elif state["step"] == "mail_body":
            subject = state["subject"]
            html_body = text
            del _state[chat_id]
            from app.email_service import send_bulk
            from sqlalchemy import select
            from app.database import Registration
            result = await db_session.execute(
                select(Registration.email, Registration.name).where(Registration.paid == True))
            rows = result.all()
            emails = [r.email for r in rows]
            if not emails:
                await send_message(chat_id, "📭 Нет оплативших участников.")
                return
            await send_message(chat_id, f"📤 Отправляю {len(emails)} участникам...")
            count = await send_bulk(emails, subject, html_body)
            await send_message(chat_id, f"✅ Отправлено: <b>{count}/{len(emails)}</b>")
            return

        elif state["step"] == "reply_text":
            reply_to = state["reply_to"]
            del _state[chat_id]
            from app.email_service import send_email
            ok = await send_email(
                to_email=reply_to,
                subject="Re: Ваш вопрос — Форум Технологии и Бизнес",
                html_body=f"<p>{text.replace(chr(10), '<br>')}</p>"
            )
            if ok:
                await send_message(chat_id, f"✅ Ответ отправлен на <code>{reply_to}</code>")
            else:
                await send_message(chat_id, f"❌ Ошибка отправки на <code>{reply_to}</code>")
            return

    # Commands
    if text in ("/start", "/help"):
        await send_message(chat_id, (
            "👋 <b>Админ-панель форума BMC</b>\n\n"
            "📊 /stats — статистика регистраций\n"
            "👥 /list — последние 10 участников\n"
            "✉️ /mail — email-рассылка всем оплатившим\n"
            "📨 /inbox — проверить входящие письма\n"
            "📅 /forums — список форумов\n"
            "❓ /help — эта справка"
        ))

    elif text == "/stats":
        from sqlalchemy import select, func
        from app.database import Registration
        total = await db_session.scalar(select(func.count()).select_from(Registration))
        paid = await db_session.scalar(
            select(func.count()).select_from(Registration).where(Registration.paid == True))
        await send_message(chat_id,
            f"📊 <b>Статистика</b>\n\n"
            f"👥 Всего заявок: <b>{total}</b>\n"
            f"✅ Оплатили: <b>{paid}</b>\n"
            f"⏳ Не оплатили: <b>{total - paid}</b>")

    elif text == "/list":
        from sqlalchemy import select
        from app.database import Registration
        result = await db_session.execute(
            select(Registration).where(Registration.paid == True)
            .order_by(Registration.paid_at.desc()).limit(10))
        regs = result.scalars().all()
        if not regs:
            await send_message(chat_id, "📭 Нет оплативших.")
            return
        lines = ["👥 <b>Последние 10 участников:</b>\n"]
        for r in regs:
            tg = f" @{r.telegram_login}" if r.telegram_login else ""
            lines.append(f"• {r.name} — <code>{r.email}</code>{tg}")
        await send_message(chat_id, "\n".join(lines))

    elif text == "/mail":
        _state[chat_id] = {"step": "mail_subject"}
        await send_message(chat_id,
            "✉️ <b>Email-рассылка всем оплатившим</b>\n\n"
            "Введите тему письма:")

    elif text == "/inbox":
        await send_message(chat_id, "📨 Проверяю почту info@bigmoneychina.tech...")
        new = await check_inbox_once()
        if not new:
            await send_message(chat_id, "📭 Новых писем нет.")
        else:
            for em in new:
                text_out = (
                    f"📨 <b>Письмо</b>\n"
                    f"От: <code>{em['from']}</code>\n"
                    f"Тема: <b>{em['subject']}</b>\n\n"
                    f"{em['body'][:1500]}"
                )
                keyboard = {"inline_keyboard": [[
                    {"text": "✉️ Ответить",
                     "callback_data": f"reply:{em['from'].split('<')[-1].strip('>')}"}
                ]]}
                await send_message(chat_id, text_out, reply_markup=keyboard)

    elif text == "/forums":
        from sqlalchemy import select
        from app.database import Forum
        result = await db_session.execute(
            select(Forum).order_by(Forum.id.desc()).limit(5))
        forums = result.scalars().all()
        if not forums:
            await send_message(chat_id, "📭 Нет форумов.")
            return
        lines = ["📅 <b>Форумы:</b>\n"]
        for f in forums:
            active = "✅" if f.is_active else "❌"
            lines.append(f"{active} [{f.id}] {f.name} — {f.dates} — {f.price:.0f}₽")
        await send_message(chat_id, "\n".join(lines))

    elif text == "/cancel":
        if chat_id in _state:
            del _state[chat_id]
            await send_message(chat_id, "❌ Отменено.")
        else:
            await send_message(chat_id, "Нечего отменять.")

    else:
        await send_message(chat_id, "❓ Неизвестная команда. /help — список команд.")
