from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Article:
    title: str
    authors: list[str] = field(default_factory=list)
    year: Optional[str] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    source: str = ""
    journal: Optional[str] = None
    raw_id: Optional[str] = None
    cited_by: Optional[int] = None
    document_type: Optional[str] = None

    @property
    def dedup_key(self) -> str:
        if self.doi:
            return "doi:" + self.doi.lower().replace("https://doi.org/", "").strip()
        normalized = " ".join(self.title.lower().split())
        return "title:" + normalized
