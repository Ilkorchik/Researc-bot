import httpx

from models import Article
from config import REQUEST_TIMEOUT


SCOPUS_URL = "https://api.elsevier.com/content/search/scopus"


def _authors(entry: dict) -> list[str]:
    raw = entry.get("author")
    if isinstance(raw, dict):
        raw = [raw]
    if isinstance(raw, list):
        names = []
        for author in raw:
            if not isinstance(author, dict):
                continue
            name = author.get("authname") or author.get("authfullname") or author.get("surname")
            if name:
                names.append(str(name))
        if names:
            return names
    creator = entry.get("dc:creator")
    return [str(creator)] if creator else []


def _clean_doi(value):
    if not value:
        return None
    value = str(value).strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
    return value or None


def _int(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


async def search_scopus(query: str, api_key: str, limit: int = 10) -> list[Article]:
    if not api_key:
        return []

    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    safe_query = query.replace('"', "'")
    params = {
        "query": f'TITLE-ABS-KEY("{safe_query}")',
        "count": min(max(limit, 1), 25),
        "start": 0,
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(SCOPUS_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    entries = (data.get("search-results") or {}).get("entry") or []
    results = []

    for e in entries:
        if not isinstance(e, dict) or not e.get("dc:title"):
            continue
        cover_date = e.get("prism:coverDate") or e.get("prism:coverDisplayDate")
        results.append(Article(
            title=str(e["dc:title"]).strip(),
            authors=_authors(e),
            year=str(cover_date)[:4] if cover_date else None,
            abstract=e.get("dc:description"),
            doi=_clean_doi(e.get("prism:doi")),
            url=e.get("prism:url"),
            source="Scopus",
            journal=e.get("prism:publicationName"),
            raw_id=e.get("dc:identifier") or e.get("eid"),
            cited_by=_int(e.get("citedby-count")),
            document_type=e.get("prism:aggregationType"),
        ))
    return results
