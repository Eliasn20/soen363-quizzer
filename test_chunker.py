from chunker import chunk_hash, split_into_chunks


def test_empty_text_gives_no_chunks():
    assert split_into_chunks("") == []
    assert split_into_chunks("\n\n\n   \n\n") == []


def test_small_paragraphs_are_grouped_into_one_chunk():
    text = "Intro to SQL.\n\nJoins combine tables.\n\n\n\nIndexes speed up lookups."
    chunks = split_into_chunks(text, max_chars=3000)
    assert chunks == ["Intro to SQL.\n\nJoins combine tables.\n\nIndexes speed up lookups."]


def test_chunks_respect_max_chars():
    paragraphs = ["a" * 40, "b" * 40, "c" * 40]
    chunks = split_into_chunks("\n\n".join(paragraphs), max_chars=100)
    # 40 + 2 + 40 = 82 fits; adding another 42 would be 124 > 100
    assert chunks == ["a" * 40 + "\n\n" + "b" * 40, "c" * 40]


def test_long_paragraph_becomes_its_own_chunk():
    chunks = split_into_chunks("short\n\n" + "x" * 500, max_chars=100)
    assert chunks == ["short", "x" * 500]


def test_hash_is_stable_and_different_for_different_text():
    assert chunk_hash("hello") == chunk_hash("hello")
    assert chunk_hash("hello") != chunk_hash("hello!")
