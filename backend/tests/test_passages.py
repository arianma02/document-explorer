from app.passages import split_passages


def test_preserves_source_whitespace():
    result = split_passages([{"page_number": None, "text": "  First\n  paragraph.  "}])
    assert result == [
        {"position": 1, "page_number": None, "text": "First\n  paragraph."}
    ]


def test_splits_at_word_limit_without_losing_words():
    words = [str(number) for number in range(301)]
    result = split_passages([{"page_number": None, "text": " ".join(words)}])
    assert [len(item["text"].split()) for item in result] == [150, 150, 1]
    assert " ".join((item["text"] for item in result)).split() == words
    assert [item["position"] for item in result] == [1, 2, 3]


def test_skips_empty_pages_without_changing_page_numbers():
    result = split_passages(
        [
            {"page_number": 1, "text": "First"},
            {"page_number": 2, "text": "  "},
            {"page_number": 3, "text": "Third"},
        ]
    )
    assert [item["page_number"] for item in result] == [1, 3]
    assert [item["position"] for item in result] == [1, 2]
