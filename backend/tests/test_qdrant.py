import math
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.models import Distance

from app.schemas.documents import Chunk
from app.services.qdrant import (
    VECTOR_SIZE,
    QdrantVectorStore,
    QdrantVectorStoreError,
)


def create_chunk(identifier: str = "chunk-1") -> Chunk:
    return Chunk(
        id=identifier,
        document_id="document-1",
        content="Synthetic regulatory evidence.",
        position=2,
        title="Synthetic document",
        source="synthetic://document",
    )


def create_client() -> MagicMock:
    return MagicMock(spec=QdrantClient)


def create_store(client: MagicMock) -> QdrantVectorStore:
    return QdrantVectorStore(
        url="http://qdrant:6333",
        collection_name="test_chunks",
        client=client,
    )


def create_embedding(value: float = 0.25) -> list[float]:
    return [value] * VECTOR_SIZE


def test_ensure_collection_creates_cosine_collection() -> None:
    client = create_client()
    client.collection_exists.return_value = False

    create_store(client).ensure_collection()

    client.create_collection.assert_called_once()
    call = client.create_collection.call_args
    assert call.kwargs["collection_name"] == "test_chunks"
    assert call.kwargs["vectors_config"].size == VECTOR_SIZE
    assert call.kwargs["vectors_config"].distance == Distance.COSINE


def test_ensure_collection_keeps_existing_collection() -> None:
    client = create_client()
    client.collection_exists.return_value = True

    create_store(client).ensure_collection()

    client.create_collection.assert_not_called()


def test_store_chunks_inserts_expected_payload() -> None:
    client = create_client()
    client.collection_exists.return_value = True
    chunk = create_chunk()

    stored_count = create_store(client).store_chunks([chunk], [create_embedding()])

    assert stored_count == 1
    point = client.upsert.call_args.kwargs["points"][0]
    assert point.vector == create_embedding()
    assert point.payload == {
        "document_id": "document-1",
        "chunk_id": "chunk-1",
        "text": "Synthetic regulatory evidence.",
        "position": 2,
        "title": "Synthetic document",
        "source": "synthetic://document",
    }
    assert client.upsert.call_args.kwargs["wait"] is True


def test_point_identifier_is_stable_and_valid_uuid() -> None:
    first_client = create_client()
    second_client = create_client()
    first_client.collection_exists.return_value = True
    second_client.collection_exists.return_value = True
    chunk = create_chunk()

    create_store(first_client).store_chunks([chunk], [create_embedding()])
    create_store(second_client).store_chunks([chunk], [create_embedding()])

    first_id = first_client.upsert.call_args.kwargs["points"][0].id
    second_id = second_client.upsert.call_args.kwargs["points"][0].id
    assert first_id == second_id
    assert str(UUID(str(first_id))) == first_id


def test_different_chunk_identifiers_produce_different_point_ids() -> None:
    client = create_client()
    client.collection_exists.return_value = True

    create_store(client).store_chunks(
        [create_chunk("chunk-1"), create_chunk("chunk-2")],
        [create_embedding(), create_embedding()],
    )

    points = client.upsert.call_args.kwargs["points"]
    assert points[0].id != points[1].id


@pytest.mark.parametrize("dimension", [0, VECTOR_SIZE - 1, VECTOR_SIZE + 1])
def test_invalid_embedding_dimension_is_rejected(dimension: int) -> None:
    client = create_client()

    with pytest.raises(ValueError, match="exactly 384"):
        create_store(client).store_chunks([create_chunk()], [[0.0] * dimension])

    client.collection_exists.assert_not_called()
    client.upsert.assert_not_called()


@pytest.mark.parametrize("invalid_value", [math.inf, -math.inf, math.nan])
def test_non_finite_embedding_value_is_rejected(invalid_value: float) -> None:
    client = create_client()
    embedding = create_embedding()
    embedding[10] = invalid_value

    with pytest.raises(ValueError, match="finite"):
        create_store(client).store_chunks([create_chunk()], [embedding])

    client.collection_exists.assert_not_called()
    client.upsert.assert_not_called()


def test_qdrant_api_error_is_exposed_as_store_error() -> None:
    client = create_client()
    client.collection_exists.side_effect = ResponseHandlingException(
        ConnectionError("Qdrant unavailable")
    )

    with pytest.raises(QdrantVectorStoreError, match="Unable to prepare"):
        create_store(client).ensure_collection()


