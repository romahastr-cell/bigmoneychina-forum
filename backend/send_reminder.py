"""Send reminder emails with MTS Link 30 min before each day. 
Usage: python send_reminder.py <day_number>  (1, 2, or 3)
"""
import asyncio, sys, os
from dotenv import load_dotenv
load_dotenv()

from app.database import AsyncSessionLocal, Registration
from app.email_service import send_email, render_reminder_email
from sqlalchemy import select


async def main():
    day = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    link_map = {
        1: os.getenv("MTS_LINK_DAY1", "#"),
        2: os.getenv("MTS_LINK_DAY2", "#"),
        3: os.getenv("MTS_LINK_DAY3", "#"),
    }
    mts_link = link_map.get(day, "#")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Registration).where(Registration.paid == True)
        )
        regs = result.scalars().all()

    print(f"Sending day {day} reminders to {len(regs)} participants...")
    count = 0
    for reg in regs:
        html = render_reminder_email(reg.name, day, mts_link)
        ok = await send_email(
            reg.email,
            f"⏰ Форум начинается через 30 минут — День {day}!",
            html
        )
        if ok:
            count += 1

    print(f"✅ Sent: {count}/{len(regs)}")

asyncio.run(main())
