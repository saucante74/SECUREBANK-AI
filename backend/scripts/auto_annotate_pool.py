import argparse
import json
import sys
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from scripts.build_annotation_pool import AnnotationPool, CandidateAnnotation

DEFAULT_SOURCE_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "rag_annotation_pool_v2.json"
)
DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "rag_annotation_judgments_llm_v2.json"
)
DEFAULT_BASE_URL = "http://127.0.0.1:8081"
DEFAULT_MODEL = "qwen2.5-3b-instruct-q4_k_m.gguf"
PROMPT_VERSION = "qwen-rag-relevance-v2"
REQUEST_TIMEOUT_SECONDS = 120.0


class LLMJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    relevance: Literal[0, 1, 2]
    reason: str = Field(min_length=1, max_length=300)

    @field_validator("relevance", mode="before")
    @classmethod
    def reject_boolean_relevance(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("relevance must be an integer")
        return value

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reason must not be blank")
        return normalized


class StoredJudgment(LLMJudgment):
    question_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)


class JudgmentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    provenance: Literal["llm_judge"] = "llm_judge"
    model: str = Field(min_length=1)
    prompt_version: str | None = None
    corpus_version: Literal["v2"] = "v2"
    source_schema_version: Literal[3] = 3
    corpus_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    updated_at: datetime


class JudgmentFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    metadata: JudgmentMetadata
    judgments: tuple[StoredJudgment, ...] = ()


class SelectionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    question_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)


class SelectionFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    corpus_version: Literal["v2"]
    selections: tuple[SelectionEntry, ...] = Field(min_length=1)

    @field_validator("selections")
    @classmethod
    def validate_unique_pairs(
        cls,
        selections: tuple[SelectionEntry, ...],
    ) -> tuple[SelectionEntry, ...]:
        pairs = [
            (selection.question_id, selection.chunk_id) for selection in selections
        ]
        if len(pairs) != len(set(pairs)):
            raise ValueError("selection pairs must be unique")
        return selections


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str


class ChatChoice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: ChatMessage


class ChatCompletion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    choices: tuple[ChatChoice, ...] = Field(min_length=1)


class FakeRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(content_length)
        content = json.dumps(
            {
                "relevance": 2,
                "reason": "Le passage répond directement à la question.",
            },
            ensure_ascii=False,
        )
        response = json.dumps(
            {"choices": [{"message": {"content": content}}]},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format_string: str, *arguments: object) -> None:
        return


def load_pool(path: Path) -> AnnotationPool:
    pool = AnnotationPool.model_validate_json(path.read_text(encoding="utf-8"))
    if pool.schema_version != 3 or pool.metadata is None:
        raise ValueError("source pool must use schema 3 with metadata")
    if pool.metadata.corpus_version != "v2":
        raise ValueError("source pool must use corpus version v2")
    return pool


def load_judgment_file(path: Path) -> JudgmentFile:
    return JudgmentFile.model_validate_json(path.read_text(encoding="utf-8"))


def load_selection_file(path: Path) -> SelectionFile:
    return SelectionFile.model_validate_json(path.read_text(encoding="utf-8"))


def current_time() -> datetime:
    return datetime.now(UTC)


def create_judgment_file(pool: AnnotationPool, model: str) -> JudgmentFile:
    if pool.metadata is None:
        raise ValueError("source pool metadata is required")
    timestamp = current_time()
    return JudgmentFile(
        metadata=JudgmentMetadata(
            model=model,
            prompt_version=PROMPT_VERSION,
            corpus_fingerprint=pool.metadata.corpus_fingerprint,
            created_at=timestamp,
            updated_at=timestamp,
        )
    )


def candidate_keys(pool: AnnotationPool) -> frozenset[tuple[str, str]]:
    return frozenset(
        (question.question_id, candidate.chunk_id)
        for question in pool.questions
        for candidate in question.candidates
    )


def validate_selection(pool: AnnotationPool, selection_file: SelectionFile) -> None:
    valid_keys = candidate_keys(pool)
    unknown_pairs = [
        (selection.question_id, selection.chunk_id)
        for selection in selection_file.selections
        if (selection.question_id, selection.chunk_id) not in valid_keys
    ]
    if unknown_pairs:
        raise ValueError(f"selection contains unknown candidates: {unknown_pairs!r}")


