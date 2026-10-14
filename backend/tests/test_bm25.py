import pytest

from app.schemas.documents import Chunk
from app.services.bm25 import BM25Retriever


def create_chunk(
    identifier: str,
    content: str,
    position: int,
    title: str = "Synthetic banking guide",
    source: str = "synthetic://banking-guide",
) -> Chunk:
    return Chunk(
        id=identifier,
        document_id="synthetic-document",
        content=content,
        position=position,
        title=title,
        source=source,
    )


def create_chunks() -> list[Chunk]:
    return [
        create_chunk(
            "chunk-credit",
            "La banque vérifie le risque de crédit crédit.",
            0,
        ),
        create_chunk(
            "chunk-account",
            "Le compte bancaire contient un solde disponible.",
            1,
        ),
        create_chunk(
            "chunk-compliance",
            "La conformité contrôle le risque réglementaire.",
            2,
        ),
    ]


def test_search_finds_term_in_chunk() -> None:
    results = BM25Retriever(create_chunks()).search("crédit")

    assert [result.chunk.id for result in results] == ["chunk-credit"]


def test_search_returns_multiple_matching_chunks() -> None:
    results = BM25Retriever(create_chunks()).search("risque")

    assert {result.chunk.id for result in results} == {
        "chunk-credit",
        "chunk-compliance",
    }


def test_results_are_ranked_by_descending_score() -> None:
    results = BM25Retriever(create_chunks()).search("risque crédit")

    assert results[0].chunk.id == "chunk-credit"
    assert [result.score for result in results] == sorted(
        (result.score for result in results),
        reverse=True,
    )


def test_top_k_limits_results() -> None:
    results = BM25Retriever(create_chunks()).search("risque", top_k=1)

    assert len(results) == 1


def test_top_k_larger_than_index_returns_available_matches() -> None:
    results = BM25Retriever(create_chunks()).search("risque", top_k=20)

    assert len(results) == 2


@pytest.mark.parametrize("top_k", [0, -1])
def test_invalid_top_k_raises_explicit_error(top_k: int) -> None:
    with pytest.raises(ValueError, match="top_k must be greater than zero"):
        BM25Retriever(create_chunks()).search("risque", top_k=top_k)


def test_empty_index_returns_no_result() -> None:
    assert BM25Retriever([]).search("risque") == []


@pytest.mark.parametrize("query", ["", "   \t"])
def test_empty_query_returns_no_result(query: str) -> None:
    assert BM25Retriever(create_chunks()).search(query) == []


def test_query_without_common_token_returns_no_result() -> None:
    assert BM25Retriever(create_chunks()).search("hypothèque") == []


def test_search_is_case_insensitive() -> None:
    results = BM25Retriever(create_chunks()).search("CRÉDIT")

    assert [result.chunk.id for result in results] == ["chunk-credit"]


def test_tokenization_separates_punctuation() -> None:
    results = BM25Retriever(create_chunks()).search("solde?!")

    assert [result.chunk.id for result in results] == ["chunk-account"]


def test_tokenization_preserves_french_accents() -> None:
    results = BM25Retriever(create_chunks()).search("conformité")

    assert [result.chunk.id for result in results] == ["chunk-compliance"]


def test_scores_are_floats_without_positive_assumption() -> None:
    results = BM25Retriever(create_chunks()).search("la")

    assert results
    assert all(isinstance(result.score, float) for result in results)


def test_result_preserves_chunk_metadata() -> None:
    chunk = create_chunk(
        "metadata-chunk",
        "Contrôle bancaire synthétique.",
        4,
        title="Synthetic title",
        source="synthetic://metadata",
    )

    result = BM25Retriever([chunk]).search("contrôle")[0]

    assert result.chunk == chunk
    assert result.chunk.title == "Synthetic title"
    assert result.chunk.source == "synthetic://metadata"


def test_equal_scores_preserve_initial_chunk_order() -> None:
    first = create_chunk("first", "risque bancaire", 0)
    second = create_chunk("second", "risque bancaire", 1)

    results = BM25Retriever([first, second]).search("risque")

    assert [result.chunk.id for result in results] == ["first", "second"]


def test_duplicate_chunk_identifier_is_returned_once() -> None:
    chunk = create_chunk("duplicate", "solde bancaire", 0)

    results = BM25Retriever([chunk, chunk]).search("solde")

    assert [result.chunk.id for result in results] == ["duplicate"]


def test_successive_searches_reuse_same_index() -> None:
    retriever = BM25Retriever(create_chunks())

    credit_results = retriever.search("crédit")
    compliance_results = retriever.search("conformité")

    assert [result.chunk.id for result in credit_results] == ["chunk-credit"]
    assert [result.chunk.id for result in compliance_results] == ["chunk-compliance"]
