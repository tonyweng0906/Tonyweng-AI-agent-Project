import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from minsearch import Index
from openai import OpenAI

from courtmate.config import OPENAI_API_KEY
from courtmate.ingest import (
    KEYWORD_FIELDS,
    TEXT_FIELDS,
    load_documents,
)

from evaluation.evaluate_retrieval import (
    hit_rate,
    mean_reciprocal_rank,
    split_by_document,
)

TOP_K = 5
RRF_K = 60

GROUND_TRUTH_PATH = Path(
    "data/ground-truth-retrieval.csv"
)
RESULTS_PATH = Path(
    "data/evaluation/hybrid-retrieval-evaluation-results.csv"
)
BEST_CONFIG_PATH = Path(
    "data/best-retrieval-config.json"
)

EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-small",
)

CANDIDATES = {
    "text_only": 1.0,
    "hybrid_text_70_vector_30": 0.7,
    "hybrid_text_50_vector_50": 0.5,
    "hybrid_text_30_vector_70": 0.3,
    "vector_only": 0.0,
}

embedding_client = OpenAI(
    api_key=OPENAI_API_KEY,
)


def build_text_index(
    documents: list[dict[str, Any]],
) -> Index:
    index = Index(
        text_fields=TEXT_FIELDS,
        keyword_fields=KEYWORD_FIELDS,
    )

    index.fit(documents)

    return index


def format_document(
    document: dict[str, Any],
) -> str:
    """Convert one document into text for embedding."""
    values = []

    for field in TEXT_FIELDS:
        value = str(
            document.get(field, "")
        ).strip()

        if value:
            values.append(
                f"{field}: {value}"
            )

    return "\n".join(values)


def create_embeddings(
    texts: list[str],
) -> np.ndarray:
    """Create normalized embeddings for a batch of texts."""
    if not texts:
        raise ValueError(
            "At least one text is required."
        )

    response = (
        embedding_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
    )

    ordered_items = sorted(
        response.data,
        key=lambda item: item.index,
    )

    embeddings = np.asarray(
        [
            item.embedding
            for item in ordered_items
        ],
        dtype=np.float32,
    )

    norms = np.linalg.norm(
        embeddings,
        axis=1,
        keepdims=True,
    )

    norms[norms == 0] = 1.0

    return embeddings / norms


def text_ranking(
    index: Index,
    query: str,
    document_count: int,
) -> list[str]:
    """Return document IDs ranked by MinSearch."""
    results = index.search(
        query=query,
        filter_dict={},
        boost_dict={},
        num_results=document_count,
    )

    return [
        str(document["id"])
        for document in results
    ]


def vector_ranking(
    query_embedding: np.ndarray,
    documents: list[dict[str, Any]],
    document_embeddings: np.ndarray,
) -> list[str]:
    """Return document IDs ranked by cosine similarity."""
    similarities = (
        document_embeddings
        @ query_embedding
    )

    ranked_positions = np.argsort(
        -similarities
    )

    return [
        str(documents[position]["id"])
        for position in ranked_positions
    ]


def reciprocal_rank_fusion(
    text_ids: list[str],
    vector_ids: list[str],
    text_weight: float,
) -> list[str]:
    """
    Combine text and vector rankings using weighted
    Reciprocal Rank Fusion.
    """
    vector_weight = 1.0 - text_weight

    text_ranks = {
        document_id: rank
        for rank, document_id in enumerate(
            text_ids,
            start=1,
        )
    }

    vector_ranks = {
        document_id: rank
        for rank, document_id in enumerate(
            vector_ids,
            start=1,
        )
    }

    all_document_ids = (
        set(text_ranks)
        | set(vector_ranks)
    )

    scores = {}

    for document_id in all_document_ids:
        score = 0.0

        text_rank = text_ranks.get(
            document_id
        )

        if text_rank is not None:
            score += (
                text_weight
                / (RRF_K + text_rank)
            )

        vector_rank = vector_ranks.get(
            document_id
        )

        if vector_rank is not None:
            score += (
                vector_weight
                / (RRF_K + vector_rank)
            )

        scores[document_id] = score

    return sorted(
        all_document_ids,
        key=lambda document_id: (
            -scores[document_id],
            document_id,
        ),
    )