def validate_resume(
    pool: AnnotationPool,
    judgment_file: JudgmentFile,
    model: str,
) -> None:
    if pool.metadata is None:
        raise ValueError("source pool metadata is required")
    metadata = judgment_file.metadata
    if metadata.model != model:
        raise ValueError("existing judgments use a different model")
    if metadata.prompt_version != PROMPT_VERSION:
        raise ValueError("existing judgments use a different prompt version")
    if metadata.corpus_fingerprint != pool.metadata.corpus_fingerprint:
        raise ValueError("existing judgments use a different corpus")
    valid_keys = candidate_keys(pool)
    stored_keys = [
        (judgment.question_id, judgment.chunk_id)
        for judgment in judgment_file.judgments
    ]
    if len(stored_keys) != len(set(stored_keys)):
        raise ValueError("existing judgments contain duplicate candidates")
    if not set(stored_keys).issubset(valid_keys):
        raise ValueError("existing judgments contain unknown candidates")


def save_judgment_file(judgment_file: JudgmentFile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        judgment_file.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "relevance": {"type": "integer", "enum": [0, 1, 2]},
            "reason": {"type": "string", "minLength": 1, "maxLength": 300},
        },
        "required": ["relevance", "reason"],
        "additionalProperties": False,
    }


def system_prompt() -> str:
    return (
        "Tu évalues la pertinence d'un passage pour répondre à une question.\n\n"
        "Grille obligatoire :\n"
        "Note 0 — Non pertinent :\n"
        "- Le passage ne fournit aucun élément permettant de répondre à la question.\n"
        "- Une simple mention du thème, sans information répondant à la demande, "
        "ne suffit pas.\n"
        "Note 1 — Partiellement pertinent :\n"
        "- Le passage fournit une information utile, mais incomplète ou indirecte.\n"
        "- Il traite d'un produit bancaire différent, même si certains critères "
        "sont similaires.\n"
        "- Il ne répond qu'à une partie substantielle de la question.\n"
        "Note 2 — Directement pertinent :\n"
        "- Le passage répond explicitement à la question.\n"
        "- Il concerne le bon produit bancaire et le bon contexte.\n"
        "- Il n'est pas nécessaire que le passage soit exhaustif, mais il doit "
        "fournir une réponse directe et suffisante.\n\n"
        "Consignes obligatoires :\n"
        "- Distingue strictement le crédit immobilier du crédit à la consommation.\n"
        "- Ne confonds pas une simple mention du sujet avec une réponse.\n"
        "- Ne sous-évalue pas un passage qui énumère directement les éléments "
        "demandés.\n"
        "- Justifie uniquement à partir des informations présentes dans le passage.\n"
        "- N'invente aucune information absente.\n\n"
        "Exemples de calibration :\n"
        "- Question sur les éléments de calcul d'un crédit immobilier + passage "
        "sur une garantie immobilière sans élément de calcul : note 0.\n"
        "- Même question + revenus, charges et crédits pour un prêt personnel : "
        "note 1.\n"
        "- Même question + revenus, charges, crédits et taux d'effort pour un "
        "crédit immobilier : note 2.\n\n"
        "Réponds uniquement avec le JSON demandé et une justification courte."
    )


def request_payload(
    question: str,
    candidate: CandidateAnnotation,
    model: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "temperature": 0,
        "max_tokens": 100,
        "messages": [
            {"role": "system", "content": system_prompt()},
            {
                "role": "user",
                "content": f"Question : {question}\nPassage : {candidate.text}",
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "relevance_judgment",
                "strict": True,
                "schema": response_schema(),
            },
        },
    }


