import re
import feedparser
import httpx

from models import Article
from config import REQUEST_TIMEOUT

ARXIV_API = "https://export.arxiv.org/api/query"

TERM_MAP = {
    "жизнь": "life",
    "спутник": "moon satellite",
    "спутнике": "moon satellite",
    "юпитера": "Jupiter",
    "юпитер": "Jupiter",
    "европа": "Europa",
    "ганимед": "Ganymede",
    "калисто": "Callisto",
    "вода": "water",
    "молекул": "molecules",
    "молекулы": "molecules",
    "диссоциация": "dissociation",
    "диссоциации": "dissociation",
    "рекомбинация": "recombination",
    "рекомбинации": "recombination",
    "перенос": "transport",
    "процессы": "processes",
    "процесс": "process",
}

def _build_query(query: str) -> str:
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9-]+", query.lower())
    expanded = []
    for word in words:
        translated = TERM_MAP.get(word)
        if translated:
            expanded.extend(translated.split())
        elif not re.search(r"[а-яё]", word):
            expanded.append(word)

    unique = list(dict.fromkeys(expanded))
    if not unique:
        return query

    return " OR ".join(f'all:"{term}"' for term in unique[:10])

async def search_arxiv(query: str, limit: int = 10) -> list[Article]:
    params = {
        "search_query": _build_query(query),
        "start": 0,
        "max_results": min(max(limit, 1), 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(ARXIV_API, params=params)
        response.raise_for_status()

    feed = feedparser.parse(response.text)
    results = []

    for entry in feed.entries:
        authors = [a.name for a in getattr(entry, "authors", [])]
        pdf_url = next(
            (link.href for link in getattr(entry, "links", [])
             if getattr(link, "type", "") == "application/pdf"),
            None,
        )

        results.append(Article(
            title=" ".join(entry.title.split()),
            authors=authors,
            year=entry.published[:4] if getattr(entry, "published", None) else None,
            abstract=" ".join(getattr(entry, "summary", "").split()),
            doi=getattr(entry, "arxiv_doi", None),
            url=getattr(entry, "id", None),
            pdf_url=pdf_url,
            source="arXiv",
            raw_id=getattr(entry, "id", None),
        ))

    return results
