import unittest

from app.passages import split_passages


class PassageTests(unittest.TestCase):
    def test_preserves_source_whitespace(self):
        result = split_passages(
            [{"page_number": None, "text": "  First\n  paragraph.  "}]
        )
        self.assertEqual(
            result,
            [{"position": 1, "page_number": None, "text": "First\n  paragraph."}],
        )

    def test_splits_at_word_limit_without_losing_words(self):
        words = [str(number) for number in range(301)]
        result = split_passages([{"page_number": None, "text": " ".join(words)}])
        self.assertEqual([len(item["text"].split()) for item in result], [150, 150, 1])
        self.assertEqual(" ".join(item["text"] for item in result).split(), words)
        self.assertEqual([item["position"] for item in result], [1, 2, 3])

    def test_skips_empty_pages_without_changing_page_numbers(self):
        result = split_passages(
            [
                {"page_number": 1, "text": "First"},
                {"page_number": 2, "text": "  "},
                {"page_number": 3, "text": "Third"},
            ]
        )
        self.assertEqual([item["page_number"] for item in result], [1, 3])
        self.assertEqual([item["position"] for item in result], [1, 2])
