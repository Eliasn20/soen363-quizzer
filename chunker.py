"""Split lecture notes into chunks small enough to send to the API."""

import hashlib


def split_into_chunks(text, max_chars=3000):
    """Group paragraphs (separated by blank lines) into chunks of up to max_chars.

    A paragraph is never cut in half. A single paragraph longer than max_chars
    becomes its own (oversized) chunk.
    """
    chunks = []
    current = ""

    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue  # skip empty "paragraphs" caused by extra blank lines

        if current and len(current) + 2 + len(paragraph) > max_chars:
            # The paragraph doesn't fit: save the current chunk, start a new one.
            chunks.append(current)
            current = paragraph
        elif current:
            current = current + "\n\n" + paragraph
        else:
            current = paragraph

    if current:
        chunks.append(current)  # don't forget the last chunk

    return chunks


def chunk_hash(chunk):
    """Return a fingerprint of the chunk text (same text -> same hash)."""
    return hashlib.sha256(chunk.encode("utf-8")).hexdigest()
