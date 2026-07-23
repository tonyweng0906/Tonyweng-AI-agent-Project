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