import math
import os
import resource
from time import perf_counter

from app.services.embeddings import LocalEmbeddingService, cosine_similarity

QUESTION_A = "Comment obtenir un crédit immobilier ?"
QUESTION_B = "Quelles sont les conditions pour un prêt immobilier ?"
QUESTION_C = "Quelle est la météo demain ?"


def peak_rss_megabytes() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main() -> None:
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    initial_peak_rss = peak_rss_megabytes()
    load_started = perf_counter()
    service = LocalEmbeddingService()
    load_seconds = perf_counter() - load_started
    loaded_peak_rss = peak_rss_megabytes()

    single_vector = service.embed_text("Question bancaire synthétique en français.")
    if len(single_vector) != 384:
        raise RuntimeError("expected an embedding dimension of 384")
    if not all(isinstance(value, float) for value in single_vector):
        raise RuntimeError("expected only float values")
    if not all(math.isfinite(value) for value in single_vector):
        raise RuntimeError("expected only finite values")

    vector_a, vector_b, vector_c = service.embed_texts(
        [QUESTION_A, QUESTION_B, QUESTION_C]
    )
    similarity_ab = cosine_similarity(vector_a, vector_b)
    similarity_ac = cosine_similarity(vector_a, vector_c)
    if similarity_ab <= similarity_ac:
        raise RuntimeError("expected the related questions to be more similar")

    print(f"dimension={len(single_vector)}")
    print(f"finite_values={all(math.isfinite(value) for value in single_vector)}")
    print(f"similarity_a_b={similarity_ab:.6f}")
    print(f"similarity_a_c={similarity_ac:.6f}")
    print(f"load_seconds={load_seconds:.3f}")
    print(f"peak_rss_before_load_mb={initial_peak_rss:.1f}")
    print(f"peak_rss_after_load_mb={loaded_peak_rss:.1f}")
    print(f"peak_rss_load_increase_mb={loaded_peak_rss - initial_peak_rss:.1f}")
    print("offline_mode=true")


if __name__ == "__main__":
    main()
