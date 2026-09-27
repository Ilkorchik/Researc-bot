import feedparser
import httpx

from models import Article
from config import REQUEST_TIMEOUT


ARXIV_API = "https://export.arxiv.org/api/query"


async def search_arxiv(query: str, limit: int = 10) -> list[Article]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(ARXIV_API, params=params)
        response.raise_for_status()

    feed = feedparser.parse(response.text)
    results = []

    for entry in feed.entries:
        doi = getattr(entry, "arxiv_doi", None)
        authors = [a.name for a in getattr(entry, "authors", [])]

        pdf_url = None
        for link in getattr(entry, "links", []):
            if getattr(link, "type", "") == "application/pdf":
                pdf_url = link.href
                break

        results.append(
            Article(
                title=" ".join(entry.title.split()),
                authors=authors,
                year=entry.published[:4] if getattr(entry, "published", None) else None,
                abstract=" ".join(getattr(entry, "summary", "").split()),
                doi=doi,
                url=getattr(entry, "id", None),
                pdf_url=pdf_url,
                source="arXiv",
                raw_id=getattr(entry, "id", None),
            )
        )

    return results
