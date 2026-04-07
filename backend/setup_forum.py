"""Run once to create the first forum in the database"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from app.database import init_db, AsyncSessionLocal, Forum


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        forum = Forum(
            name=os.getenv("FORUM_NAME", "Технологии и Бизнес 2026"),
            dates=os.getenv("FORUM_DATES", "21–23 апреля 2026"),
            price=float(os.getenv("FORUM_PRICE", "501.00")),
            mts_link_day1=os.getenv("MTS_LINK_DAY1", ""),
            mts_link_day2=os.getenv("MTS_LINK_DAY2", ""),
            mts_link_day3=os.getenv("MTS_LINK_DAY3", ""),
            is_active=True,
        )
        db.add(forum)
        await db.commit()
        print(f"✅ Forum created: ID={forum.id}")


asyncio.run(main())
