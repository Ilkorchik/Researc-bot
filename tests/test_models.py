from models import Article


def test_dedup_key_prefers_doi():
    article = Article(title="Example", doi="10.1234/ABC")
    assert article.dedup_key == "doi:10.1234/abc"


def test_dedup_key_falls_back_to_title():
    article = Article(title="  Water   Transport  ")
    assert article.dedup_key == "title:water transport"
