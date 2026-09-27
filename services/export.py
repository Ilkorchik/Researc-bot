import csv
from pathlib import Path

from models import Article


def export_csv(articles: list[Article], path: str) -> str:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "title", "authors", "year", "source",
        "journal", "doi", "url", "pdf_url", "abstract",
    ]

    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for a in articles:
            writer.writerow({
                "title": a.title,
                "authors": "; ".join(a.authors),
                "year": a.year or "",
                "source": a.source,
                "journal": a.journal or "",
                "doi": a.doi or "",
                "url": a.url or "",
                "pdf_url": a.pdf_url or "",
                "abstract": a.abstract or "",
            })

    return str(output)
