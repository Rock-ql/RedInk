from backend.services.outline import OutlineService


def test_parse_outline_reindexes_after_empty_pages():
    service = OutlineService.__new__(OutlineService)
    text = "<page>\nPage one\n<page>\n\n<page>\nPage three"
    pages = service._parse_outline(text)
    assert [page["index"] for page in pages] == [0, 1]
