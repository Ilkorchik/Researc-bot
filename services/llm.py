from openai import AsyncOpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from models import Article


def _article_text(article: Article) -> str:
    return f"""
Название: {article.title}
Авторы: {", ".join(article.authors) or "не указаны"}
Год: {article.year or "не указан"}
Журнал/источник: {article.journal or article.source}
DOI: {article.doi or "нет"}
Аннотация: {article.abstract or "нет аннотации"}
""".strip()


async def analyze_article(article: Article) -> str:
    if not OPENAI_API_KEY:
        return "OPENAI_API_KEY не задан. Добавьте ключ в .env."

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
Ты научный ассистент. Проанализируй библиографическую запись ниже.
Не выдумывай факты, которых нет в тексте.

Нужно вернуть на русском языке:

1. Краткое саммари (5-8 предложений).
2. Научный анализ:
   - цель работы;
   - объект/система;
   - методы;
   - основные результаты;
   - что авторы утверждают о механизме переноса;
   - ограничения и что нельзя заключить из доступной аннотации.
3. Перевод названия на русский.
4. Перевод аннотации на русский.
5. DOI и исходную ссылку.

Если полного текста статьи нет, прямо укажи, что анализ ограничен библиографическими данными/аннотацией.

Статья:
{_article_text(article)}
"""

    response = await client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
    )
    return response.output_text
