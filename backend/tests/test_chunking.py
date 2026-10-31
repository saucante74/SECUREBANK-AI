import pytest

from app.schemas.documents import Document
from app.services.chunking import CharacterChunker, StructuredChunker


def create_document(content: str = "abcdefghij") -> Document:
    return Document(
        id="synthetic-document",
        content=content,
        title="Synthetic regulatory note",
        source="synthetic://regulatory-note",
    )


def test_document_shorter_than_chunk_size_produces_one_chunk() -> None:
    chunks = CharacterChunker(chunk_size=20).chunk(create_document("court"))

    assert [chunk.content for chunk in chunks] == ["court"]


def test_document_equal_to_chunk_size_produces_one_chunk() -> None:
    chunks = CharacterChunker(chunk_size=10).chunk(create_document())

    assert [chunk.content for chunk in chunks] == ["abcdefghij"]


def test_document_longer_than_chunk_size_produces_ordered_chunks() -> None:
    chunks = CharacterChunker(chunk_size=4).chunk(create_document())

    assert [chunk.content for chunk in chunks] == ["abcd", "efgh", "ij"]
    assert [chunk.position for chunk in chunks] == [0, 1, 2]


def test_chunks_include_configured_overlap() -> None:
    chunks = CharacterChunker(chunk_size=5, overlap=2).chunk(create_document())

    assert [chunk.content for chunk in chunks] == ["abcde", "defgh", "ghij"]
    assert chunks[0].content[-2:] == chunks[1].content[:2]
    assert chunks[1].content[-2:] == chunks[2].content[:2]


def test_chunks_have_no_overlap_when_disabled() -> None:
    chunks = CharacterChunker(chunk_size=4, overlap=0).chunk(create_document())

    assert "".join(chunk.content for chunk in chunks) == "abcdefghij"


def test_chunks_preserve_document_metadata() -> None:
    document = create_document("contenu synthétique français")

    chunks = CharacterChunker(chunk_size=10, overlap=2).chunk(document)

    assert all(chunk.document_id == document.id for chunk in chunks)
    assert all(chunk.title == document.title for chunk in chunks)
    assert all(chunk.source == document.source for chunk in chunks)


def test_chunk_identifiers_are_deterministic() -> None:
    document = create_document()
    chunker = CharacterChunker(chunk_size=4, overlap=1)

    first_ids = [chunk.id for chunk in chunker.chunk(document)]
    second_ids = [chunk.id for chunk in chunker.chunk(document)]

    assert first_ids == second_ids
    assert first_ids == [
        "synthetic-document:chunk:0",
        "synthetic-document:chunk:1",
        "synthetic-document:chunk:2",
    ]


def test_chunk_order_matches_document_order() -> None:
    chunks = CharacterChunker(chunk_size=3, overlap=1).chunk(
        create_document("01234567")
    )

    assert [(chunk.position, chunk.content) for chunk in chunks] == [
        (0, "012"),
        (1, "234"),
        (2, "456"),
        (3, "67"),
    ]


def test_french_accents_are_preserved() -> None:
    content = "Réglementation bancaire à Genève"

    chunks = CharacterChunker(chunk_size=11, overlap=3).chunk(create_document(content))

    reconstructed = chunks[0].content
    reconstructed += "".join(chunk.content[3:] for chunk in chunks[1:])
    assert reconstructed == content


@pytest.mark.parametrize(
    ("chunk_size", "overlap", "message"),
    [
        (0, 0, "chunk_size must be greater than zero"),
        (-1, 0, "chunk_size must be greater than zero"),
        (5, -1, "overlap must be greater than or equal to zero"),
        (5, 5, "overlap must be smaller than chunk_size"),
        (5, 6, "overlap must be smaller than chunk_size"),
    ],
)
def test_invalid_parameters_raise_explicit_error(
    chunk_size: int,
    overlap: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        CharacterChunker(chunk_size=chunk_size, overlap=overlap)


def test_chunks_never_exceed_maximum_size_or_are_empty() -> None:
    chunks = CharacterChunker(chunk_size=4, overlap=3).chunk(create_document())

    assert chunks
    assert all(0 < len(chunk.content) <= 4 for chunk in chunks)


def test_overlap_reconstruction_loses_no_character() -> None:
    content = "abcdefghijklmnopqrstuvwxyz"
    overlap = 3
    chunks = CharacterChunker(chunk_size=8, overlap=overlap).chunk(
        create_document(content)
    )

    reconstructed = chunks[0].content
    reconstructed += "".join(chunk.content[overlap:] for chunk in chunks[1:])
    assert reconstructed == content


def test_chunking_does_not_modify_document() -> None:
    document = create_document("Texte français synthétique.")
    original_content = document.content

    CharacterChunker(chunk_size=8, overlap=2).chunk(document)

    assert document.content == original_content


def reconstruct_overlapping_chunks(contents: list[str]) -> str:
    reconstructed = contents[0]
    for content in contents[1:]:
        overlap = min(len(reconstructed), len(content))
        while overlap and not reconstructed.endswith(content[:overlap]):
            overlap -= 1
        separator = "" if overlap else "\n\n"
        reconstructed += separator + content[overlap:]
    return reconstructed


def test_structured_chunks_preserve_complete_content() -> None:
    content = (
        "Première section\nUne première phrase utile. Une deuxième phrase utile.\n\n"
        "Deuxième section\nUne conclusion bancaire précise."
    )
    chunks = StructuredChunker(chunk_size=70, overlap=20).chunk(
        create_document(content)
    )

    assert (
        reconstruct_overlapping_chunks([chunk.content for chunk in chunks]) == content
    )


def test_structured_chunker_keeps_sections_whole_when_they_fit() -> None:
    content = (
        "Titre un\nCette section reste entière.\n\n"
        "Titre deux\nCette autre section reste entière."
    )
    chunks = StructuredChunker(chunk_size=48, overlap=10).chunk(
        create_document(content)
    )

    assert [chunk.content for chunk in chunks] == content.split("\n\n")


def test_structured_chunker_is_deterministic() -> None:
    document = create_document("Titre\nUne phrase. Une autre phrase. " * 20)
    chunker = StructuredChunker(chunk_size=120, overlap=25)

    first = chunker.chunk(document)
    second = chunker.chunk(document)

    assert first == second
    assert [chunk.id for chunk in first] == [
        f"synthetic-document:structured-chunk:{position}"
        for position in range(len(first))
    ]


def test_structured_chunker_splits_long_sections_at_sentence_boundaries() -> None:
    sentences = [f"Phrase bancaire numéro {number} complète." for number in range(30)]
    content = "Section longue\n" + " ".join(sentences)
    chunks = StructuredChunker(chunk_size=120, overlap=30).chunk(
        create_document(content)
    )

    assert len(chunks) > 1
    assert all(len(chunk.content) <= 120 for chunk in chunks)
    assert all(chunk.content.rstrip().endswith(".") for chunk in chunks)
    assert (
        reconstruct_overlapping_chunks([chunk.content for chunk in chunks]) == content
    )
