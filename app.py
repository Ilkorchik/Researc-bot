import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, MAX_RESULTS_PER_SOURCE
from services.search import search_all
from services.llm import analyze_article
from services.export import export_csv
from models import Article


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


HELP = """
<b>Научный бот-поисковик</b>

Отправьте обычным сообщением научный запрос.

Команды:
<code>/search &lt;запрос&gt;</code> — поиск
<code>/results</code> — последние результаты
<code>/analyze &lt;номер&gt;</code> — саммари + анализ + перевод
<code>/export</code> — выгрузить последний поиск в CSV
<code>/help</code> — справка

Источники:
arXiv, Scopus, Web of Science, eLIBRARY.
"""


def format_article(i: int, a: Article) -> str:
    lines = [f"<b>{i}. {a.title}</b>"]
    if a.authors:
        lines.append("Авторы: " + ", ".join(a.authors[:5]))
    if a.year:
        lines.append("Год: " + a.year)
    lines.append("Источник: " + a.source)
    if a.journal:
        lines.append("Журнал: " + a.journal)
    if a.doi:
        lines.append(f'DOI: <a href="https://doi.org/{a.doi}">{a.doi}</a>')
    if a.url:
        lines.append(f'<a href="{a.url}">Открыть запись</a>')
    if a.pdf_url:
        lines.append(f'<a href="{a.pdf_url}">PDF</a>')
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode=ParseMode.HTML)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP, parse_mode=ParseMode.HTML)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text(
            "Пример: /search water molecule dissociation transport"
        )
        return

    await update.message.reply_text(
        f"Ищу по источникам: arXiv, Scopus, Web of Science, eLIBRARY...\n"
        f"Лимит: до {MAX_RESULTS_PER_SOURCE} результатов на источник."
    )

    articles = await search_all(query)
    context.user_data["articles"] = articles
    context.user_data["query"] = query
    await send_results(update, articles)


async def text_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    await update.message.reply_text(
        f"Ищу по источникам: arXiv, Scopus, Web of Science, eLIBRARY...\n"
        f"Лимит: до {MAX_RESULTS_PER_SOURCE} результатов на источник."
    )

    articles = await search_all(query)
    context.user_data["articles"] = articles
    context.user_data["query"] = query
    await send_results(update, articles)


async def send_results(update: Update, articles: list[Article]):
    if not articles:
        await update.message.reply_text("Ничего не найдено.")
        return

    chunks = []
    current = ""

    for i, article in enumerate(articles, 1):
        block = format_article(i, article)
        if len(current) + len(block) + 3 > 3800:
            chunks.append(current)
            current = ""
        current += block + "\n\n"

    if current:
        chunks.append(current)

    await update.message.reply_text(
        f"<b>Найдено уникальных записей: {len(articles)}</b>",
        parse_mode=ParseMode.HTML,
    )

    for chunk in chunks:
        await update.message.reply_text(
            chunk,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )

    await update.message.reply_text(
        "Для анализа: /analyze 1\n"
        "Для CSV: /export"
    )


async def results_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    articles = context.user_data.get("articles", [])
    if not articles:
        await update.message.reply_text("Сначала выполните поиск.")
        return
    await send_results(update, articles)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    articles: list[Article] = context.user_data.get("articles", [])
    if not articles:
        await update.message.reply_text("Сначала выполните поиск.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Пример: /analyze 1")
        return

    index = int(context.args[0]) - 1
    if index < 0 or index >= len(articles):
        await update.message.reply_text("Нет статьи с таким номером.")
        return

    await update.message.reply_text("Готовлю саммари, научный разбор и перевод...")
    result = await analyze_article(articles[index])

    for start in range(0, len(result), 3800):
        await update.message.reply_text(result[start:start + 3800])


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    articles: list[Article] = context.user_data.get("articles", [])
    if not articles:
        await update.message.reply_text("Сначала выполните поиск.")
        return

    path = export_csv(articles, "exports/results.csv")
    with open(path, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename="scientific_search_results.csv",
            caption="Результаты последнего поиска.",
        )


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN в .env")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("results", results_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_search)
    )

    logger.info("Bot started")
    application.run_polling()


if __name__ == "__main__":
    main()
