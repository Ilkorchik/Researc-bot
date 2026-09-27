import urllib.parse

from models import Article


def build_elibrary_result(query: str) -> list[Article]:
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.elibrary.ru/query_results.asp?querybox={encoded}"

    return [
        Article(
            title=f"Поиск eLIBRARY по запросу: {query}",
            source="eLIBRARY",
            url=url,
        )
    ]
