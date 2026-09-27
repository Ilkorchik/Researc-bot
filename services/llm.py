import httpx

from config import OLLAMA_MODEL, OLLAMA_URL, REQUEST_TIMEOUT
from models import Article


def _article_text(article: Article) -> str:
    return f"""
Название: {article.title}
Авторы: {", ".join(article.authors) or "не указаны"}
Год: {article.year or "не указан"}
Журнал/источник: {article.journal or article.source}
DOI: {article.doi or "нет"}
Аннотация: {article.abstract or "нет аннотации"}
Ссылка: {article.url or "нет"}
""".strip()


async def analyze_article(article: Article) -> str:
    prompt = f"""
Ты научный ассистент для университетского исследовательского проекта.
Проанализируй библиографическую запись научной статьи ниже.

Критические правила:
- Не выдумывай факты, методы, результаты или выводы, которых нет в переданных данных.
- Если есть только библиографическая запись и аннотация, прямо укажи, что анализ ограничен ими.
- Не выдавай предположение за результат эксперимента.
- Отвечай на русском языке.

Структура ответа:

1. КРАТКОЕ САММАРИ
5-8 предложений о том, что можно установить из доступных данных.

2. НАУЧНЫЙ РАЗБОР
- цель работы;
- объект/система;
- методы;
- основные результаты;
- механизм переноса, если он описан в доступных данных;
- связь с диссоциацией/рекомбинацией молекул воды и транспортными процессами;
- ограничения анализа.

3. ПЕРЕВОД
- название статьи на русский;
- аннотация на русский, если аннотация предоставлена.

4. БИБЛИОГРАФИЯ
- DOI;
- исходная ссылка.

Статья:
{_article_text(article)}
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Ты аккуратный научный ассистент. Работаешь только с предоставленными данными и явно отмечаешь ограничения."
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT * 6) as client:
        response = await client.post(f"{OLLAMA_URL.rstrip('/')}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()

    content = data.get("message", {}).get("content", "").strip()
    if not content:
        return "Локальная модель не вернула текст анализа."

    return content
