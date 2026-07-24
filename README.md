# Tonyweng-AI-agent-Project
# CourtMate AI

CourtMate is an AI assistant for badminton club information,
coach discovery, court booking policies, and drop-in programs.

## Problem

Badminton club staff repeatedly answer questions about coach
specialties, lesson types, booking rules, cancellations, facilities,
and drop-in sessions.

CourtMate uses retrieval-augmented generation to search a badminton
club knowledge base and produce grounded answers.

## Current Features

- Search badminton club policies
- Answer coach-related questions
- Explain lesson and drop-in programs
- Return source documents used in the answer

## Dataset

The knowledge base is stored in:

`data/knowledge_base.csv`

Each document contains:

- id
- category
- title
- content
- coach_name
- skill_level
- location

The repository uses synthetic and anonymized data. No real customer
personal information is included.

## Installation

```bash
uv sync
```

## Retrieval Evaluation

A ground-truth dataset was created by generating user questions for
each knowledge-base document. Each question is associated with its
expected document ID.

The retrieval flow was evaluated using:

- Hit Rate
- Mean Reciprocal Rank
- A document-level validation/test split

| Retrieval approach | Hit Rate | MRR |
|---|---:|---:|
| MinSearch without boost | 0.xx | 0.xx |
| MinSearch manual boost | 0.xx | 0.xx |
| MinSearch optimized boost | 0.xx | 0.xx |

The optimized configuration was selected for the final RAG flow.

The evaluation notebook is available at:

`notebooks/02-retrieval-evaluation.ipynb`


## RAG Evaluation

The final generated answers were evaluated using an
LLM-as-a-Judge approach.

The evaluator classified each answer as:

- RELEVANT
- PARTLY_RELEVANT
- NON_RELEVANT

The same evaluation question sample was used to compare two prompt
strategies.

| Configuration | Relevant | Partly relevant | Non-relevant | Weighted score |
|---|---:|---:|---:|---:|
| Baseline prompt | 0.xx | 0.xx | 0.xx | 0.xx |
| Improved prompt | 0.xx | 0.xx | 0.xx | 0.xx |

The improved prompt was selected because it produced more directly
grounded answers and fewer unsupported claims.

The complete evaluation is available in:

`notebooks/03-rag-evaluation.ipynb`


## Application Structure

The notebook prototype was converted into a Python application.

- `courtmate/ingest.py`: loads the knowledge base and builds the
  MinSearch index
- `courtmate/rag.py`: performs retrieval, prompt construction and
  LLM generation
- `app.py`: exposes the RAG flow through a Flask API

Because MinSearch is an in-memory search engine, the ingestion process
runs when the application starts.

## Run the API

Install dependencies:

```bash
uv sync

## Monitoring

CourtMate stores every RAG conversation in PostgreSQL.

For each request, the application records:

- question and generated answer
- retrieved sources
- generation model
- judge model
- response time
- relevance classification
- relevance explanation
- generation token usage
- evaluation token usage
- timestamp

Users can submit positive or negative feedback through the
`POST /feedback` endpoint.

## Monitoring Dashboard

Grafana is available at:

`http://localhost:3000`

The dashboard includes:

1. Daily question volume
2. Relevance distribution
3. Average response time
4. Token usage
5. User feedback distribution
6. Total question count
7. Positive feedback percentage
8. Recent conversations

## Run with Docker Compose

Create `.env` from `.env.example`.

Start all services:

```bash
docker compose up -d --build