def request_judgment(
    base_url: str,
    question: str,
    candidate: CandidateAnnotation,
    model: str,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
) -> LLMJudgment:
    request = Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(
            request_payload(question, candidate, model),
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        completion = ChatCompletion.model_validate_json(response.read())
    return LLMJudgment.model_validate_json(completion.choices[0].message.content)


def validate_base_url(base_url: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise ValueError("base URL must use HTTP on the local loopback interface")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("base URL must not contain credentials")


def pending_candidates(
    pool: AnnotationPool,
    judgment_file: JudgmentFile,
    selection_file: SelectionFile | None = None,
) -> Iterator[tuple[str, str, CandidateAnnotation]]:
    completed = {
        (judgment.question_id, judgment.chunk_id)
        for judgment in judgment_file.judgments
    }
    if selection_file is not None:
        candidates_by_key = {
            (question.question_id, candidate.chunk_id): (
                question.question,
                candidate,
            )
            for question in pool.questions
            for candidate in question.candidates
        }
        for selection in selection_file.selections:
            key = (selection.question_id, selection.chunk_id)
            if key not in completed:
                question, candidate = candidates_by_key[key]
                yield selection.question_id, question, candidate
        return
    for question in pool.questions:
        for candidate in question.candidates:
            key = (question.question_id, candidate.chunk_id)
            if key not in completed:
                yield question.question_id, question.question, candidate


def append_judgment(
    judgment_file: JudgmentFile,
    question_id: str,
    candidate: CandidateAnnotation,
    judgment: LLMJudgment,
) -> JudgmentFile:
    stored = StoredJudgment(
        question_id=question_id,
        chunk_id=candidate.chunk_id,
        relevance=judgment.relevance,
        reason=judgment.reason,
    )
    metadata = judgment_file.metadata.model_copy(update={"updated_at": current_time()})
    return judgment_file.model_copy(
        update={
            "metadata": metadata,
            "judgments": (*judgment_file.judgments, stored),
        }
    )


def annotate_pool(
    pool: AnnotationPool,
    judgment_file: JudgmentFile,
    output_path: Path,
    base_url: str,
    model: str,
    limit: int | None,
    selection_file: SelectionFile | None = None,
) -> JudgmentFile:
    annotated = 0
    candidates = pending_candidates(pool, judgment_file, selection_file)
    for question_id, question, candidate in candidates:
        if limit is not None and annotated >= limit:
            break
        judgment = request_judgment(base_url, question, candidate, model)
        judgment_file = append_judgment(
            judgment_file,
            question_id,
            candidate,
            judgment,
        )
        save_judgment_file(judgment_file, output_path)
        annotated += 1
        print(f"Annotated {question_id} / {candidate.chunk_id}: {judgment.relevance}")
    print(f"New judgments: {annotated}")
    print(f"Total judgments: {len(judgment_file.judgments)}")
    return judgment_file


@contextmanager
def fake_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--selection-file", type=Path)
    parser.add_argument("--test-mode", action="store_true")
    parsed = parser.parse_args(arguments)
    if parsed.limit is not None and parsed.limit < 1:
        parser.error("--limit must be greater than zero")
    if parsed.test_mode and parsed.output == DEFAULT_OUTPUT_PATH:
        parser.error("--test-mode requires an explicit --output path")
    return parsed


def run(arguments: argparse.Namespace, base_url: str) -> int:
    source_path = arguments.source.resolve()
    output_path = arguments.output.resolve()
    if source_path == output_path:
        raise ValueError("source and output paths must be different")
    validate_base_url(base_url)
    pool = load_pool(source_path)
    selection_file = None
    if arguments.selection_file is not None:
        selection_file = load_selection_file(arguments.selection_file.resolve())
        validate_selection(pool, selection_file)
    if output_path.exists():
        judgment_file = load_judgment_file(output_path)
        validate_resume(pool, judgment_file, arguments.model)
    else:
        judgment_file = create_judgment_file(pool, arguments.model)
    annotate_pool(
        pool,
        judgment_file,
        output_path,
        base_url,
        arguments.model,
        arguments.limit,
        selection_file,
    )
    return 0


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        parsed = parse_arguments(arguments)
        if parsed.test_mode:
            with fake_server() as base_url:
                return run(parsed, base_url)
        return run(parsed, parsed.base_url)
    except (HTTPError, OSError, URLError, ValidationError, ValueError) as error:
        print(f"Automatic annotation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
