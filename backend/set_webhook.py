"""Set Telegram webhook. Run once after deploy."""
import asyncio, httpx, os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
BASE_URL = os.getenv("BASE_URL", "https://bigmoneychina.tech")


async def main():
    webhook_url = f"{BASE_URL}/tg/webhook"
    async with httpx.AsyncClient() as c:
        r = await c.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook",
                         json={"url": webhook_url})
        print(r.json())

asyncio.run(main())