def hybrid_search(
    query: str,
    text_weight: float,
    index: Index,
    documents: list[dict[str, Any]],
    document_embeddings: np.ndarray,
    query_embeddings: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    """Search using text/vector weighted RRF."""
    text_ids = text_ranking(
        index=index,
        query=query,
        document_count=len(documents),
    )

    vector_ids = vector_ranking(
        query_embedding=(
            query_embeddings[query]
        ),
        documents=documents,
        document_embeddings=(
            document_embeddings
        ),
    )

    fused_ids = reciprocal_rank_fusion(
        text_ids=text_ids,
        vector_ids=vector_ids,
        text_weight=text_weight,
    )

    documents_by_id = {
        str(document["id"]): document
        for document in documents
    }

    return [
        documents_by_id[document_id]
        for document_id in fused_ids[:TOP_K]
    ]


def evaluate(
    records: list[dict[str, Any]],
    text_weight: float,
    index: Index,
    documents: list[dict[str, Any]],
    document_embeddings: np.ndarray,
    query_embeddings: dict[str, np.ndarray],
) -> dict[str, float]:
    relevance_total = []

    for record in records:
        question = str(
            record["question"]
        )
        expected_id = str(
            record["id"]
        )

        results = hybrid_search(
            query=question,
            text_weight=text_weight,
            index=index,
            documents=documents,
            document_embeddings=(
                document_embeddings
            ),
            query_embeddings=(
                query_embeddings
            ),
        )

        relevance_total.append(
            [
                str(document["id"])
                == expected_id
                for document in results
            ]
        )

    return {
        "hit_rate": hit_rate(
            relevance_total
        ),
        "mrr": mean_reciprocal_rank(
            relevance_total
        ),
    }


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

    documents = load_documents()
    text_index = build_text_index(
        documents
    )

    document_texts = [
        format_document(document)
        for document in documents
    ]

    all_questions = list(
        dict.fromkeys(
            ground_truth[
                "question"
            ].astype(str)
        )
    )

    print(
        f"Embedding model: "
        f"{EMBEDDING_MODEL}"
    )
    print(
        f"Documents: {len(documents)}"
    )
    print(
        f"Questions: {len(all_questions)}"
    )
    print(
        "Creating document embeddings..."
    )

    document_embeddings = (
        create_embeddings(
            document_texts
        )
    )

    print(
        "Creating question embeddings..."
    )

    question_embedding_matrix = (
        create_embeddings(
            all_questions
        )
    )

    query_embeddings = {
        question: (
            question_embedding_matrix[
                position
            ]
        )
        for position, question in enumerate(
            all_questions
        )
    }

    validation_scores = {}

    print("\nValidation results:")

    for name, text_weight in (
        CANDIDATES.items()
    ):
        metrics = evaluate(
            records=validation_records,
            text_weight=text_weight,
            index=text_index,
            documents=documents,
            document_embeddings=(
                document_embeddings
            ),
            query_embeddings=(
                query_embeddings
            ),
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
            validation_scores[name][
                "hit_rate"
            ],
        ),
    )

    selected_text_weight = (
        CANDIDATES[selected_name]
    )

    print(
        f"\nSelected using validation data: "
        f"{selected_name}"
    )

    test_scores = {}
    result_rows = []

    print("\nHeld-out test results:")

    for name, text_weight in (
        CANDIDATES.items()
    ):
        metrics = evaluate(
            records=test_records,
            text_weight=text_weight,
            index=text_index,
            documents=documents,
            document_embeddings=(
                document_embeddings
            ),
            query_embeddings=(
                query_embeddings
            ),
        )

        test_scores[name] = metrics

        result_rows.append(
            {
                "approach": name,
                "top_k": TOP_K,
                "text_weight": (
                    text_weight
                ),
                "vector_weight": (
                    1.0 - text_weight
                ),
                "validation_hit_rate": (
                    validation_scores[
                        name
                    ]["hit_rate"]
                ),
                "validation_mrr": (
                    validation_scores[
                        name
                    ]["mrr"]
                ),
                "test_hit_rate": (
                    metrics["hit_rate"]
                ),
                "test_mrr": (
                    metrics["mrr"]
                ),
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

    selected_config = {
        "approach": selected_name,
        "top_k": TOP_K,
        "rrf_k": RRF_K,
        "text_weight": (
            selected_text_weight
        ),
        "vector_weight": (
            1.0
            - selected_text_weight
        ),
        "embedding_model": (
            EMBEDDING_MODEL
        ),
        "selected_using": (
            "validation_mrr"
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

    selected_test = (
        test_scores[selected_name]
    )

    print(
        f"\nFinal selected test result: "
        f"Hit Rate@{TOP_K}="
        f"{selected_test['hit_rate']:.3f}, "
        f"MRR@{TOP_K}="
        f"{selected_test['mrr']:.3f}"
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