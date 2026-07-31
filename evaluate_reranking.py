import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from courtmate.hybrid_search import (
    HybridSearch,
)
from courtmate.rerank import (
    RERANK_MODEL,
    rerank_documents,
)
from evaluate_retrieval import (
    GROUND_TRUTH_PATH,
    hit_rate,
    mean_reciprocal_rank,
    split_by_document,
)


TOP_K = 5
CANDIDATE_COUNT = 5

RESULTS_PATH = Path(
    "data/reranking-evaluation-results.csv"
)
BEST_CONFIG_PATH = Path(
    "data/best-reranking-config.json"
)

CONFIGURATIONS = [
    "hybrid_without_reranking",
    "hybrid_with_llm_reranking",
]


def calculate_metrics(
    relevance_total: list[list[bool]],
) -> dict[str, float]:
    relevance_at_1 = [
        relevance[:1]
        for relevance in relevance_total
    ]
    relevance_at_3 = [
        relevance[:3]
        for relevance in relevance_total
    ]
    relevance_at_5 = [
        relevance[:5]
        for relevance in relevance_total
    ]

    return {
        "hit_rate_at_1": hit_rate(
            relevance_at_1
        ),
        "hit_rate_at_3": hit_rate(
            relevance_at_3
        ),
        "hit_rate_at_5": hit_rate(
            relevance_at_5
        ),
        "mrr_at_5": (
            mean_reciprocal_rank(
                relevance_at_5
            )
        ),
    }


def evaluate_records(
    records: list[dict[str, Any]],
    retriever: HybridSearch,
    split_name: str,
) -> dict[str, dict[str, float]]:
    baseline_relevance = []
    reranked_relevance = []
    reranking_errors = 0

    for position, record in enumerate(
        records,
        start=1,
    ):
        question = str(
            record["question"]
        )
        expected_id = str(
            record["id"]
        )

        documents = retriever.search(
            query=question,
            num_results=CANDIDATE_COUNT,
        )

        baseline_relevance.append(
            [
                str(document["id"])
                == expected_id
                for document in documents
            ]
        )

        try:
            reranked_documents = (
                rerank_documents(
                    question=question,
                    documents=documents,
                )
            )

        except Exception as exception:
            reranking_errors += 1
            reranked_documents = documents

            print(
                f"Reranking failed for "
                f"{question}: {exception}"
            )

        reranked_relevance.append(
            [
                str(document["id"])
                == expected_id
                for document in (
                    reranked_documents
                )
            ]
        )

        print(
            f"[{split_name} "
            f"{position}/{len(records)}] "
            f"{question}"
        )

        time.sleep(0.1)

    baseline_metrics = (
        calculate_metrics(
            baseline_relevance
        )
    )
    baseline_metrics["errors"] = 0

    reranked_metrics = (
        calculate_metrics(
            reranked_relevance
        )
    )
    reranked_metrics["errors"] = (
        reranking_errors
    )

    return {
        "hybrid_without_reranking": (
            baseline_metrics
        ),
        "hybrid_with_llm_reranking": (
            reranked_metrics
        ),
    }


def print_results(
    title: str,
    scores: dict[
        str,
        dict[str, float],
    ],
) -> None:
    print(f"\n{title}:")

    for name, metrics in scores.items():
        print(
            f"{name}: "
            f"Hit Rate@1="
            f"{metrics['hit_rate_at_1']:.3f}, "
            f"Hit Rate@3="
            f"{metrics['hit_rate_at_3']:.3f}, "
            f"Hit Rate@5="
            f"{metrics['hit_rate_at_5']:.3f}, "
            f"MRR@5="
            f"{metrics['mrr_at_5']:.3f}, "
            f"errors="
            f"{int(metrics['errors'])}"
        )


