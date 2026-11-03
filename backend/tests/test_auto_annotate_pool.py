import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from pydantic import ValidationError

import scripts.auto_annotate_pool as auto_annotate_pool_module
from scripts.auto_annotate_pool import (
    DEFAULT_MODEL,
    PROMPT_VERSION,
    LLMJudgment,
    SelectionFile,
    annotate_pool,
    create_judgment_file,
    load_judgment_file,
    load_pool,
    load_selection_file,
    main,
    parse_arguments,
    request_judgment,
    save_judgment_file,
    system_prompt,
    validate_base_url,
    validate_resume,
    validate_selection,
)
from scripts.build_annotation_pool import AnnotationPool

SOURCE_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "rag_annotation_pool_v2.json"
)
SELECTION_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "rag_annotation_selection_v2_human_blind_test.json"
)


class ResponseHandler(BaseHTTPRequestHandler):
    response_content = '{"relevance": 2, "reason": "Passage directement pertinent."}'
    requests: list[dict[str, object]] = []

    def do_POST(self) -> None:
        content_length = int(self.headers["Content-Length"])
        request_data = json.loads(self.rfile.read(content_length))
        type(self).requests.append(request_data)
        response = json.dumps(
            {"choices": [{"message": {"content": self.response_content}}]}
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format_string: str, *arguments: object) -> None:
        return


@contextmanager
def fake_http_server(content: str) -> Iterator[str]:
    ResponseHandler.response_content = content
    ResponseHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), ResponseHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def source_pool() -> AnnotationPool:
    return load_pool(SOURCE_PATH)


def write_selection_file(
    path: Path,
    pairs: list[tuple[str, str]],
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "corpus_version": "v2",
                "selections": [
                    {"question_id": question_id, "chunk_id": chunk_id}
                    for question_id, chunk_id in pairs
                ],
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "payload",
    [
        '{"relevance": 3, "reason": "Incorrect."}',
        '{"relevance": true, "reason": "Incorrect."}',
        '{"relevance": 2, "reason": ""}',
        '{"relevance": 2, "reason": "Valide.", "extra": 1}',
        '{"relevance": "2", "reason": "Incorrect."}',
        "not-json",
    ],
)
def test_strict_judgment_validation_rejects_invalid_payload(payload: str) -> None:
    with pytest.raises(ValidationError):
        LLMJudgment.model_validate_json(payload)


def test_fake_http_server_returns_valid_constrained_judgment() -> None:
    pool = source_pool()
    question = pool.questions[0]
    candidate = question.candidates[0]

    with fake_http_server(
        '{"relevance": 2, "reason": "Le passage répond directement."}'
    ) as base_url:
        judgment = request_judgment(
            base_url,
            question.question,
            candidate,
            DEFAULT_MODEL,
        )

    assert judgment.relevance == 2
    assert judgment.reason == "Le passage répond directement."
    assert len(ResponseHandler.requests) == 1
    request = ResponseHandler.requests[0]
    assert request["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "relevance_judgment",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "relevance": {"type": "integer", "enum": [0, 1, 2]},
                    "reason": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 300,
                    },
                },
                "required": ["relevance", "reason"],
                "additionalProperties": False,
            },
        },
    }


def test_resume_preserves_existing_judgments(tmp_path: Path) -> None:
    pool = source_pool()
    output_path = tmp_path / "judgments.json"
    initial = create_judgment_file(pool, DEFAULT_MODEL)
    first_question = pool.questions[0]
    first_candidate = first_question.candidates[0]

    with fake_http_server(
        '{"relevance": 1, "reason": "Information partielle."}'
    ) as base_url:
        first_run = annotate_pool(
            pool,
            initial,
            output_path,
            base_url,
            DEFAULT_MODEL,
            limit=1,
        )
        resumed = load_judgment_file(output_path)
        validate_resume(pool, resumed, DEFAULT_MODEL)
        second_run = annotate_pool(
            pool,
            resumed,
            output_path,
            base_url,
            DEFAULT_MODEL,
            limit=1,
        )

    assert len(first_run.judgments) == 1
    assert len(second_run.judgments) == 2
    assert second_run.judgments[0] == first_run.judgments[0]
    assert second_run.judgments[0].chunk_id == first_candidate.chunk_id
    assert second_run.judgments[1].chunk_id != first_candidate.chunk_id


