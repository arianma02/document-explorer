import re


WORDS_PER_PASSAGE = 150


def split_passages(pages: list[dict], tokenizer=None) -> list[dict]:
    """Keep source whitespace and page boundaries. Positions start at 1.

    When a tokenizer is supplied, shorten passages until they fit 256 tokens.
    An individual whitespace-separated word that cannot fit is rejected.
    """
    passages = []
    for page in pages:
        text = page["text"]
        words = list(re.finditer(r"\S+", text))
        start = 0
        while start < len(words):
            end = min(start + WORDS_PER_PASSAGE, len(words)) - 1
            start_character = words[start].start()
            end_character = words[end].end()
            passage_text = text[start_character:end_character]
            if tokenizer is not None:
                while len(tokenizer.encode(passage_text).ids) > 256:
                    if start == end:
                        raise ValueError(
                            "A word is too long for the model. Add spaces or shorten it."
                        )
                    end = (start + end) // 2
                    end_character = words[end].end()
                    passage_text = text[start_character:end_character]
            passages.append(
                {
                    "position": len(passages) + 1,
                    "page_number": page["page_number"],
                    "text": passage_text,
                }
            )
            start = end + 1
    return passages
