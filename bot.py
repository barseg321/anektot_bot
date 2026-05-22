import os
import asyncio
import random
import httpx
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OFFSET = 0

CATEGORIES = {
    "🔥 Злободневные": "https://www.anekdot.ru/last/burning/",
    "🕊 Без политики": "https://www.anekdot.ru/last/non_burning/",
    "😇 Приличные": "https://www.anekdot.ru/last/good/",
    "✍️ Авторские": "https://www.anekdot.ru/last/anekdot_original/",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}


async def scrape_anekdots(url: str, limit: int = 10) -> list[str]:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers=HEADERS)
        r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    topics = soup.select("div.topicbox div.text")
    results = []
    for topic in topics[:limit]:
        for br in topic.find_all("br"):
            br.replace_with("\n")
        text = topic.get_text(separator="").strip()
        if text:
            results.append(text)
    return results


async def send_message(chat_id: int, text: str, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{API}/sendMessage", json=payload)


async def answer_callback(callback_id: str):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{API}/answerCallbackQuery", json={"callback_query_id": callback_id})


async def get_updates(offset: int):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API}/getUpdates", params={"timeout": 25, "offset": offset})
        return r.json().get("result", [])


async def handle_anekdot(chat_id: int):
    await send_message(chat_id, "Ищу свежий анекдот...")
    anekdots = await scrape_anekdots("https://www.anekdot.ru/last/anekdot/", limit=1)
    text = anekdots[0] if anekdots else "Не удалось получить анекдот 😔"
    await send_message(chat_id, text)


async def handle_random(chat_id: int):
    await send_message(chat_id, "Ищу случайный анекдот...")
    anekdots = await scrape_anekdots("https://www.anekdot.ru/random/anekdot/", limit=10)
    text = random.choice(anekdots) if anekdots else "Не удалось получить анекдот 😔"
    await send_message(chat_id, text)


async def handle_top(chat_id: int):
    await send_message(chat_id, "Загружаю топ анекдотов дня...")
    anekdots = await scrape_anekdots("https://www.anekdot.ru/release/anekdot/day/", limit=5)
    if not anekdots:
        await send_message(chat_id, "Не удалось получить топ 😔")
        return
    for i, a in enumerate(anekdots, 1):
        await send_message(chat_id, f"⭐ #{i}\n\n{a}")
        await asyncio.sleep(0.5)


async def handle_category(chat_id: int):
    buttons = [[{"text": name, "callback_data": f"cat:{name}"}] for name in CATEGORIES]
    await send_message(chat_id, "Выбери категорию:", reply_markup={"inline_keyboard": buttons})


async def handle_callback(callback: dict):
    chat_id = callback["message"]["chat"]["id"]
    data = callback.get("data", "")
    await answer_callback(callback["id"])

    if data.startswith("cat:"):
        name = data[4:]
        url = CATEGORIES.get(name)
        if not url:
            await send_message(chat_id, "Неизвестная категория")
            return
        await send_message(chat_id, f"Загружаю: {name}...")
        anekdots = await scrape_anekdots(url, limit=10)
        text = random.choice(anekdots) if anekdots else "Не удалось получить анекдот 😔"
        await send_message(chat_id, text)


async def handle_start(chat_id: int):
    text = (
        "Привет! Я бот с анекдотами 🎭\n\n"
        "/anekdot — свежий анекдот\n"
        "/random — случайный анекдот\n"
        "/top — топ-5 анекдотов дня\n"
        "/category — выбрать категорию"
    )
    await send_message(chat_id, text)


async def main():
    global OFFSET
    print("Бот запущен!")
    while True:
        try:
            updates = await get_updates(OFFSET)
            for update in updates:
                OFFSET = update["update_id"] + 1

                # Обработка callback (кнопки)
                if "callback_query" in update:
                    await handle_callback(update["callback_query"])
                    continue

                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")
                if not chat_id:
                    continue

                if text.startswith("/start"):
                    await handle_start(chat_id)
                elif text.startswith("/anekdot"):
                    await handle_anekdot(chat_id)
                elif text.startswith("/random"):
                    await handle_random(chat_id)
                elif text.startswith("/top"):
                    await handle_top(chat_id)
                elif text.startswith("/category"):
                    await handle_category(chat_id)

        except Exception as e:
            print(f"Ошибка: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
