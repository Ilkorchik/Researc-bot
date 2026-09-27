import re
import httpx

from models import Article
from config import REQUEST_TIMEOUT


WOS_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"


def _clean_doi(value):
    if not value:
        return None
    if isinstance(value, dict):
        value = value.get("value") or value.get("doi") or value.get("DOI")
    if isinstance(value, list):
        value = value[0] if value else None
    if not value:
        return None
    value = str(value).strip()
    value = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    return value or None


def _text(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("value", "text", "content", "title"):
            result = _text(value.get(key))
            if result:
                return result
    if isinstance(value, list):
        parts = [_text(x) for x in value]
        parts = [x for x in parts if x]
        return " ".join(parts) or None
    return str(value)


def _authors(value):
    if isinstance(value, dict):
        for key in ("authors", "author", "names", "value"):
            if key in value:
                return _authors(value[key])
        name = value.get("displayName") or value.get("fullName") or value.get("name")
        return [str(name)] if name else []
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                name = item.get("displayName") or item.get("fullName") or item.get("name")
                if name:
                    result.append(str(name))
        return result
    return [str(value)] if value else []


def _year(value):
    match = re.search(r"\b(19|20)\d{2}\b", str(value or ""))
    return match.group(0) if match else None


def _find(obj, keys):
    if isinstance(obj, dict):
        for key in keys:
            if obj.get(key) not in (None, "", [], {}):
                return obj[key]
        for value in obj.values():
            found = _find(value, keys)
            if found not in (None, "", [], {}):
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find(value, keys)
            if found not in (None, "", [], {}):
                return found
    return None


def _record_url(item):
    links = _find(item, ("links", "link"))
    if isinstance(links, dict):
        for key in ("record", "self", "url", "href"):
            value = links.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
    uid = _find(item, ("uid", "UT", "ut"))
    return f"https://www.webofscience.com/wos/woscc/full-record/{uid}" if uid else None


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def search_wos(query: str, api_key: str, limit: int = 10) -> list[Article]:
    if not api_key:
        return []

    headers = {"X-ApiKey": api_key, "Accept": "application/json"}
    params = {"q": query, "limit": min(max(limit, 1), 50), "page": 1}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(WOS_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    records = data.get("hits") or data.get("documents") or data.get("data") or []
    results = []

    for item in records:
        if not isinstance(item, dict):
            continue
        document = item.get("document") if isinstance(item.get("document"), dict) else {}

        title = _text(item.get("title") or item.get("documentTitle") or document.get("title"))
        if not title:
            continue

        authors = item.get("authors") or item.get("author") or document.get("authors")
        doi = item.get("doi") or item.get("DOI") or document.get("doi") or _find(item, ("doi", "DOI"))
        year = item.get("year") or item.get("publicationYear") or document.get("year")
        abstract = item.get("abstract") or item.get("abstractText") or document.get("abstract")
        journal = item.get("sourceTitle") or item.get("journal") or document.get("sourceTitle")
        cited = item.get("timesCited") or item.get("citedCount") or _find(item, ("timesCited", "citedCount"))
        uid = item.get("uid") or item.get("UT") or document.get("uid")

        results.append(Article(
            title=title,
            authors=_authors(authors),
            year=_year(year),
            abstract=_text(abstract),
            doi=_clean_doi(doi),
            url=_record_url(item),
            source="Web of Science",
            journal=_text(journal),
            raw_id=str(uid) if uid else None,
            cited_by=_int(cited),
            document_type=_text(item.get("documentType") or item.get("type")),
        ))

    return results
