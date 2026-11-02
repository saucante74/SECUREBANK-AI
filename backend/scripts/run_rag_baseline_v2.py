import os
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from app.services.baseline_history import (
    build_baseline_run,
    current_code_version,
    save_baseline_run,
)
from scripts.compare_retrievers import create_local_comparison, run_comparison


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    pipeline = create_local_comparison(index_chunks=False, corpus_version="v2")
    comparisons = run_comparison(pipeline)
    run = build_baseline_run(
        comparisons,
        code_version=current_code_version(repository_root),
        metadata=pipeline.metadata,
    )
    output_path = save_baseline_run(run)
    print(f"Baseline v2 saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
