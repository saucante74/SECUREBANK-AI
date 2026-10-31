import re

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


class StructuredChunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 75) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if overlap < 0:
            raise ValueError("overlap must be greater than or equal to zero")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(self, document: Document) -> list[Chunk]:
        contents = self._split_content(document.content)
        return [
            Chunk(
                id=f"{document.id}:structured-chunk:{position}",
                document_id=document.id,
                content=content,
                position=position,
                title=document.title,
                source=document.source,
            )
            for position, content in enumerate(contents)
        ]

    def _split_content(self, content: str) -> list[str]:
        sections = content.split("\n\n")
        chunks: list[str] = []
        pending = ""

        for section in sections:
            candidate = section if not pending else f"{pending}\n\n{section}"
            if len(candidate) <= self._chunk_size:
                pending = candidate
                continue
            if pending:
                chunks.append(pending)
                pending = ""
            if len(section) <= self._chunk_size:
                pending = section
            else:
                chunks.extend(self._split_long_section(section))

        if pending:
            chunks.append(pending)
        return chunks

    def _split_long_section(self, section: str) -> list[str]:
        chunks: list[str] = []
        start = 0

        while start < len(section):
            maximum_end = min(start + self._chunk_size, len(section))
            end = self._preferred_end(section, start, maximum_end)
            chunks.append(section[start:end])
            if end == len(section):
                break
            start = self._overlap_start(section, start, end)

        return chunks

    @staticmethod
    def _preferred_end(content: str, start: int, maximum_end: int) -> int:
        if maximum_end == len(content):
            return maximum_end
        window = content[start:maximum_end]
        sentence_ends = [match.end() for match in re.finditer(r"[.!?](?=\s)", window)]
        if sentence_ends:
            return start + sentence_ends[-1]
        whitespace = window.rfind(" ")
        if whitespace > 0:
            return start + whitespace
        return maximum_end

    def _overlap_start(self, content: str, previous_start: int, end: int) -> int:
        target = max(previous_start + 1, end - self._overlap)
        sentence_starts = [
            match.end()
            for match in re.finditer(r"[.!?]\s+", content[previous_start:end])
            if previous_start + match.end() >= target
        ]
        if sentence_starts:
            return previous_start + sentence_starts[0]
        whitespace = content.find(" ", target, end)
        if whitespace >= 0:
            return whitespace + 1
        return target
