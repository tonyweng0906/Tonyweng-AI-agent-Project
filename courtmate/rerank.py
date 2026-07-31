import json
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from courtmate.config import (
    OPENAI_API_KEY,
    OPENAI_RERANK_MODEL,
    RERANK_CONFIG_PATH,
)


def load_rerank_config() -> dict[str, Any]:
    if not RERANK_CONFIG_PATH.exists():
        return {
            "enabled": False,
            "model": OPENAI_RERANK_MODEL,
            "candidate_count": 5,
            "top_k": 5,
        }

    with RERANK_CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


RERANK_CONFIG = load_rerank_config()

RERANK_ENABLED = bool(
    RERANK_CONFIG.get(
        "enabled",
        False,
    )
)

RERANK_MODEL = str(
    RERANK_CONFIG.get(
        "model",
        OPENAI_RERANK_MODEL,
    )
)

RERANK_CANDIDATE_COUNT = int(
    RERANK_CONFIG.get(
        "candidate_count",
        5,
    )
)

print(
    "Document re-ranking loaded: "
    f"enabled={RERANK_ENABLED}, "
    f"model={RERANK_MODEL}, "
    f"candidate_count="
    f"{RERANK_CANDIDATE_COUNT}"
)

rerank_client = OpenAI(
    api_key=OPENAI_API_KEY,
)


class RankedDocument(BaseModel):
    document_id: str = Field(
        description=(
            "The exact ID of one supplied document."
        )
    )
    relevance_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Relevance to the user question, "
            "from 0 to 100."
        ),
    )


class RerankResult(BaseModel):
    ranked_documents: list[RankedDocument]


RERANK_INSTRUCTIONS = """
You are a document re-ranking system for a badminton club
retrieval-augmented generation application.

Rank every supplied document by how useful it is for answering
the USER QUESTION.

Rules:
- Return every supplied document exactly once.
- Use the exact document IDs provided.
- Rank documents containing the direct answer first.
- Prefer specific factual information over general word overlap.
- A document containing only related vocabulary but no useful answer
  should receive a lower score.
- Do not answer the user question.
- Do not invent document IDs or document content.
""".strip()


def rerank_documents(
    question: str,
    documents: list[dict[str, Any]],
    model: str = RERANK_MODEL,
) -> list[dict[str, Any]]:
    """Re-rank retrieved documents using an LLM."""
    if len(documents) <= 1:
        return documents

    documents_for_prompt = [
        {
            "document_id": str(
                document["id"]
            ),
            "category": document.get(
                "category",
                "",
            ),
            "title": document.get(
                "title",
                "",
            ),
            "content": document.get(
                "content",
                "",
            ),
            "coach_name": document.get(
                "coach_name",
                "",
            ),
            "skill_level": document.get(
                "skill_level",
                "",
            ),
            "location": document.get(
                "location",
                "",
            ),
        }
        for document in documents
    ]

    prompt = {
        "user_question": question,
        "documents": documents_for_prompt,
    }

    response = rerank_client.responses.parse(
        model=model,
        instructions=RERANK_INSTRUCTIONS,
        input=json.dumps(
            prompt,
            ensure_ascii=False,
        ),
        text_format=RerankResult,
    )

    result = response.output_parsed

    if result is None:
        raise RuntimeError(
            "The re-ranker did not return "
            "structured output."
        )

    documents_by_id = {
        str(document["id"]): document
        for document in documents
    }

    valid_rankings = []
    seen_ids = set()

    for ranking in sorted(
        result.ranked_documents,
        key=lambda item: (
            -item.relevance_score
        ),
    ):
        document_id = str(
            ranking.document_id
        )

        if document_id not in documents_by_id:
            continue

        if document_id in seen_ids:
            continue

        valid_rankings.append(
            documents_by_id[document_id]
        )
        seen_ids.add(document_id)

    # Preserve any document omitted by the model.
    for document in documents:
        document_id = str(
            document["id"]
        )

        if document_id not in seen_ids:
            valid_rankings.append(
                document
            )
            seen_ids.add(document_id)

    return valid_rankings