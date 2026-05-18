import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8972047923:AAHdMMLWBMxfcOI_xQkgWRn_lfZ4ph347lM"


async def get_first_anekdot() -> str:
    url = "https://www.anekdot.ru/last/anekdot/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Анекдоты лежат в div.text с родителем div.topicbox
    topic = soup.select_one("div.topicbox div.text")
    if not topic:
        return "Не удалось получить анекдот 😔"

    # Заменяем <br> на переносы строк
    for br in topic.find_all("br"):
        br.replace_with("\n")

    text = topic.get_text(separator="").strip()
    return text


async def anekdot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ищу свежий анекдот...")
    try:
        text = await get_first_anekdot()
        await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Что-то пошло не так, попробуй позже 🤷")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("anekdot", anekdot_command))
    logger.info("Бот запущен. Жду команду /anekdot")
    app.run_polling()


if __name__ == "__main__":
    main()
