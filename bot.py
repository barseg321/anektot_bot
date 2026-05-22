import os
import asyncio
import httpx
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OFFSET = 0


async def get_first_anekdot() -> str:
    url = "https://www.anekdot.ru/last/anekdot/"
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    topic = soup.select_one("div.topicbox div.text")
    if not topic:
        return "Не удалось получить анекдот 😔"
    for br in topic.find_all("br"):
        br.replace_with("\n")
    return topic.get_text(separator="").strip()


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text})


async def get_updates(offset: int):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API}/getUpdates", params={"timeout": 25, "offset": offset})
        return r.json().get("result", [])


async def main():
    global OFFSET
    print("Бот запущен. Жду команду /anekdot")
    while True:
        try:
            updates = await get_updates(OFFSET)
            for update in updates:
                OFFSET = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")
                if chat_id and text.startswith("/anekdot"):
                    await send_message(chat_id, "Ищу свежий анекдот...")
                    anekdot = await get_first_anekdot()
                    await send_message(chat_id, anekdot)
        except Exception as e:
            print(f"Ошибка: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
