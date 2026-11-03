from app.services.outline import normalize_chapters


def _raw(n, words=1000):
    return [{"title": f"第{i}章", "key_points": ["论点"], "data_needed": ["总投资"],
             "suggested_words": words} for i in range(1, n + 1)]


def test_scale_words_to_target():
    data = normalize_chapters(_raw(10, 1000), 12000)
    assert data.chapter_count == 10
    assert data.total_words == 12000
    assert data.needs_manual is False


def test_chapter_count_in_range_ok():
    assert normalize_chapters(_raw(8), 8000).needs_manual is False
    assert normalize_chapters(_raw(13), 13000).needs_manual is False


def test_chapter_count_out_of_range():
    assert normalize_chapters(_raw(5), 5000).needs_manual is True
    assert normalize_chapters(_raw(14), 14000).needs_manual is True


def test_renumber_and_clean_fields():
    raw = [{"chapter_id": 99, "title": "   ", "key_points": ["a", "b"],
            "data_needed": [1, 2], "suggested_words": -5}]
    data = normalize_chapters(raw, 100, allow_scale=False)
    assert data.chapters[0].chapter_id == 1
    assert data.chapters[0].title == "第1章"
    assert data.chapters[0].suggested_words == 0
    assert data.chapters[0].data_needed == ["1", "2"]
