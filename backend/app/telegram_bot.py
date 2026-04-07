"""Telegram bot: admin notifications + mailing management"""
import os
import httpx
import asyncio
from typing import Optional

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Bot state for conversation
_pending_mails: dict = {}  # chat_id -> {"step": "subject"|"body", "subject": str}


async def send_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        })
        return r.status_code == 200


async def notify_new_registration(name: str, email: str, phone: str,
                                   inv_id: int, amount: float,
                                   invited_by: Optional[str] = None,
                                   tg_login: Optional[str] = None):
    """Send new paid registration notification to admin"""
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


async def process_update(update: dict, db_session):
    """Process incoming Telegram update (webhook)"""
    msg = update.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "").strip()

    # Security: only admin
    if chat_id != ADMIN_CHAT_ID:
        await send_message(chat_id, "⛔ Доступ запрещён.")
        return

    # Handle ongoing mail composition
    if chat_id in _pending_mails:
        state = _pending_mails[chat_id]
        if state["step"] == "subject":
            state["subject"] = text
            state["step"] = "body"
            await send_message(chat_id,
                "✉️ Введите текст письма (HTML поддерживается).\n\n"
                "Используй /cancel для отмены.")
            return
        elif state["step"] == "body":
            subject = state["subject"]
            html_body = text
            del _pending_mails[chat_id]
            # Import here to avoid circular
            from app.email_service import send_bulk
            from sqlalchemy import select
            from app.database import Registration
            result = await db_session.execute(
                select(Registration.email, Registration.name).where(Registration.paid == True)
            )
            rows = result.all()
            emails = [r.email for r in rows]
            if not emails:
                await send_message(chat_id, "📭 Нет оплативших участников для рассылки.")
                return
            await send_message(chat_id,
                f"📤 Отправляю рассылку {len(emails)} участникам...\n"
                f"Тема: <b>{subject}</b>")
            count = await send_bulk(emails, subject, html_body)
            await send_message(chat_id,
                f"✅ Рассылка отправлена!\n"
                f"Доставлено: <b>{count}/{len(emails)}</b>")
            return

    # Commands
    if text == "/start" or text == "/help":
        await send_message(chat_id, (
            "👋 <b>Админ-панель форума</b>\n\n"
            "Доступные команды:\n"
            "/stats — статистика регистраций\n"
            "/list — последние 10 участников\n"
            "/mail — создать email-рассылку\n"
            "/forums — список форумов\n"
            "/help — это сообщение"
        ))

    elif text == "/stats":
        from sqlalchemy import select, func
        from app.database import Registration
        total = await db_session.scalar(select(func.count()).select_from(Registration))
        paid = await db_session.scalar(
            select(func.count()).select_from(Registration).where(Registration.paid == True))
        unpaid = total - paid
        await send_message(chat_id,
            f"📊 <b>Статистика</b>\n\n"
            f"👥 Всего заявок: <b>{total}</b>\n"
            f"✅ Оплатили: <b>{paid}</b>\n"
            f"⏳ Не оплатили: <b>{unpaid}</b>")

    elif text == "/list":
        from sqlalchemy import select
        from app.database import Registration
        result = await db_session.execute(
            select(Registration).where(Registration.paid == True)
            .order_by(Registration.paid_at.desc()).limit(10)
        )
        regs = result.scalars().all()
        if not regs:
            await send_message(chat_id, "📭 Нет оплативших участников.")
            return
        lines = ["👥 <b>Последние 10 участников:</b>\n"]
        for r in regs:
            tg = f" @{r.telegram_login}" if r.telegram_login else ""
            lines.append(f"• {r.name} — <code>{r.email}</code>{tg}")
        await send_message(chat_id, "\n".join(lines))

    elif text == "/mail":
        _pending_mails[chat_id] = {"step": "subject"}
        await send_message(chat_id,
            "✉️ <b>Создание рассылки</b>\n\n"
            "Письмо будет отправлено ВСЕМ оплатившим участникам.\n\n"
            "Введите тему письма:")

    elif text == "/cancel":
        if chat_id in _pending_mails:
            del _pending_mails[chat_id]
            await send_message(chat_id, "❌ Рассылка отменена.")
        else:
            await send_message(chat_id, "Нечего отменять.")

    elif text == "/forums":
        from sqlalchemy import select
        from app.database import Forum
        result = await db_session.execute(select(Forum).order_by(Forum.id.desc()).limit(5))
        forums = result.scalars().all()
        if not forums:
            await send_message(chat_id, "📭 Нет форумов в базе.")
            return
        lines = ["📅 <b>Форумы:</b>\n"]
        for f in forums:
            active = "✅" if f.is_active else "❌"
            lines.append(f"{active} [{f.id}] {f.name} — {f.dates} — {f.price:.0f}₽")
        await send_message(chat_id, "\n".join(lines))

    else:
        await send_message(chat_id, "❓ Неизвестная команда. /help — список команд.")
