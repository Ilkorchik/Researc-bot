import asyncio
import re
import urllib.parse
import urllib.request

import feedparser

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

    # Keep the arXiv query simple. Complex boolean/quoted queries can
    # trigger HTTP 406 on some network/CDN paths.
    return " OR ".join(f"all:{term}" for term in unique[:10])


def _fetch_arxiv(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Researc-bot/1.0 (scientific research Telegram bot)",
            "Accept": "application/atom+xml, application/xml;q=0.9, text/xml;q=0.8",
        },
    )

    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read().decode("utf-8")


async def search_arxiv(query: str, limit: int = 10) -> list[Article]:
    params = {
        "search_query": _build_query(query),
        "start": 0,
        "max_results": min(max(limit, 1), 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    xml_text = await asyncio.to_thread(_fetch_arxiv, url)

    feed = feedparser.parse(xml_text)
    results = []

    for entry in feed.entries:
        authors = [a.name for a in getattr(entry, "authors", [])]
        pdf_url = next(
            (
                link.href
                for link in getattr(entry, "links", [])
                if getattr(link, "type", "") == "application/pdf"
            ),
            None,
        )

        results.append(
            Article(
                title=" ".join(entry.title.split()),
                authors=authors,
                year=entry.published[:4] if getattr(entry, "published", None) else None,
                abstract=" ".join(getattr(entry, "summary", "").split()),
                doi=getattr(entry, "arxiv_doi", None),
                url=getattr(entry, "id", None),
                pdf_url=pdf_url,
                source="arXiv",
                raw_id=getattr(entry, "id", None),
            )
        )

    return results
