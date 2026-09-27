import httpx

from models import Article
from config import REQUEST_TIMEOUT


WOS_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"


async def search_wos(query: str, api_key: str, limit: int = 10) -> list[Article]:
    if not api_key:
        return []

    headers = {
        "X-ApiKey": api_key,
        "Accept": "application/json",
    }

    params = {
        "q": query,
        "limit": min(limit, 50),
        "page": 1,
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(WOS_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    records = data.get("hits") or data.get("documents") or data.get("data") or []

    results = []
    for item in records:
        document = item.get("document", {}) if isinstance(item.get("document"), dict) else {}

        title = item.get("title") or document.get("title") or "Без названия"
        doi = item.get("doi") or document.get("doi")
        year = item.get("year") or document.get("year")

        authors = item.get("authors") or document.get("authors") or []
        if isinstance(authors, dict):
            authors = authors.get("authors", [])
        if not isinstance(authors, list):
            authors = [str(authors)]

        links = item.get("links", {})
        url = links.get("record") if isinstance(links, dict) else None

        results.append(
            Article(
                title=str(title),
                authors=[str(a) for a in authors],
                year=str(year) if year else None,
                abstract=item.get("abstract") or document.get("abstract"),
                doi=doi,
                url=url,
                source="Web of Science",
                journal=item.get("sourceTitle") or item.get("journal"),
                raw_id=item.get("uid") or document.get("uid"),
            )
        )

    return results
