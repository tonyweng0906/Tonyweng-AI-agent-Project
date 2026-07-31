import json
import random
from pathlib import Path
from typing import Any

import pandas as pd
from minsearch import Index

from courtmate.ingest import (
    KEYWORD_FIELDS,
    TEXT_FIELDS,
    load_documents,
)


TOP_K = 5
RANDOM_SEED = 42

GROUND_TRUTH_PATH = Path(
    "data/ground-truth-retrieval.csv"
)
RESULTS_PATH = Path(
    "data/retrieval-evaluation-results.csv"
)
BEST_BOOST_PATH = Path(
    "data/best-minsearch-boost.json"
)


NO_BOOST: dict[str, float] = {}

MANUAL_BOOST = {
    "category": 1.2,
    "title": 2.0,
    "content": 1.0,
    "coach_name": 1.5,
    "skill_level": 1.0,
    "location": 0.5,
}

PREVIOUS_OPTIMIZED_BOOST = {
    "category": 2.6765387031145362,
    "title": 0.3477553305176646,
    "content": 1.2657654590558112,
    "coach_name": 0.11918887775228137,
    "skill_level": 0.6559139244108101,
    "location": 1.0107105762067248,
}

CANDIDATES = {
    "no_boost": NO_BOOST,
    "manual_boost": MANUAL_BOOST,
    "previous_optimized_boost": (
        PREVIOUS_OPTIMIZED_BOOST
    ),
}


def build_index() -> Index:
    documents = load_documents()

    search_index = Index(
        text_fields=TEXT_FIELDS,
        keyword_fields=KEYWORD_FIELDS,
    )

    search_index.fit(documents)

    print(
        f"Knowledge base loaded: "
        f"{len(documents)} documents"
    )

    return search_index


def search(
    search_index: Index,
    query: str,
    boost: dict[str, float],
) -> list[dict[str, Any]]:
    return search_index.search(
        query=query,
        filter_dict={},
        boost_dict=boost,
        num_results=TOP_K,
    )


def hit_rate(
    relevance_total: list[list[bool]],
) -> float:
    if not relevance_total:
        return 0.0

    hits = sum(
        any(relevance)
        for relevance in relevance_total
    )

    return hits / len(relevance_total)


def mean_reciprocal_rank(
    relevance_total: list[list[bool]],
) -> float:
    if not relevance_total:
        return 0.0

    total_score = 0.0

    for relevance in relevance_total:
        for rank, is_relevant in enumerate(
            relevance,
            start=1,
        ):
            if is_relevant:
                total_score += 1 / rank
                break

    return total_score / len(relevance_total)


def evaluate(
    search_index: Index,
    records: list[dict[str, str]],
    boost: dict[str, float],
) -> dict[str, float]:
    relevance_total = []

    for record in records:
        question = record["question"]
        expected_id = str(record["id"])

        results = search(
            search_index=search_index,
            query=question,
            boost=boost,
        )

        relevance = [
            str(document.get("id")) == expected_id
            for document in results
        ]

        relevance_total.append(relevance)

    return {
        "hit_rate": hit_rate(relevance_total),
        "mrr": mean_reciprocal_rank(
            relevance_total
        ),
    }


def split_by_document(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split by document ID so questions generated from the same
    document cannot appear in both validation and test sets.
    """
    document_ids = list(
        dataframe["id"].astype(str).unique()
    )

    if len(document_ids) < 2:
        raise ValueError(
            "At least two document IDs are required."
        )

    random_generator = random.Random(
        RANDOM_SEED
    )
    random_generator.shuffle(document_ids)

    validation_size = max(
        1,
        round(len(document_ids) * 0.7),
    )

    validation_ids = set(
        document_ids[:validation_size]
    )
    test_ids = set(
        document_ids[validation_size:]
    )

    if not test_ids:
        moved_id = validation_ids.pop()
        test_ids.add(moved_id)

    validation_dataframe = dataframe[
        dataframe["id"].astype(str).isin(
            validation_ids
        )
    ].copy()

    test_dataframe = dataframe[
        dataframe["id"].astype(str).isin(
            test_ids
        )
    ].copy()

    print(
        "Validation document IDs:",
        sorted(validation_ids),
    )
    print(
        "Test document IDs:",
        sorted(test_ids),
    )

    return (
        validation_dataframe,
        test_dataframe,
    )


def main() -> None:
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(
            f"Ground truth not found: "
            f"{GROUND_TRUTH_PATH}"
        )

    dataframe = pd.read_csv(
        GROUND_TRUTH_PATH
    ).fillna("")

    required_columns = {"id", "question"}
    missing_columns = (
        required_columns - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            "Ground truth is missing columns: "
            f"{sorted(missing_columns)}"
        )

    validation_dataframe, test_dataframe = (
        split_by_document(dataframe)
    )

    validation_records = (
        validation_dataframe.to_dict(
            orient="records"
        )
    )
    test_records = test_dataframe.to_dict(
        orient="records"
    )

    print(
        f"Validation questions: "
        f"{len(validation_records)}"
    )
    print(
        f"Test questions: {len(test_records)}"
    )
    print(f"Top K: {TOP_K}")

    search_index = build_index()

    validation_scores = {}

    print("\nValidation results:")

    for name, boost in CANDIDATES.items():
        metrics = evaluate(
            search_index=search_index,
            records=validation_records,
            boost=boost,
        )

        validation_scores[name] = metrics

        print(
            f"{name}: "
            f"Hit Rate@{TOP_K}="
            f"{metrics['hit_rate']:.3f}, "
            f"MRR@{TOP_K}="
            f"{metrics['mrr']:.3f}"
        )

    selected_name = max(
        validation_scores,
        key=lambda name: (
            validation_scores[name]["mrr"],
            validation_scores[name]["hit_rate"],
        ),
    )

    selected_boost = CANDIDATES[
        selected_name
    ]

    print(
        f"\nSelected using validation data: "
        f"{selected_name}"
    )

    test_scores = {}
    result_rows = []

    print("\nHeld-out test results:")

    for name, boost in CANDIDATES.items():
        metrics = evaluate(
            search_index=search_index,
            records=test_records,
            boost=boost,
        )

        test_scores[name] = metrics

        result_rows.append(
            {
                "approach": name,
                "top_k": TOP_K,
                "validation_hit_rate": (
                    validation_scores[name][
                        "hit_rate"
                    ]
                ),
                "validation_mrr": (
                    validation_scores[name]["mrr"]
                ),
                "test_hit_rate": (
                    metrics["hit_rate"]
                ),
                "test_mrr": metrics["mrr"],
                "selected": (
                    name == selected_name
                ),
            }
        )

        print(
            f"{name}: "
            f"Hit Rate@{TOP_K}="
            f"{metrics['hit_rate']:.3f}, "
            f"MRR@{TOP_K}="
            f"{metrics['mrr']:.3f}"
        )

    results_dataframe = pd.DataFrame(
        result_rows
    )

    results_dataframe.to_csv(
        RESULTS_PATH,
        index=False,
    )

    with BEST_BOOST_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            selected_boost,
            file,
            indent=2,
        )

    print(
        f"\nSaved comparison to: "
        f"{RESULTS_PATH}"
    )
    print(
        f"Saved selected boost to: "
        f"{BEST_BOOST_PATH}"
    )

    selected_test = test_scores[
        selected_name
    ]

    print(
        f"\nFinal selected test result: "
        f"Hit Rate@{TOP_K}="
        f"{selected_test['hit_rate']:.3f}, "
        f"MRR@{TOP_K}="
        f"{selected_test['mrr']:.3f}"
    )


if __name__ == "__main__":
    main()