def create_scored_point(
    identifier: str,
    score: float,
    position: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        score=score,
        payload={
            "document_id": "document-1",
            "chunk_id": identifier,
            "text": f"Evidence {identifier}",
            "position": position,
            "title": "Synthetic document",
            "source": "synthetic://document",
        },
    )


def test_search_returns_ordered_results_with_reconstructed_chunks() -> None:
    client = create_client()
    client.query_points.return_value = SimpleNamespace(
        points=[
            create_scored_point("chunk-2", 0.91, 1),
            create_scored_point("chunk-1", 0.72, 0),
        ]
    )

    results = create_store(client).search(create_embedding(), top_k=2)

    assert [result.chunk.id for result in results] == ["chunk-2", "chunk-1"]
    assert [result.score for result in results] == [0.91, 0.72]
    assert results[0].chunk == Chunk(
        id="chunk-2",
        document_id="document-1",
        content="Evidence chunk-2",
        position=1,
        title="Synthetic document",
        source="synthetic://document",
    )
    call = client.query_points.call_args
    assert call.kwargs["limit"] == 2
    assert call.kwargs["with_vectors"] is False


def test_search_limits_results_to_top_k() -> None:
    client = create_client()
    client.query_points.return_value = SimpleNamespace(
        points=[
            create_scored_point("chunk-1", 0.9, 0),
            create_scored_point("chunk-2", 0.8, 1),
            create_scored_point("chunk-3", 0.7, 2),
        ]
    )

    results = create_store(client).search(create_embedding(), top_k=2)

    assert [result.chunk.id for result in results] == ["chunk-1", "chunk-2"]


@pytest.mark.parametrize("dimension", [0, VECTOR_SIZE - 1, VECTOR_SIZE + 1])
def test_search_rejects_invalid_vector_dimension(dimension: int) -> None:
    client = create_client()

    with pytest.raises(ValueError, match="exactly 384"):
        create_store(client).search([0.0] * dimension)

    client.query_points.assert_not_called()


@pytest.mark.parametrize("invalid_value", [math.inf, -math.inf, math.nan])
def test_search_rejects_non_finite_vector(invalid_value: float) -> None:
    client = create_client()
    vector = create_embedding()
    vector[10] = invalid_value

    with pytest.raises(ValueError, match="finite"):
        create_store(client).search(vector)

    client.query_points.assert_not_called()


@pytest.mark.parametrize("top_k", [0, -1, 1.5, True])
def test_search_rejects_invalid_top_k(top_k: object) -> None:
    client = create_client()

    with pytest.raises(ValueError, match="strictly positive integer"):
        create_store(client).search(create_embedding(), top_k=top_k)

    client.query_points.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {
            "document_id": "document-1",
            "chunk_id": "chunk-1",
            "text": "Evidence",
            "position": -1,
            "title": "Synthetic document",
            "source": "synthetic://document",
        },
    ],
)
def test_search_rejects_invalid_payload(payload: object) -> None:
    client = create_client()
    client.query_points.return_value = SimpleNamespace(
        points=[SimpleNamespace(payload=payload, score=0.8)]
    )

    with pytest.raises(QdrantVectorStoreError, match="Invalid search response"):
        create_store(client).search(create_embedding())


def test_search_translates_qdrant_error() -> None:
    client = create_client()
    client.query_points.side_effect = ResponseHandlingException(
        ConnectionError("Qdrant unavailable")
    )

    with pytest.raises(QdrantVectorStoreError, match="Unable to search"):
        create_store(client).search(create_embedding())


def test_search_translates_missing_collection_error() -> None:
    client = create_client()
    client.query_points.side_effect = ValueError("Collection test_chunks not found")

    with pytest.raises(QdrantVectorStoreError, match="Unable to search"):
        create_store(client).search(create_embedding())


def test_search_rejects_malformed_qdrant_response() -> None:
    client = create_client()
    client.query_points.return_value = object()

    with pytest.raises(QdrantVectorStoreError, match="Invalid search response"):
        create_store(client).search(create_embedding())


def test_search_rejects_non_finite_score() -> None:
    client = create_client()
    point = create_scored_point("chunk-1", math.nan, 0)
    client.query_points.return_value = SimpleNamespace(points=[point])

    with pytest.raises(QdrantVectorStoreError, match="Invalid search response"):
        create_store(client).search(create_embedding())
