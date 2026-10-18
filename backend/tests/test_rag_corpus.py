from pathlib import Path

import pytest
from pydantic import ValidationError

from app.services.rag_corpus import create_rag_chunks, load_rag_corpus


def test_load_corpus_and_create_chunks(tmp_path: Path) -> None:
    corpus_path = tmp_path / "synthetic-corpus.json"
    corpus_path.write_text(
        """
        {
          "documents": [
            {
              "id": "synthetic-policy",
              "content": "A synthetic policy used only for testing.",
              "title": "Synthetic policy",
              "source": "synthetic://policy"
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    corpus = load_rag_corpus(corpus_path)
    chunks = create_rag_chunks(corpus)

    assert [document.id for document in corpus.documents] == ["synthetic-policy"]
    assert [chunk.id for chunk in chunks] == ["synthetic-policy:chunk:0"]
    assert chunks[0].source == "synthetic://policy"


def test_empty_corpus_is_rejected(tmp_path: Path) -> None:
    corpus_path = tmp_path / "empty-corpus.json"
    corpus_path.write_text('{"documents": []}', encoding="utf-8")

    with pytest.raises(ValidationError):
        load_rag_corpus(corpus_path)
