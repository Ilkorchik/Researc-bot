import httpx

from models import Article
from config import REQUEST_TIMEOUT


SCOPUS_URL = "https://api.elsevier.com/content/search/scopus"


async def search_scopus(query: str, api_key: str, limit: int = 10) -> list[Article]:
    if not api_key:
        return []

    headers = {
        "X-ELS-APIKey": api_key,
        "Accept": "application/json",
    }

    params = {
        "query": f'TITLE-ABS-KEY("{query}")',
        "count": min(limit, 25),
        "start": 0,
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(SCOPUS_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    entries = data.get("search-results", {}).get("entry", [])
    results = []

    for e in entries:
        authors = [e["dc:creator"]] if e.get("dc:creator") else []

        results.append(
            Article(
                title=e.get("dc:title", "Без названия"),
                authors=authors,
                year=(e.get("prism:coverDate") or "")[:4] or None,
                abstract=e.get("dc:description"),
                doi=e.get("prism:doi"),
                url=e.get("prism:url"),
                source="Scopus",
                journal=e.get("prism:publicationName"),
                raw_id=e.get("dc:identifier"),
            )
        )

    return results