def test_source_and_human_annotations_remain_unchanged(tmp_path: Path) -> None:
    source_before = SOURCE_PATH.read_bytes()
    output_path = tmp_path / "llm-judgments.json"

    exit_code = main(["--test-mode", "--limit", "1", "--output", str(output_path)])

    assert exit_code == 0
    assert SOURCE_PATH.read_bytes() == source_before
    assert output_path != SOURCE_PATH
    result = load_judgment_file(output_path)
    assert len(result.judgments) == 1
    assert result.metadata.provenance == "llm_judge"
    assert result.metadata.model == DEFAULT_MODEL
    assert result.metadata.prompt_version == PROMPT_VERSION
    assert result.metadata.corpus_version == "v2"


def test_existing_selection_is_valid_for_source_pool() -> None:
    selection_file = load_selection_file(SELECTION_PATH)

    validate_selection(source_pool(), selection_file)

    assert len(selection_file.selections) == 10


def test_cli_accepts_selection_file() -> None:
    arguments = parse_arguments(["--selection-file", str(SELECTION_PATH)])

    assert arguments.selection_file == SELECTION_PATH


@pytest.mark.parametrize(
    "payload",
    [
        {"schema_version": 2, "corpus_version": "v2", "selections": [{}]},
        {"schema_version": 1, "corpus_version": "v1", "selections": [{}]},
        {"schema_version": 1, "corpus_version": "v2", "selections": []},
    ],
)
def test_selection_rejects_invalid_metadata_or_empty_list(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        SelectionFile.model_validate(payload)


def test_selection_rejects_duplicate_pairs() -> None:
    pair = {
        "question_id": "factual-mortgage-capacity",
        "chunk_id": "benchmark-mortgage-capacity:structured-chunk:0",
    }

    with pytest.raises(ValidationError, match="selection pairs must be unique"):
        SelectionFile.model_validate(
            {
                "schema_version": 1,
                "corpus_version": "v2",
                "selections": [pair, pair],
            }
        )


def test_selection_rejects_unknown_pool_pair() -> None:
    selection_file = SelectionFile.model_validate(
        {
            "schema_version": 1,
            "corpus_version": "v2",
            "selections": [
                {"question_id": "unknown-question", "chunk_id": "unknown-chunk"}
            ],
        }
    )

    with pytest.raises(ValueError, match="selection contains unknown candidates"):
        validate_selection(source_pool(), selection_file)


def test_selection_annotates_only_selected_pairs_in_file_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = source_pool()
    first = pool.questions[1]
    second = pool.questions[3]
    pairs = [
        (second.question_id, second.candidates[1].chunk_id),
        (first.question_id, first.candidates[0].chunk_id),
    ]
    selection_path = tmp_path / "selection.json"
    output_path = tmp_path / "judgments.json"
    write_selection_file(selection_path, pairs)
    selection_file = load_selection_file(selection_path)
    monkeypatch.setattr(
        auto_annotate_pool_module,
        "request_judgment",
        lambda *arguments, **keywords: LLMJudgment(
            relevance=2,
            reason="Jugement synthétique de test.",
        ),
    )

    result = annotate_pool(
        pool,
        create_judgment_file(pool, DEFAULT_MODEL),
        output_path,
        "http://127.0.0.1:8081",
        DEFAULT_MODEL,
        limit=10,
        selection_file=selection_file,
    )

    assert [
        (judgment.question_id, judgment.chunk_id) for judgment in result.judgments
    ] == pairs


def test_selection_limit_and_resume_follow_selection_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = source_pool()
    question = pool.questions[1]
    pairs = [
        (question.question_id, candidate.chunk_id)
        for candidate in question.candidates[:3]
    ]
    selection_path = tmp_path / "selection.json"
    output_path = tmp_path / "judgments.json"
    write_selection_file(selection_path, pairs)
    selection_file = load_selection_file(selection_path)
    monkeypatch.setattr(
        auto_annotate_pool_module,
        "request_judgment",
        lambda *arguments, **keywords: LLMJudgment(
            relevance=2,
            reason="Jugement synthétique de test.",
        ),
    )

    first_result = annotate_pool(
        pool,
        create_judgment_file(pool, DEFAULT_MODEL),
        output_path,
        "http://127.0.0.1:8081",
        DEFAULT_MODEL,
        limit=1,
        selection_file=selection_file,
    )
    result = annotate_pool(
        pool,
        first_result,
        output_path,
        "http://127.0.0.1:8081",
        DEFAULT_MODEL,
        limit=1,
        selection_file=selection_file,
    )

    assert [
        (judgment.question_id, judgment.chunk_id) for judgment in result.judgments
    ] == pairs[:2]


def test_rejects_source_as_output_path() -> None:
    source_before = SOURCE_PATH.read_bytes()

    exit_code = main(
        [
            "--test-mode",
            "--limit",
            "1",
            "--source",
            str(SOURCE_PATH),
            "--output",
            str(SOURCE_PATH),
        ]
    )

    assert exit_code == 1
    assert SOURCE_PATH.read_bytes() == source_before


def test_resume_rejects_different_corpus(tmp_path: Path) -> None:
    pool = source_pool()
    output_path = tmp_path / "judgments.json"
    judgment_file = create_judgment_file(pool, DEFAULT_MODEL)
    incompatible_metadata = judgment_file.metadata.model_copy(
        update={"corpus_fingerprint": "0" * 64}
    )
    incompatible = judgment_file.model_copy(update={"metadata": incompatible_metadata})
    save_judgment_file(incompatible, output_path)

    with pytest.raises(ValueError, match="different corpus"):
        validate_resume(pool, load_judgment_file(output_path), DEFAULT_MODEL)


def test_prompt_contains_complete_scoring_criteria() -> None:
    prompt = system_prompt()

    assert "Note 0 — Non pertinent" in prompt
    assert "simple mention du thème" in prompt
    assert "Note 1 — Partiellement pertinent" in prompt
    assert "produit bancaire différent" in prompt
    assert "partie substantielle" in prompt
    assert "Note 2 — Directement pertinent" in prompt
    assert "bon produit bancaire et le bon contexte" in prompt
    assert "réponse directe et suffisante" in prompt
    assert "crédit immobilier du crédit à la consommation" in prompt
    assert "N'invente aucune information absente" in prompt


def test_prompt_contains_calibration_examples() -> None:
    prompt = system_prompt()

    assert "garantie immobilière sans élément de calcul : note 0" in prompt
    assert "revenus, charges et crédits pour un prêt personnel : note 1" in prompt
    assert (
        "revenus, charges, crédits et taux d'effort pour un crédit immobilier : note 2"
    ) in prompt


def test_resume_rejects_legacy_prompt_version() -> None:
    pool = source_pool()
    judgment_file = create_judgment_file(pool, DEFAULT_MODEL)
    legacy_metadata = judgment_file.metadata.model_copy(update={"prompt_version": None})
    legacy_file = judgment_file.model_copy(update={"metadata": legacy_metadata})

    with pytest.raises(ValueError, match="different prompt version"):
        validate_resume(pool, legacy_file, DEFAULT_MODEL)


@pytest.mark.parametrize(
    "base_url",
    [
        "https://127.0.0.1:8081",
        "http://example.com:8081",
        "http://user:password@127.0.0.1:8081",
    ],
)
def test_rejects_non_local_or_credentialed_server_url(base_url: str) -> None:
    with pytest.raises(ValueError):
        validate_base_url(base_url)
