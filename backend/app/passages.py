import re


WORDS_PER_PASSAGE = 150


def split_passages(pages: list[dict]) -> list[dict]:
    """Keep source whitespace and page boundaries. Positions start at 1.

    The 150-word limit is a starting point, not an embedding model input limit.
    """
    passages = []
    for page in pages:
        text = page["text"]
        words = list(re.finditer(r"\S+", text))
        for start in range(0, len(words), WORDS_PER_PASSAGE):
            end = min(start + WORDS_PER_PASSAGE, len(words)) - 1
            start_character = words[start].start()
            end_character = words[end].end()
            passage_text = text[start_character:end_character]
            passages.append(
                {
                    "position": len(passages) + 1,
                    "page_number": page["page_number"],
                    "text": passage_text,
                }
            )
    return passages
