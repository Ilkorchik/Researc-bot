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


def _search_via_crossref(query: str, limit: int) -> list[Article]:
    """Use Crossref as a public fallback for scholarly metadata."""
    search_terms = []
    for word in re.findall(r"[A-Za-zА-Яа-яЁё0-9-]+", query.lower()):
        translated = TERM_MAP.get(word)
        if translated:
            search_terms.extend(translated.split())
        elif not re.search(r"[а-яё]", word):
            search_terms.append(word)

    search_text = " ".join(dict.fromkeys(search_terms)) or query
    params = urllib.parse.urlencode({
        "query.bibliographic": search_text,
        "rows": min(max(limit, 1), 50),
    })
    url = f"https://api.crossref.org/works?{params}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Researc-bot/1.0 (scientific research Telegram bot)",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        payload = response.read().decode("utf-8", errors="replace")

    import json
    data = json.loads(payload)
    results = []

    for work in (data.get("message") or {}).get("items", []):
        title_list = work.get("title") or []
        title = " ".join((title_list[0] if title_list else "").split())
        if not title:
            continue

        authors = []
        for author in work.get("author") or []:
            given = (author.get("given") or "").strip()
            family = (author.get("family") or "").strip()
            name = " ".join(x for x in [given, family] if x)
            if name:
                authors.append(name)

        date_parts = (
            (work.get("published-print") or {}).get("date-parts")
            or (work.get("published-online") or {}).get("date-parts")
            or (work.get("issued") or {}).get("date-parts")
            or []
        )
        year = str(date_parts[0][0]) if date_parts and date_parts[0] else None

        doi = work.get("DOI")
        url = f"https://doi.org/{doi}" if doi else work.get("URL")
        journal = (work.get("container-title") or [None])[0]

        results.append(
            Article(
                title=title,
                authors=authors,
                year=year,
                abstract=None,
                doi=doi,
                url=url,
                pdf_url=None,
                source="Crossref",
                journal=journal,
                raw_id=doi or work.get("URL"),
                document_type=work.get("type"),
            )
        )

        if len(results) >= limit:
            break

    return results


def _search_arxiv_via_openalex(query: str, limit: int) -> list[Article]:
    """Use OpenAlex as a broad fallback when direct arXiv access is blocked."""
    terms = []
    for word in re.findall(r"[A-Za-zА-Яа-яЁё0-9-]+", query.lower()):
        translated = TERM_MAP.get(word)
        if translated:
            terms.extend(translated.split())
        elif not re.search(r"[а-яё]", word):
            terms.append(word)

    search_text = " ".join(dict.fromkeys(terms)) or query
    params = urllib.parse.urlencode({
        "search": search_text,
        "per-page": min(max(limit * 5, limit), 100),
    })
    url = f"https://api.openalex.org/works?{params}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Researc-bot/1.0 (scientific research Telegram bot)",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        payload = response.read().decode("utf-8", errors="replace")

    import json
    data = json.loads(payload)
    results = []

    for work in data.get("results", []):
        locations = work.get("locations") or []
        arxiv_id = None
        arxiv_url = None

        for location in locations:
            landing = location.get("landing_page_url") or ""
            match = re.search(r"arxiv\.org/(?:abs|pdf)/([^/?#]+)", landing)
            if match:
                arxiv_id = match.group(1)
                arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
                break

        authors = [
            (author.get("author") or {}).get("display_name")
            for author in (work.get("authorships") or [])
            if (author.get("author") or {}).get("display_name")
        ]

        results.append(
            Article(
                title=" ".join((work.get("title") or "").split()),
                authors=authors,
                year=str(work["publication_year"]) if work.get("publication_year") else None,
                abstract=None,
                doi=(work.get("doi") or "").replace("https://doi.org/", "") or None,
                url=arxiv_url or work.get("doi") or work.get("id"),
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None,
                source="arXiv" if arxiv_id else "OpenAlex",
                raw_id=arxiv_id or work.get("id"),
                cited_by=work.get("cited_by_count"),
                document_type="preprint" if arxiv_id else "article",
            )
        )

        if len(results) >= limit:
            break

    return results

def _search_arxiv_via_semantic_scholar(query: str, limit: int) -> list[Article]:
    """Find arXiv papers through Semantic Scholar when direct arXiv access is blocked."""
    search_terms = []
    for word in re.findall(r"[A-Za-zА-Яа-яЁё0-9-]+", query.lower()):
        translated = TERM_MAP.get(word)
        if translated:
            search_terms.extend(translated.split())
        elif not re.search(r"[а-яё]", word):
            search_terms.append(word)

    search_text = " ".join(dict.fromkeys(search_terms)) or query
    params = urllib.parse.urlencode({
        "query": search_text,
        "limit": min(max(limit * 4, limit), 50),
        "fields": "title,authors,year,abstract,externalIds,url,openAccessPdf,venue,citationCount",
    })
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Researc-bot/1.0 (scientific research Telegram bot)",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        payload = response.read().decode("utf-8", errors="replace")

    import json
    data = json.loads(payload)
    results = []

    for paper in data.get("data", []):
        external_ids = paper.get("externalIds") or {}
        arxiv_id = external_ids.get("ArXiv")
        if not arxiv_id:
            continue

        authors = [
            author.get("name")
            for author in (paper.get("authors") or [])
            if author.get("name")
        ]
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

        results.append(
            Article(
                title=" ".join((paper.get("title") or "").split()),
                authors=authors,
                year=str(paper["year"]) if paper.get("year") else None,
                abstract=" ".join((paper.get("abstract") or "").split()) or None,
                doi=external_ids.get("DOI"),
                url=abs_url,
                pdf_url=pdf_url,
                source="arXiv",
                journal=paper.get("venue") or None,
                raw_id=arxiv_id,
                cited_by=paper.get("citationCount"),
                document_type="preprint",
            )
        )

        if len(results) >= limit:
            break

    return results


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
    # Some networks reject arXiv directly with HTTP 406.
    # Try public indexes first, using simpler query variants before direct arXiv.
    candidate_queries = [query]
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9-]+", query.lower())
    translated = []
    for word in words:
        mapped = TERM_MAP.get(word)
        if mapped:
            translated.extend(mapped.split())
        elif not re.search(r"[а-яё]", word):
            translated.append(word)
    translated = list(dict.fromkeys(translated))
    if translated:
        candidate_queries.append(" ".join(translated))
        if len(translated) > 3:
            candidate_queries.append(" ".join(translated[:3]))

    for candidate in candidate_queries:
        try:
            openalex_results = await asyncio.to_thread(
                _search_arxiv_via_openalex, candidate, limit
            )
            if openalex_results:
                return openalex_results
        except Exception:
            pass

        try:
            semantic_results = await asyncio.to_thread(
                _search_arxiv_via_semantic_scholar, candidate, limit
            )
            if semantic_results:
                return semantic_results
        except Exception:
            pass

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
        # Try the public arXiv HTML search page, but do not let a blocked
        # network endpoint crash the whole Telegram search.
        try:
            return await asyncio.to_thread(_search_arxiv_web, query, limit)
        except Exception:
            return []

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
