import json
from typing import Any

import numpy as np
from minsearch import Index
from openai import OpenAI

from courtmate.config import (
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    RETRIEVAL_CONFIG_PATH,
)
from courtmate.ingest import (
    KEYWORD_FIELDS,
    TEXT_FIELDS,
    load_boost,
    load_documents,
)


class HybridSearch:
    """Combine MinSearch and vector retrieval with weighted RRF."""

    def __init__(self) -> None:
        self.documents = load_documents()

        self.documents_by_id = {
            str(document["id"]): document
            for document in self.documents
        }

        self.text_index = Index(
            text_fields=TEXT_FIELDS,
            keyword_fields=KEYWORD_FIELDS,
        )
        self.text_index.fit(
            self.documents
        )

        self.text_boost = load_boost()

        self.config = (
            self._load_config()
        )

        self.text_weight = float(
            self.config.get(
                "text_weight",
                0.5,
            )
        )
        self.vector_weight = float(
            self.config.get(
                "vector_weight",
                0.5,
            )
        )
        self.rrf_k = int(
            self.config.get(
                "rrf_k",
                60,
            )
        )

        self.embedding_model = str(
            self.config.get(
                "embedding_model",
                OPENAI_EMBEDDING_MODEL,
            )
        )

        self.embedding_client = OpenAI(
            api_key=OPENAI_API_KEY,
        )

        document_texts = [
            self._format_document(
                document
            )
            for document in self.documents
        ]

        self.document_embeddings = (
            self._create_embeddings(
                document_texts
            )
        )

        print(
            "Hybrid search loaded: "
            f"{self.config.get('approach', 'hybrid')}, "
            f"text_weight={self.text_weight}, "
            f"vector_weight={self.vector_weight}, "
            f"embedding_model={self.embedding_model}"
        )

    def _load_config(
        self,
    ) -> dict[str, Any]:
        if not RETRIEVAL_CONFIG_PATH.exists():
            return {
                "approach": (
                    "hybrid_text_50_vector_50"
                ),
                "text_weight": 0.5,
                "vector_weight": 0.5,
                "rrf_k": 60,
                "embedding_model": (
                    OPENAI_EMBEDDING_MODEL
                ),
            }

        with RETRIEVAL_CONFIG_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            config = json.load(file)

        text_weight = float(
            config.get(
                "text_weight",
                0.5,
            )
        )
        vector_weight = float(
            config.get(
                "vector_weight",
                0.5,
            )
        )

        if not 0 <= text_weight <= 1:
            raise ValueError(
                "text_weight must be "
                "between 0 and 1."
            )

        if not 0 <= vector_weight <= 1:
            raise ValueError(
                "vector_weight must be "
                "between 0 and 1."
            )

        return config

    @staticmethod
    def _format_document(
        document: dict[str, Any],
    ) -> str:
        values = []

        for field in TEXT_FIELDS:
            value = str(
                document.get(
                    field,
                    "",
                )
            ).strip()

            if value:
                values.append(
                    f"{field}: {value}"
                )

        return "\n".join(values)

    def _create_embeddings(
        self,
        texts: list[str],
    ) -> np.ndarray:
        response = (
            self.embedding_client.embeddings.create(
                model=self.embedding_model,
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

    def _text_ranking(
        self,
        query: str,
    ) -> list[str]:
        results = self.text_index.search(
            query=query,
            filter_dict={},
            boost_dict=self.text_boost,
            num_results=len(
                self.documents
            ),
        )

        return [
            str(document["id"])
            for document in results
        ]

    def _vector_ranking(
        self,
        query: str,
    ) -> list[str]:
        query_embedding = (
            self._create_embeddings(
                [query]
            )[0]
        )

        similarities = (
            self.document_embeddings
            @ query_embedding
        )

        ranked_positions = np.argsort(
            -similarities
        )

        return [
            str(
                self.documents[
                    position
                ]["id"]
            )
            for position in ranked_positions
        ]

    def _fuse_rankings(
        self,
        text_ids: list[str],
        vector_ids: list[str],
    ) -> list[str]:
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
                    self.text_weight
                    / (
                        self.rrf_k
                        + text_rank
                    )
                )

            vector_rank = (
                vector_ranks.get(
                    document_id
                )
            )

            if vector_rank is not None:
                score += (
                    self.vector_weight
                    / (
                        self.rrf_k
                        + vector_rank
                    )
                )

            scores[document_id] = score

        return sorted(
            all_document_ids,
            key=lambda document_id: (
                -scores[document_id],
                document_id,
            ),
        )

    def search(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        text_ids = self._text_ranking(
            query
        )
        vector_ids = (
            self._vector_ranking(
                query
            )
        )

        fused_ids = (
            self._fuse_rankings(
                text_ids=text_ids,
                vector_ids=vector_ids,
            )
        )

        return [
            self.documents_by_id[
                document_id
            ]
            for document_id in (
                fused_ids[:num_results]
            )
        ]