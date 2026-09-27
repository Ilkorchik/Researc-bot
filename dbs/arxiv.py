import asyncio
import html
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

    return " OR ".join(f"all:{term}" for term in unique[:10])


def _fetch_arxiv(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Researc-bot/1.0 (scientific research Telegram bot)",
            "Accept": "*/*",
        },
    )

    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read().decode("utf-8")


def _strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(value).split())


def _search_arxiv_web(query: str, limit: int) -> list[Article]:
    terms = []
    for word in re.findall(r"[A-Za-zА-Яа-яЁё0-9-]+", query.lower()):
        translated = TERM_MAP.get(word)
        if translated:
            terms.extend(translated.split())
        elif not re.search(r"[а-яё]", word):
            terms.append(word)

    search_text = " ".join(dict.fromkeys(terms)) or query
    url = "https://arxiv.org/search/?" + urllib.parse.urlencode({
        "query": search_text,
        "searchtype": "all",
        "abstracts": "show",
        "order": "-announced_date_first",
        "size": min(max(limit, 1), 50),
    })

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/140 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        html_text = response.read().decode("utf-8", errors="replace")

    blocks = re.findall(
        r'<li class="arxiv-result">(.*?)(?=<li class="arxiv-result"|</ol>)',
        html_text,
        flags=re.S,
    )

    results = []
    for block in blocks[:limit]:
        title_match = re.search(
            r'<p class="title[^>]*>(.*?)</p>', block, flags=re.S
        )
        abstract_match = re.search(
            r'<span class="abstract-(?:short|full)[^>]*>(.*?)</span>',
            block,
            flags=re.S,
        )
        abs_match = re.search(r'href="(/abs/[^"]+)"', block)
        pdf_match = re.search(r'href="(/pdf/[^"]+)"', block)
        year_match = re.search(r"Submitted.*?(20\d{2})", block, flags=re.S)

        if not title_match or not abs_match:
            continue

        authors = []
        author_block = re.search(
            r'<p class="authors">(.*?)</p>', block, flags=re.S
        )
        if author_block:
            authors = re.findall(
                r'<a[^>]*>(.*?)</a>', author_block.group(1), flags=re.S
            )
            authors = [_strip_html(a) for a in authors]

        abs_url = urllib.parse.urljoin("https://arxiv.org", abs_match.group(1))
        pdf_url = (
            urllib.parse.urljoin("https://arxiv.org", pdf_match.group(1))
            if pdf_match
            else None
        )

        results.append(
            Article(
                title=_strip_html(title_match.group(1)),
                authors=authors,
                year=year_match.group(1) if year_match else None,
                abstract=_strip_html(abstract_match.group(1)) if abstract_match else None,
                url=abs_url,
                pdf_url=pdf_url,
                source="arXiv",
                raw_id=abs_url,
            )
        )

    return results


async def search_arxiv(query: str, limit: int = 10) -> list[Article]:
    params = {
        "search_query": _build_query(query),
        "start": 0,
        "max_results": min(max(limit, 1), 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"

    try:
        xml_text = await asyncio.to_thread(_fetch_arxiv, url)
        feed = feedparser.parse(xml_text)
    except Exception:
        # Some networks/proxies return HTTP 406 for the arXiv API.
        # Fall back to the public arXiv HTML search page.
        return await asyncio.to_thread(_search_arxiv_web, query, limit)

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