def main() -> None:
    ground_truth = pd.read_csv(
        GROUND_TRUTH_PATH
    ).fillna("")

    validation_dataframe, test_dataframe = (
        split_by_document(
            ground_truth
        )
    )

    validation_records = (
        validation_dataframe.to_dict(
            orient="records"
        )
    )
    test_records = (
        test_dataframe.to_dict(
            orient="records"
        )
    )

    print(
        f"Re-ranking model: "
        f"{RERANK_MODEL}"
    )
    print(
        f"Candidate documents: "
        f"{CANDIDATE_COUNT}"
    )

    retriever = HybridSearch()

    validation_scores = evaluate_records(
        records=validation_records,
        retriever=retriever,
        split_name="validation",
    )

    print_results(
        "Validation results",
        validation_scores,
    )

    selected_configuration = max(
        CONFIGURATIONS,
        key=lambda name: (
            validation_scores[name][
                "mrr_at_5"
            ],
            validation_scores[name][
                "hit_rate_at_1"
            ],
            validation_scores[name][
                "hit_rate_at_3"
            ],
            -validation_scores[name][
                "errors"
            ],
        ),
    )

    print(
        f"\nSelected using validation data: "
        f"{selected_configuration}"
    )

    test_scores = evaluate_records(
        records=test_records,
        retriever=retriever,
        split_name="test",
    )

    print_results(
        "Held-out test results",
        test_scores,
    )

    rows = []

    for name in CONFIGURATIONS:
        rows.append(
            {
                "configuration": name,
                "candidate_count": (
                    CANDIDATE_COUNT
                ),
                "top_k": TOP_K,
                "rerank_model": (
                    RERANK_MODEL
                    if "with_llm" in name
                    else ""
                ),
                "validation_hit_rate_at_1": (
                    validation_scores[name][
                        "hit_rate_at_1"
                    ]
                ),
                "validation_hit_rate_at_3": (
                    validation_scores[name][
                        "hit_rate_at_3"
                    ]
                ),
                "validation_hit_rate_at_5": (
                    validation_scores[name][
                        "hit_rate_at_5"
                    ]
                ),
                "validation_mrr_at_5": (
                    validation_scores[name][
                        "mrr_at_5"
                    ]
                ),
                "validation_errors": int(
                    validation_scores[name][
                        "errors"
                    ]
                ),
                "test_hit_rate_at_1": (
                    test_scores[name][
                        "hit_rate_at_1"
                    ]
                ),
                "test_hit_rate_at_3": (
                    test_scores[name][
                        "hit_rate_at_3"
                    ]
                ),
                "test_hit_rate_at_5": (
                    test_scores[name][
                        "hit_rate_at_5"
                    ]
                ),
                "test_mrr_at_5": (
                    test_scores[name][
                        "mrr_at_5"
                    ]
                ),
                "test_errors": int(
                    test_scores[name][
                        "errors"
                    ]
                ),
                "selected": (
                    name
                    == selected_configuration
                ),
            }
        )

    pd.DataFrame(rows).to_csv(
        RESULTS_PATH,
        index=False,
    )

    selected_config = {
        "enabled": (
            selected_configuration
            == "hybrid_with_llm_reranking"
        ),
        "configuration": (
            selected_configuration
        ),
        "method": "llm",
        "model": RERANK_MODEL,
        "candidate_count": (
            CANDIDATE_COUNT
        ),
        "top_k": TOP_K,
        "selected_using": (
            "validation_mrr_at_5"
        ),
    }

    with BEST_CONFIG_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            selected_config,
            file,
            indent=2,
        )

    selected_test = test_scores[
        selected_configuration
    ]

    print(
        f"\nFinal selected test result: "
        f"Hit Rate@1="
        f"{selected_test['hit_rate_at_1']:.3f}, "
        f"Hit Rate@5="
        f"{selected_test['hit_rate_at_5']:.3f}, "
        f"MRR@5="
        f"{selected_test['mrr_at_5']:.3f}"
    )

    print(
        f"Saved results to: "
        f"{RESULTS_PATH}"
    )
    print(
        f"Saved configuration to: "
        f"{BEST_CONFIG_PATH}"
    )


if __name__ == "__main__":
    main()