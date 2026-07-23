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