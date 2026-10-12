import math
from collections.abc import Sequence
from numbers import Real
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ApiException
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import Settings
from app.schemas.documents import Chunk
from app.schemas.retrieval import RetrievalResult

VECTOR_SIZE = 384
POINT_NAMESPACE = uuid5(NAMESPACE_URL, "securebank-ai/qdrant/chunks")


class QdrantVectorStoreError(RuntimeError):
    pass


class QdrantVectorStore:
    def __init__(
        self,
        url: str,
        collection_name: str,
        client: QdrantClient | None = None,
    ) -> None:
        if not url.strip():
            raise ValueError("Qdrant URL must not be empty")
        if not collection_name.strip():
            raise ValueError("Qdrant collection name must not be empty")
        self._collection_name = collection_name
        self._client = client or QdrantClient(url=url)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        client: QdrantClient | None = None,
    ) -> "QdrantVectorStore":
        return cls(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection_name,
            client=client,
        )

    def ensure_collection(self) -> None:
        try:
            if self._client.collection_exists(self._collection_name):
                return
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
        except ApiException as error:
            raise QdrantVectorStoreError(
                f"Unable to prepare Qdrant collection {self._collection_name!r}"
            ) from error

    def store_chunks(
        self,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        points = [
            self._build_point(chunk, embedding)
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        self.ensure_collection()
        if not points:
            return 0

        try:
            self._client.upsert(
                collection_name=self._collection_name,
                points=points,
                wait=True,
            )
        except ApiException as error:
            raise QdrantVectorStoreError(
                f"Unable to store chunks in Qdrant collection {self._collection_name!r}"
            ) from error
        return len(points)

    def search(
        self,
        query_vector: Sequence[float],
        top_k: int = 3,
    ) -> list[RetrievalResult]:
        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
            raise ValueError("top_k must be a strictly positive integer")

        vector = self._validate_vector(query_vector, "query_vector")
        try:
            response = self._client.query_points(
                collection_name=self._collection_name,
                query=vector,
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )
        except (ApiException, ValueError) as error:
            raise QdrantVectorStoreError(
                f"Unable to search Qdrant collection {self._collection_name!r}"
            ) from error

        try:
            points = response.points
            return [self._build_retrieval_result(point) for point in points[:top_k]]
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValidationError,
            ValueError,
        ) as error:
            raise QdrantVectorStoreError(
                f"Invalid search response from Qdrant collection "
                f"{self._collection_name!r}"
            ) from error

    def _build_point(
        self,
        chunk: Chunk,
        embedding: Sequence[float],
    ) -> PointStruct:
        if not chunk.document_id.strip() or not chunk.id.strip():
            raise ValueError("chunk identifiers must not be empty")
        vector = self._validate_vector(embedding, "embedding")

        point_id = str(uuid5(POINT_NAMESPACE, f"{chunk.document_id}\x00{chunk.id}"))
        return PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "document_id": chunk.document_id,
                "chunk_id": chunk.id,
                "text": chunk.content,
                "position": chunk.position,
                "title": chunk.title,
                "source": chunk.source,
            },
        )

    @staticmethod
    def _validate_vector(vector: Sequence[float], name: str) -> list[float]:
        if len(vector) != VECTOR_SIZE:
            raise ValueError(f"{name} must contain exactly {VECTOR_SIZE} values")
        if not all(isinstance(value, Real) for value in vector):
            raise ValueError(f"{name} must contain only numeric values")

        normalized_vector = [float(value) for value in vector]
        if not all(math.isfinite(value) for value in normalized_vector):
            raise ValueError(f"{name} must contain only finite values")
        return normalized_vector

    @staticmethod
    def _build_retrieval_result(point: object) -> RetrievalResult:
        payload = point.payload
        if not isinstance(payload, dict):
            raise ValueError("Qdrant point payload must be an object")
        score = point.score
        if not isinstance(score, Real) or not math.isfinite(float(score)):
            raise ValueError("Qdrant point score must be a finite number")

        chunk = Chunk(
            id=payload["chunk_id"],
            document_id=payload["document_id"],
            content=payload["text"],
            position=payload["position"],
            title=payload["title"],
            source=payload["source"],
        )
        return RetrievalResult(chunk=chunk, score=float(score))
