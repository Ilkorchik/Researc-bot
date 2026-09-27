import asyncio
from collections import OrderedDict

from config import MAX_RESULTS_PER_SOURCE, SCOPUS_API_KEY, WOS_API_KEY
from dbs.arxiv import search_arxiv
from dbs.scopus import search_scopus
from dbs.wos import search_wos
from dbs.elibrary import build_elibrary_result
from models import Article


async def safe_call(coro, source_name: str) -> tuple[str, list[Article]]:
    try:
        return source_name, await coro
    except Exception as exc:
        return source_name, [
            Article(
                title=f"Ошибка поиска в {source_name}: {exc}",
                source=source_name,
            )
        ]


async def search_all(query: str, limit: int = MAX_RESULTS_PER_SOURCE):
    tasks = [
        safe_call(search_arxiv(query, limit), "arXiv"),
        safe_call(search_scopus(query, SCOPUS_API_KEY, limit), "Scopus"),
        safe_call(search_wos(query, WOS_API_KEY, limit), "Web of Science"),
    ]

    results = await asyncio.gather(*tasks)
    all_articles = [article for _, items in results for article in items]
    all_articles.extend(build_elibrary_result(query))

    unique = OrderedDict()
    for article in all_articles:
        unique.setdefault(article.dedup_key, article)

    return list(unique.values())
