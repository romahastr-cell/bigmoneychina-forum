"""FastAPI backend for bigmoneychina.tech forum registration"""
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from contextlib import asynccontextmanager
import os
import json

from app.database import get_db, init_db, Registration, Forum
from app.robokassa import build_payment_url, verify_result, build_ok_response
from app.email_service import send_email, render_confirmation_email
from app.telegram_bot import notify_new_registration, process_update, send_message

ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
BASE_URL = os.getenv("BASE_URL", "https://bigmoneychina.tech")
FORUM_PRICE = float(os.getenv("FORUM_PRICE", "501.00"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

app.add_middleware(CORSMiddleware,
    allow_origins=["https://bigmoneychina.tech", "http://bigmoneychina.tech"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"])


# ─── Registration Form ────────────────────────────────────────────────────────

@app.get("/register", response_class=HTMLResponse)
async def register_form(db: AsyncSession = Depends(get_db)):
    """Registration page embedded into the site"""
    result = await db.execute(select(Forum).where(Forum.is_active == True).order_by(Forum.id.desc()))
    forum = result.scalars().first()
    if not forum:
        return HTMLResponse("<p>Регистрация временно закрыта.</p>", status_code=503)

    html = f"""<!DOCTYPE html><html lang="ru">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Регистрация — {forum.name}</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#ECFEFF,#F0F9FF);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
    .card{{background:#fff;border-radius:20px;padding:40px;max-width:480px;width:100%;box-shadow:0 4px 24px rgba(0,0,0,0.1)}}
    .logo{{display:flex;align-items:center;gap:10px;margin-bottom:24px}}
    .logo img{{width:40px;height:40px}}
    .logo-text{{font-weight:700;color:#164E63;font-size:16px;line-height:1.2}}
    h1{{color:#164E63;font-size:24px;font-weight:700;margin-bottom:6px}}
    .subtitle{{color:#475569;font-size:15px;margin-bottom:28px}}
    .price-badge{{background:#ECFEFF;color:#0891B2;border:1.5px solid #BAE6FD;border-radius:100px;padding:8px 20px;font-weight:700;font-size:18px;display:inline-block;margin-bottom:24px}}
    label{{display:block;color:#374151;font-size:14px;font-weight:500;margin-bottom:6px}}
    input{{width:100%;padding:12px 16px;border:1.5px solid #E2E8F0;border-radius:10px;font-size:15px;font-family:inherit;transition:.2s;outline:none}}
    input:focus{{border-color:#0891B2;box-shadow:0 0 0 3px rgba(8,145,178,0.1)}}
    input.required-field{{border-color:#E2E8F0}}
    .field{{margin-bottom:18px}}
    .optional-label{{color:#94A3B8;font-weight:400;font-size:12px;margin-left:4px}}
    .submit-btn{{width:100%;background:linear-gradient(135deg,#0891B2,#059669);color:#fff;border:none;padding:16px;border-radius:100px;font-size:17px;font-weight:700;cursor:pointer;transition:.2s;margin-top:8px}}
    .submit-btn:hover{{transform:translateY(-2px);box-shadow:0 8px 24px rgba(8,145,178,0.3)}}
    .submit-btn:disabled{{opacity:.6;cursor:not-allowed;transform:none}}
    .secure{{color:#94A3B8;font-size:12px;text-align:center;margin-top:14px}}
    .divider{{height:1px;background:#F1F5F9;margin:20px 0}}
    .error{{color:#DC2626;font-size:13px;margin-top:4px;display:none}}
    .consent-block {{ margin: 16px 0; }}
    .consent-label {{ display: flex; gap: 10px; align-items: flex-start; cursor: pointer; color: #475569; font-size: 14px; line-height: 1.5; }}
    .consent-label input[type="checkbox"] {{ width: 18px; height: 18px; min-width: 18px; margin-top: 2px; accent-color: #0891B2; cursor: pointer; }}
    .consent-label a {{ color: #0891B2; text-decoration: underline; }}
    .submit-btn:disabled {{ opacity: 0.45; cursor: not-allowed; transform: none !important; box-shadow: none !important; }}
  </style>
</head>
<body>
<div class="card">
  <div class="logo">
    <img src="https://i.ibb.co/dJMk5M1h/40-x-40.png" alt="BMC">
    <div class="logo-text">Big Money China<br><span style="font-weight:400;color:#64748B">Форум</span></div>
  </div>
  <h1>{forum.name}</h1>
  <p class="subtitle">📅 {forum.dates} · Онлайн, 11:00 МСК</p>
  <div class="price-badge">Билет — {forum.price:.0f} ₽</div>

  <form id="regForm" method="POST" action="/register">
    <input type="hidden" name="forum_id" value="{forum.id}">

    <div class="field">
      <label for="name">Ваше имя *</label>
      <input type="text" id="name" name="name" placeholder="Иван Иванов" required autocomplete="name">
    </div>

    <div class="field">
      <label for="email">Email *</label>
      <input type="email" id="email" name="email" placeholder="ivan@mail.ru" required autocomplete="email">
      <div class="error" id="email-error">Введите корректный email</div>
    </div>

    <div class="field">
      <label for="phone">Телефон *</label>
      <input type="tel" id="phone" name="phone" placeholder="+7 900 000 00 00" required autocomplete="tel">
    </div>

    <div class="divider"></div>

    <div class="field">
      <label for="invited_by">Кто вас пригласил <span class="optional-label">(необязательно)</span></label>
      <input type="text" id="invited_by" name="invited_by" placeholder="Имя или ник пригласившего">
    </div>

    <div class="field">
      <label for="telegram_login">Ваш Telegram <span class="optional-label">(необязательно)</span></label>
      <input type="text" id="telegram_login" name="telegram_login" placeholder="@username">
    </div>

    <div class="divider"></div>

    <div class="consent-block">
      <label class="consent-label">
        <input type="checkbox" id="consent" name="consent" required onchange="document.getElementById('submitBtn').disabled=!this.checked">
        <span>Я ознакомлен(а) и согласен(а) с <a href="https://bigmoneychina.tech/offer.html" target="_blank">договором оферты</a> и <a href="https://bigmoneychina.tech/privacy.html" target="_blank">политикой конфиденциальности</a></span>
      </label>
    </div>

    <button type="submit" class="submit-btn" id="submitBtn" disabled>
      Перейти к оплате →
    </button>
    <p class="secure">🔒 Безопасная оплата через Robokassa · SSL-шифрование</p>
  </form>
</div>
<script>
document.getElementById('regForm').addEventListener('submit', function(e) {{
  var btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Переходим к оплате...';
}});
// Phone mask
document.getElementById('phone').addEventListener('input', function(e) {{
  var v = e.target.value.replace(/\D/g,'');
  if(v.length>0 && v[0]!='7' && v[0]!='8') v='7'+v;
  if(v.length>11) v=v.substr(0,11);
  if(v.length==0) {{ e.target.value=''; return; }}
  var f='+'+v[0];
  if(v.length>1) f+=' ('+v.substr(1,3);
  if(v.length>4) f+=') '+v.substr(4,3);
  if(v.length>7) f+='-'+v.substr(7,2);
  if(v.length>9) f+='-'+v.substr(9,2);
  e.target.value=f;
}});
// TG @ prefix
document.getElementById('telegram_login').addEventListener('blur', function(e) {{
  var v = e.target.value.trim();
  if(v && !v.startsWith('@')) e.target.value = '@'+v;
}});
</script>
</body></html>"""
    return HTMLResponse(html)


@app.post("/register")
async def register_submit(
    request: Request,
    forum_id: int = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    invited_by: str = Form(default=""),
    telegram_login: str = Form(default=""),
    db: AsyncSession = Depends(get_db)
):
    """Handle registration form, create pending record, redirect to Robokassa"""
    # Get active forum
    forum = await db.get(Forum, forum_id)
    if not forum or not forum.is_active:
        raise HTTPException(400, "Форум не найден или регистрация закрыта")

    # Generate unique InvId
    import random
    inv_id = random.randint(100000, 9999999)

    # Create pending registration
    reg = Registration(
        inv_id=inv_id,
        name=name.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        invited_by=invited_by.strip() or None,
        telegram_login=telegram_login.strip().lstrip("@") or None,
        forum_id=forum_id,
        amount=forum.price,
        paid=False,
    )
    db.add(reg)
    await db.commit()

    # Build Robokassa URL
    payment_url = build_payment_url(
        inv_id=inv_id,
        amount=forum.price,
        description=f"Билет на форум «{forum.name}» {forum.dates}",
        email=email,
        item_name=f"Билет на форум «{forum.name}»",
    )
    return RedirectResponse(payment_url, status_code=303)


# ─── Robokassa Callbacks ──────────────────────────────────────────────────────

@app.post("/payment/result")
async def payment_result(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Robokassa ResultURL — called server-to-server on successful payment"""
    form = await request.form()
    out_sum = form.get("OutSum", "")
    inv_id = form.get("InvId", "")
    signature = form.get("SignatureValue", "")

    if not verify_result(out_sum, inv_id, signature):
        raise HTTPException(400, "Bad signature")

    # Find registration
    result = await db.execute(
        select(Registration).where(Registration.inv_id == int(inv_id)))
    reg = result.scalars().first()
    if not reg:
        raise HTTPException(404, "Registration not found")

    if not reg.paid:
        reg.paid = True
        reg.paid_at = datetime.utcnow()
        reg.robokassa_data = str(dict(form))
        await db.commit()

        # Send confirmation email
        try:
            html = render_confirmation_email(reg.name, reg.inv_id)
            await send_email(reg.email, f"✅ Вы зарегистрированы на форум!", html)
            reg.email_sent = True
            await db.commit()
        except Exception as e:
            print(f"[EMAIL] Error: {e}")

        # Notify admin via Telegram
        try:
            await notify_new_registration(
                name=reg.name,
                email=reg.email,
                phone=reg.phone or "—",
                inv_id=reg.inv_id,
                amount=reg.amount,
                invited_by=reg.invited_by,
                tg_login=reg.telegram_login,
            )
        except Exception as e:
            print(f"[TG] Error: {e}")

    return PlainTextResponse(build_ok_response(inv_id))


@app.get("/payment/success", response_class=HTMLResponse)
async def payment_success(InvId: int = 0):
    return HTMLResponse(f"""<!DOCTYPE html><html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Оплата прошла успешно</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<meta http-equiv="refresh" content="5;url=https://bigmoneychina.tech">
<style>body{{font-family:'Inter',sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;background:linear-gradient(135deg,#ECFEFF,#F0FDF4);margin:0}}
.card{{background:#fff;border-radius:20px;padding:48px;text-align:center;max-width:440px;box-shadow:0 4px 24px rgba(0,0,0,0.1)}}
h1{{color:#059669;font-size:28px;margin:16px 0 8px}}p{{color:#475569;font-size:16px;line-height:1.6}}
a{{color:#0891B2;text-decoration:none;font-weight:600}}</style></head>
<body><div class="card">
  <div style="font-size:64px">🎉</div>
  <h1>Оплата прошла!</h1>
  <p>Заказ <strong>#{InvId}</strong> подтверждён.<br>Письмо с подтверждением отправлено на ваш email.</p>
  <p style="margin-top:16px;color:#94A3B8;font-size:14px">Через 5 секунд вы будете перенаправлены на сайт...</p>
  <p style="margin-top:16px"><a href="https://bigmoneychina.tech">← На главную</a></p>
</div></body></html>""")


@app.get("/payment/fail", response_class=HTMLResponse)
async def payment_fail():
    return HTMLResponse("""<!DOCTYPE html><html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ошибка оплаты</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>body{font-family:'Inter',sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;background:#FFF1F2;margin:0}
.card{background:#fff;border-radius:20px;padding:48px;text-align:center;max-width:440px;box-shadow:0 4px 24px rgba(0,0,0,0.1)}
h1{color:#DC2626;font-size:28px;margin:16px 0 8px}p{color:#475569;font-size:16px}a{color:#0891B2;text-decoration:none;font-weight:600}</style></head>
<body><div class="card">
  <div style="font-size:64px">😕</div>
  <h1>Оплата не прошла</h1>
  <p>Попробуйте ещё раз или напишите нам:<br><a href="mailto:info@bigmoneychina.tech">info@bigmoneychina.tech</a></p>
  <p style="margin-top:20px"><a href="/register">← Попробовать снова</a></p>
</div></body></html>""")


# ─── Telegram Webhook ─────────────────────────────────────────────────────────

@app.post("/tg/webhook")
async def tg_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    update = await request.json()
    await process_update(update, db)
    return {"ok": True}


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
