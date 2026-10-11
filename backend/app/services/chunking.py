from app.schemas.documents import Chunk, Document


class CharacterChunker:
    def __init__(self, chunk_size: int, overlap: int = 0) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if overlap < 0:
            raise ValueError("overlap must be greater than or equal to zero")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(self, document: Document) -> list[Chunk]:
        chunks: list[Chunk] = []
        start = 0
        position = 0

        while start < len(document.content):
            end = min(start + self._chunk_size, len(document.content))
            chunks.append(
                Chunk(
                    id=f"{document.id}:chunk:{position}",
                    document_id=document.id,
                    content=document.content[start:end],
                    position=position,
                    title=document.title,
                    source=document.source,
                )
            )
            if end == len(document.content):
                break
            start = end - self._overlap
            position += 1

        return chunks
