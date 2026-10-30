from pathlib import Path

from app.services.baseline_history import (
    build_baseline_run,
    current_code_version,
    save_baseline_run,
)
from scripts.compare_retrievers import create_local_comparison, run_comparison


def main() -> int:
    repository_root = Path(__file__).resolve().parents[2]
    comparisons = run_comparison(create_local_comparison())
    run = build_baseline_run(
        comparisons,
        code_version=current_code_version(repository_root),
    )
    output_path = save_baseline_run(run)
    print(f"Baseline saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
