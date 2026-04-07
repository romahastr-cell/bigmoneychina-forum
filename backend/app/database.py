from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./forum.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    inv_id = Column(Integer, unique=True, index=True)  # Robokassa invoice ID
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    invited_by = Column(String(200), nullable=True)    # кто пригласил
    telegram_login = Column(String(100), nullable=True) # логин в TG
    forum_id = Column(Integer, nullable=False, default=1)
    amount = Column(Float, nullable=False)
    paid = Column(Boolean, default=False)
    paid_at = Column(DateTime, nullable=True)
    email_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    robokassa_data = Column(Text, nullable=True)  # raw callback data


class Forum(Base):
    __tablename__ = "forums"

    id = Column(Integer, primary_key=True)
    name = Column(String(300), nullable=False)
    dates = Column(String(100), nullable=False)
    price = Column(Float, nullable=False, default=501.0)
    mts_link_day1 = Column(String(500), nullable=True)
    mts_link_day2 = Column(String(500), nullable=True)
    mts_link_day3 = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailCampaign(Base):
    __tablename__ = "email_campaigns"

    id = Column(Integer, primary_key=True)
    forum_id = Column(Integer, nullable=True)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    send_at = Column(DateTime, nullable=True)   # плановая отправка
    sent_at = Column(DateTime, nullable=True)   # фактическая
    sent_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
