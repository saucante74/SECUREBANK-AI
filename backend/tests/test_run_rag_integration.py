import json
from unittest.mock import MagicMock

import pytest

from app.services.embeddings import LocalEmbeddingService
from app.services.pii_masking import PiiMasker
from app.services.qdrant import QdrantVectorStore
from scripts.run_rag_integration import (
    CORPUS_PATH,
    DEMO_COLLECTION_NAME,
    FakeLLM,
    find_passage_reference,
    parse_prompt,
    prepare_integration,
    reset_demo_collection,
)


def create_prompt(question: str, passages: list[dict[str, object]]) -> str:
    return (
        "Instructions\n\n"
        f"Question utilisateur:\n{question}\n\n"
        "Passages récupérés (JSON):\n"
        f"{json.dumps(passages, ensure_ascii=False)}"
    )


def test_fake_llm_returns_cited_answer_only_for_matching_evidence() -> None:
    llm = FakeLLM()
    prompt = create_prompt(
        "Quel est le plafond quotidien fictif ?",
        [{"passage": 2, "content": "Le plafond est de 25000 CHF."}],
    )

    response = json.loads(llm.generate(prompt))

    assert response == {
        "answer": "Le plafond quotidien fictif est de 25000 CHF [2].",
        "abstained": False,
    }
    assert llm.prompts == [prompt]


def test_fake_llm_abstains_without_matching_documentary_evidence() -> None:
    llm = FakeLLM()
    prompt = create_prompt(
        "Quel est le plafond quotidien fictif ?",
        [{"passage": 1, "content": "Information sur le renouvellement KYC."}],
    )

    response = json.loads(llm.generate(prompt))

    assert response["abstained"] is True
    assert response["answer"] == ("Les passages fournis ne permettent pas de répondre.")


def test_prompt_helpers_preserve_question_and_find_reference() -> None:
    passages = [
        {"passage": 1, "content": "Autre information"},
        {"passage": 3, "content": "Délai de cinq jours ouvrés"},
    ]

    question, parsed_passages = parse_prompt(create_prompt("Question", passages))

    assert question == "Question"
    assert parsed_passages == passages
    assert find_passage_reference(parsed_passages, "CINQ JOURS") == 3
    assert find_passage_reference(parsed_passages, "absent") is None


def test_prepare_integration_uses_existing_components_without_external_services() -> (
    None
):
    embeddings = MagicMock(spec=LocalEmbeddingService)
    embeddings.embed_chunks.side_effect = lambda chunks: [[0.1] * 384] * len(chunks)
    vector_store = MagicMock(spec=QdrantVectorStore)
    pii_masker = MagicMock(spec=PiiMasker)
    reset_collection = MagicMock()
    point_count = 4

    prepared = prepare_integration(
        corpus_path=CORPUS_PATH,
        embedding_service=embeddings,
        vector_store=vector_store,
        pii_masker=pii_masker,
        reset_collection=reset_collection,
        count_points=lambda: point_count,
    )

    assert len(prepared.chunks) == point_count
    reset_collection.assert_called_once_with()
    embeddings.embed_chunks.assert_called_once_with(prepared.chunks)
    vector_store.store_chunks.assert_called_once_with(
        prepared.chunks,
        prepared.embeddings,
    )
    assert prepared.point_count == point_count


def test_reset_demo_collection_rejects_non_demo_collection() -> None:
    client = MagicMock()

    with pytest.raises(ValueError, match="non-demonstration"):
        reset_demo_collection(client, "securebank_chunks")

    client.collection_exists.assert_not_called()
    client.delete_collection.assert_not_called()


def test_reset_demo_collection_deletes_only_reserved_collection() -> None:
    client = MagicMock()
    client.collection_exists.return_value = True

    reset_demo_collection(client, DEMO_COLLECTION_NAME)

    client.collection_exists.assert_called_once_with(DEMO_COLLECTION_NAME)
    client.delete_collection.assert_called_once_with(
        collection_name=DEMO_COLLECTION_NAME
    )
