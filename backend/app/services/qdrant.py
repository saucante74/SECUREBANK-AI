import math
from collections.abc import Sequence
from numbers import Real
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ApiException
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import Settings
from app.schemas.documents import Chunk

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

    def _build_point(
        self,
        chunk: Chunk,
        embedding: Sequence[float],
    ) -> PointStruct:
        if not chunk.document_id.strip() or not chunk.id.strip():
            raise ValueError("chunk identifiers must not be empty")
        if len(embedding) != VECTOR_SIZE:
            raise ValueError(f"embedding must contain exactly {VECTOR_SIZE} values")
        if not all(isinstance(value, Real) for value in embedding):
            raise ValueError("embedding must contain only numeric values")

        vector = [float(value) for value in embedding]
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("embedding must contain only finite values")

        point_id = str(uuid5(POINT_NAMESPACE, f"{chunk.document_id}\x00{chunk.id}"))
        return PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "document_id": chunk.document_id,
                "chunk_id": chunk.id,
                "text": chunk.content,
                "position": chunk.position,
            },
        )
