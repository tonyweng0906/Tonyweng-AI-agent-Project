# Badminton Court AI Agent

An AI-powered assistant for badminton court operations, designed to reduce repetitive work related to court bookings, coach availability, lesson scheduling, cancellations, drop-in sessions, and customer inquiries.

This project is developed as part of the **LLM Zoomcamp final project**, following the structure and methodology demonstrated in the DataTalksClub project example.

---

## 1. Project Overview

Badminton facilities often manage information across multiple places, including:

* Court schedules
* Coach availability
* Private lesson bookings
* Group classes
* Drop-in sessions
* Cancellation policies
* Membership information
* Pricing and facility rules

Staff frequently need to answer the same questions and manually coordinate schedules between customers, coaches, and available courts.

The goal of this project is to build an AI agent that can understand natural-language questions, retrieve relevant facility information, and eventually support booking-related actions.

Example user questions include:

* Which coaches are available on Saturday?
* Are there courts available tomorrow evening?
* What are the drop-in times this week?
* How much does a private lesson cost?
* What is the cancellation policy?
* Can I reschedule my lesson?
* Which coach is suitable for a beginner?
* Are there any group classes this weekend?

---

## 2. Problem Statement

The current booking and customer-service process contains repetitive manual tasks.

Staff may need to:

1. Search through schedules.
2. Check coach availability.
3. Check court availability.
4. Explain pricing and policies.
5. coordinate cancellations and rescheduling.
6. Respond repeatedly to common customer questions.
7. Update operational records manually.

This creates several problems:

* Slow response times
* Repetitive administrative work
* Inconsistent answers
* Scheduling conflicts
* Difficulty finding information quickly
* Increased workload during busy periods

The AI agent provides a single conversational interface for accessing facility information.

---

## 3. Project Goals

The current version of the project focuses on building a reliable question-answering and monitoring system.

### Current goals

* Build a searchable badminton facility knowledge base.
* Retrieve relevant information using semantic search.
* Generate grounded answers with an LLM.
* Evaluate retrieval quality.
* Evaluate generated RAG answers.
* Expose the assistant through a Flask API.
* Record conversations and user feedback in PostgreSQL.
* Monitor application activity using Grafana.
* Run the complete application with Docker Compose.

### Future goals

* Check real-time court availability.
* Check real-time coach availability.
* Create new bookings.
* Cancel or reschedule lessons.
* Recommend coaches based on player level.
* Integrate with a calendar or booking platform.
* Send booking confirmations and reminders.
* Add authentication and user profiles.
* Support multi-step agent workflows.

---

## 4. Current Project Status

The current version implements a complete RAG application with a web UI, API, persistence, evaluation artifacts, monitoring, and containerized services.

Implemented components include:

* [x] Project problem definition
* [x] Badminton facility knowledge base
* [x] Automated CSV loading and text indexing
* [x] MinSearch text retrieval
* [x] Retrieval-Augmented Generation
* [x] Ground-truth retrieval evaluation with Hit Rate and MRR
* [x] LLM-as-a-Judge evaluation
* [x] Flask API
* [x] Streamlit chat interface
* [x] Conversation-history-aware retrieval queries
* [x] PostgreSQL conversation and feedback storage
* [x] Grafana dashboard with eight monitoring panels
* [x] Docker Compose setup
* [ ] Real booking tools
* [ ] Coach scheduling automation
* [ ] Cancellation and rescheduling workflow
* [ ] Production deployment

---

## 5. System Architecture

The application uses a Retrieval-Augmented Generation architecture.

```text
User
  |
  v
Streamlit UI
  |
  v
Flask API
  |
  v
Conversation-aware RAG pipeline
  |
  +------------------------+
  |                        |
  v                        v
MinSearch text retrieval   OpenAI-compatible LLM
  |
  v
CSV knowledge base
  |
  v
Retrieved context
  |
  v
Generated answer
  |
  +------------------------+
  |                        |
  v                        v
PostgreSQL             API / Streamlit response
  |
  v
Grafana dashboard
```

### Request flow

1. The user submits a question through Streamlit or directly to the Flask API.
2. The frontend sends the current question and up to eight recent messages.
3. The RAG pipeline uses recent user messages to contextualize follow-up retrieval queries.
4. MinSearch retrieves the most relevant records from the badminton knowledge base.
5. The retrieved documents and conversation history are added to the LLM prompt.
6. The LLM generates a grounded answer.
7. The question, answer, relevance judgment, token usage, and response time are stored in PostgreSQL.
8. The user can submit positive or negative feedback.
9. Grafana reads the stored application data for monitoring.

---

## 6. Technology Stack

| Component | Technology |
| --- | --- |
| Programming language | Python 3.13 in Docker |
| Web interface | Streamlit |
| Web API | Flask |
| LLM orchestration | Custom conversation-aware RAG pipeline |
| Language model | OpenAI-compatible LLM |
| Search | MinSearch text retrieval with evaluated field boosts |
| Data processing | Pandas |
| Database | PostgreSQL 16 |
| Monitoring | Grafana |
| Dependency management | uv, `pyproject.toml`, and `uv.lock` |
| Containerization | Docker and Docker Compose |
| Evaluation | Ground truth, Hit Rate, MRR, and LLM-as-a-Judge |

---

## 7. Project Structure

```text
Tonyweng-AI-agent-Project/
├── app.py
├── frontend.py
├── courtmate/
│   ├── config.py
│   ├── db.py
│   ├── hybrid_search.py
│   ├── ingest.py
│   ├── live_context.py
│   ├── operations.py
│   ├── query_router.py
│   ├── rag.py
│   └── rerank.py
├── evaluation/
│   ├── evaluate_retrieval.py
│   ├── evaluate_hybrid.py
│   ├── evaluate_reranking.py
│   └── evaluate_rag.py
├── scripts/
│   ├── db_prep.py
│   ├── seed_operational_data.py
│   └── check_operational_search.py
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   └── test_ingest.py
├── data/
│   ├── knowledge_base.csv
│   ├── ground-truth-retrieval.csv
│   ├── best-minsearch-boost.json
│   ├── best-retrieval-config.json
│   ├── best-reranking-config.json
│   └── evaluation/
│       ├── retrieval-evaluation-results.csv
│       ├── hybrid-retrieval-evaluation-results.csv
│       ├── reranking-evaluation-results.csv
│       ├── rag-evaluation-comparison.csv
│       └── rag-prompt-comparison.csv
├── notebooks/
├── grafana/
│   ├── init.py
│   └── dashboard.json
├── Dockerfile
├── docker-compose.yaml
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
└── README.md
```

---

## 8. Knowledge Base

The knowledge base contains information related to badminton facility operations.

Possible document categories include:

* Facility information
* Opening hours
* Court availability rules
* Court rental prices
* Coach profiles
* Coach specialties
* Coach availability
* Private lesson pricing
* Group lesson schedules
* Drop-in schedules
* Membership plans
* Cancellation policies
* Rescheduling policies
* Equipment rental
* Facility rules
* Frequently asked questions

Each document should contain enough metadata to support accurate retrieval.

Example document:

```json
{
  "id": "coach-001",
  "category": "coach",
  "name": "Coach Alex",
  "level": ["beginner", "intermediate"],
  "availability": ["Monday evening", "Saturday morning"],
  "content": "Coach Alex teaches beginner and intermediate badminton lessons..."
}
```

---

## 9. RAG Pipeline

The application uses Retrieval-Augmented Generation to answer user questions.

### 9.1 Document preparation

Raw facility data is converted into searchable text documents.

Each document may contain:

* A unique document ID
* A category
* A title
* Structured metadata
* Searchable text content

### 9.2 Indexing

Documents are transformed into embeddings and stored in a searchable index.

The index allows the application to find documents that are semantically related to the user’s question.

### 9.3 Retrieval

For each user question, the system retrieves the top matching documents.

Example:

```python
results = search_engine.search(
    query=user_question,
    num_results=5
)
```

### 9.4 Prompt construction

The retrieved documents are inserted into a prompt.

```text
You are a helpful assistant for a badminton facility.

Answer the user question using only the supplied context.

Context:
{retrieved_documents}

Question:
{user_question}
```

### 9.5 Answer generation

The LLM generates a response based on the retrieved information.

The prompt is designed to reduce hallucinations and keep the answer grounded in the knowledge base.

---

## 10. Retrieval Evaluation

Retrieval evaluation measures whether the search system returns the correct document for a given question.

A ground-truth dataset is created with fields such as:

```text
question,document_id
```

Example:

```csv
question,document_id
"What time is beginner drop-in on Friday?",dropin-003
"Which coach teaches beginners?",coach-001
"What is the cancellation policy?",policy-002
```

### Evaluation metrics

The retrieval system may be evaluated using:

* Hit Rate
* Mean Reciprocal Rank
* Precision at K
* Recall at K

### Hit Rate

Hit Rate measures whether the expected document appears anywhere in the retrieved results.

```python
def hit_rate(relevance_total):
    return sum(any(line) for line in relevance_total) / len(relevance_total)
```

### Mean Reciprocal Rank

Mean Reciprocal Rank gives a higher score when the correct document appears near the top of the result list.

```python
def mrr(relevance_total):
    total_score = 0.0

    for line in relevance_total:
        for rank, relevant in enumerate(line):
            if relevant:
                total_score += 1 / (rank + 1)
                break

    return total_score / len(relevance_total)
```

The evaluation results are used to improve:

* Document wording
* Metadata
* Search parameters
* Number of retrieved documents
* Embedding model selection

---

## 11. RAG Evaluation

Retrieval evaluation only checks whether the correct documents were found.

RAG evaluation checks the quality of the generated answer.

The generated answers can be evaluated based on:

* Relevance
* Correctness
* Groundedness
* Completeness
* Hallucination risk

### Example evaluation flow

1. Load a set of evaluation questions.
2. Generate an answer using the RAG pipeline.
3. Compare the answer with the retrieved context or reference answer.
4. Use an LLM judge or evaluation metric to assign a score.
5. Store and summarize the results.

Example evaluation categories:

```text
RELEVANT
PARTLY_RELEVANT
NON_RELEVANT
```

The evaluation results help identify:

* Missing knowledge-base information
* Weak retrieval results
* Poor prompt instructions
* Unsupported generated claims
* Questions the application cannot answer reliably

---

## 12. Flask API

The project exposes the RAG application through a Flask API.

### Main endpoint

```http
POST /question
```

Example request:

```json
{
  "question": "Which coaches are available on Saturday?"
}
```

Example response:

```json
{
  "conversation_id": "example-conversation-id",
  "question": "Which coaches are available on Saturday?",
  "answer": "Based on the current schedule, Coach Alex is available on Saturday morning.",
  "response_time": 1.42
}
```

### Feedback endpoint

```http
POST /feedback
```

Example request:

```json
{
  "conversation_id": "example-conversation-id",
  "feedback": 1
}
```

Feedback values may be:

```text
1  = positive
-1 = negative
```

Example response:

```json
{
  "status": "feedback recorded"
}
```

### Health-check endpoint

A health endpoint may also be included:

```http
GET /health
```

Example response:

```json
{
  "status": "ok"
}
```

---

## 13. PostgreSQL Database

PostgreSQL stores application activity and user feedback.

Typical stored fields include:

* Conversation ID
* User question
* Generated answer
* Model name
* Response time
* Token usage
* Timestamp
* User feedback

Example conversations table:

```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    model_used TEXT,
    response_time FLOAT,
    relevance TEXT,
    relevance_explanation TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Example feedback table:

```sql
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    conversation_id TEXT,
    feedback INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id)
        REFERENCES conversations(id)
);
```

The actual schema should match the implementation in the project.

---

## 14. Grafana Monitoring

Grafana is used to monitor the application through PostgreSQL.

The Grafana PostgreSQL datasource is provisioned from:

```text
grafana/provisioning/datasources/postgres.yaml
```

Example datasource configuration:

```yaml
apiVersion: 1

datasources:
  - name: PostgreSQL
    type: postgres
    access: proxy
    url: postgres:5432
    user: postgres
    secureJsonData:
      password: postgres
    jsonData:
      database: badminton_agent
      sslmode: disable
      postgresVersion: 1500
      timescaledb: false
    isDefault: true
    editable: true
```

The exact database name, username, and password must match the values in `docker-compose.yaml` and `.env`.

### Suggested dashboard metrics

Grafana can display:

* Total number of conversations
* Conversations per hour or day
* Average response time
* Positive feedback count
* Negative feedback count
* Feedback ratio
* Questions with low relevance
* Token usage
* Most common user questions
* Application errors

Example SQL query for total conversations:

```sql
SELECT COUNT(*) AS total_conversations
FROM conversations;
```

Example SQL query for average response time:

```sql
SELECT AVG(response_time) AS average_response_time
FROM conversations;
```

Example feedback query:

```sql
SELECT
    feedback,
    COUNT(*) AS count
FROM feedback
GROUP BY feedback;
```

---

## 15. Environment Variables

Create a `.env` file in the project root.

Example:

```env
OPENAI_API_KEY=your_openai_api_key

POSTGRES_DB=badminton_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

Do not commit the real `.env` file to GitHub.

Create an `.env.example` file using placeholder values:

```env
OPENAI_API_KEY=your_openai_api_key

POSTGRES_DB=badminton_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

---

## 16. Local Installation

Docker Compose is the recommended way to run the complete project. For local Python development, this repository uses [uv](https://docs.astral.sh/uv/) rather than `requirements.txt`.

### 16.1 Clone the repository

```bash
git clone https://github.com/tonyweng0906/Tonyweng-AI-agent-Project.git
cd Tonyweng-AI-agent-Project
```

### 16.2 Install the locked dependencies

Install uv if it is not already available, then run:

```bash
uv sync --locked
```

The dependency declarations are in `pyproject.toml`, and exact resolved versions are stored in `uv.lock`.

### 16.3 Configure environment variables

On macOS or Linux:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Add a valid `OPENAI_API_KEY` to `.env`. Do not commit the real `.env` file.

### 16.4 Optional local development

When PostgreSQL and the Flask backend are already available, start the API with:

```bash
uv run python -m scripts.db_prep
uv run python -m scripts.seed_operational_data
uv run python app.py
```

In another terminal, start the Streamlit frontend:

```bash
uv run streamlit run frontend.py --server.port 8501
```

For the simplest full setup, use Docker Compose as described below.

---

## 17. Running with Docker Compose

The Compose configuration starts all application services:

* `postgres` — PostgreSQL database
* `app` — Flask API and RAG backend
* `frontend` — Streamlit chat interface
* `grafana` — monitoring dashboard service

### 17.1 Configure and start

Create `.env` from `.env.example`, add `OPENAI_API_KEY`, then run:

```bash
docker compose up -d --build
```

Check service status:

```bash
docker compose ps
```

### 17.2 Access the services

| Service | URL |
| --- | --- |
| Streamlit frontend | `http://localhost:8501` |
| Flask API | `http://localhost:5000` |
| Flask health check | `http://localhost:5000/health` |
| Grafana | `http://localhost:3000` |
| PostgreSQL from the host | `localhost:5432` |

### 17.3 View logs

```bash
docker compose logs -f app
```

```bash
docker compose logs -f frontend
```

```bash
docker compose logs -f grafana
```

### 17.4 Stop the project

```bash
docker compose down
```

This preserves the PostgreSQL and Grafana named volumes.

To delete containers and all stored database and Grafana data:

```bash
docker compose down -v
```

Use `-v` only when you intentionally want to erase the stored data.

---

## 18. Docker Compose Configuration

The repository's `docker-compose.yaml` is the source of truth for service configuration.

| Service | Container port | Host port | Purpose |
| --- | ---: | ---: | --- |
| `app` | 5000 | 5000 | Flask API and RAG backend |
| `frontend` | 8501 | 8501 | Streamlit web interface |
| `grafana` | 3000 | 3000 | Monitoring dashboard |
| `postgres` | 5432 | 5432 | Conversation and feedback storage |

Inside Docker Compose, services communicate using service names:

```text
frontend -> http://app:5000
app      -> postgres:5432
grafana  -> postgres:5432
```

The named volumes `courtmate_postgres_data` and `courtmate_grafana_data` preserve data across normal container restarts.

---

## 19. Testing the API

### Using curl

```bash
curl -X POST http://localhost:5000/question \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What are the drop-in times?\"}"
```

On PowerShell:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:5000/question" `
  -ContentType "application/json" `
  -Body '{"question":"What are the drop-in times?"}'
```

### Submit feedback

```bash
curl -X POST http://localhost:5000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "replace-with-conversation-id",
    "feedback": 1
  }'
```

### Health check

```bash
curl http://localhost:5000/health
```

---

## 20. Useful Docker Troubleshooting Commands

### Check running containers

```bash
docker ps
```

A formatted view:

```bash
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}"
```

### Check the resolved Docker Compose configuration

```bash
docker compose config
```

This is useful when Docker still appears to use an old port mapping.

### Rebuild after configuration changes

```bash
docker compose down --remove-orphans
docker compose up -d --build
```

### Check application logs

```bash
docker compose logs app
```

### Check PostgreSQL logs

```bash
docker compose logs postgres
```

### Check Grafana logs

```bash
docker compose logs grafana
```

### Check whether port 5000 is occupied

On Windows:

```powershell
netstat -ano | findstr :5000
```

On macOS or Linux:

```bash
lsof -i :5000
```

Because port `5000` is occupied on the current development machine, the Docker application uses host port `5001`.

---

## 21. Grafana Setup

After Docker Compose starts successfully, initialize the PostgreSQL datasource and import the version-controlled dashboard.

Run the initializer inside the application container:

```bash
docker compose exec -e GRAFANA_URL=http://grafana:3000 app python grafana/init.py
```

Alternatively, run it from the host after `uv sync --locked`:

```bash
uv run python grafana/init.py
```

Open Grafana:

```text
http://localhost:3000
```

Default credentials:

```text
Username: admin
Password: admin
```

The initializer is safe to run again: it creates or updates the PostgreSQL datasource and imports `grafana/dashboard.json`.

The dashboard contains eight panels covering question volume, response relevance, latency, token usage, feedback, satisfaction, and recent conversations.

---

## 22. Common Issues

### Frontend cannot reach the API

Check both services:

```bash
docker compose ps
docker compose logs frontend --tail=100
docker compose logs app --tail=100
```

The frontend container must use:

```text
BADMINTON_MATE_API_URL=http://app:5000
```

### Application cannot connect to PostgreSQL

Inside Docker, the database host must be the Compose service name:

```text
POSTGRES_HOST=postgres
```

Check the database and application logs:

```bash
docker compose logs postgres --tail=100
docker compose logs app --tail=100
```

### Port 5000 is already in use

Change the app mapping in `docker-compose.yaml`:

```yaml
ports:
  - "5001:5000"
```

Then access the API from the host at `http://localhost:5001`. The frontend container still uses `http://app:5000`.

### Grafana has no datasource or dashboard

Run:

```bash
docker compose exec -e GRAFANA_URL=http://grafana:3000 app python grafana/init.py
```

Then inspect the Grafana logs if initialization fails:

```bash
docker compose logs grafana --tail=100
```

### Docker is using an old configuration

```bash
docker compose config
docker compose down --remove-orphans
docker compose up -d --build
```

---

## 23. Example User Interaction

### User

```text
Which coaches are available for beginner lessons on Saturday?
```

### Assistant

```text
Based on the current facility information, Coach Alex offers beginner lessons
on Saturday morning. Availability should be confirmed before completing a
booking.
```

### User

```text
What is the cancellation policy?
```

### Assistant

```text
Lessons must be cancelled within the period specified by the facility policy.
Late cancellations may not qualify for a refund or credit.
```

The assistant should avoid inventing information when the answer is not contained in the knowledge base.

---

## 24. Planned Agent Tools

The current system mainly provides RAG-based question answering.

Future versions can introduce tools that allow the agent to perform actions.

### Search coaches

```python
def search_coaches(
    skill_level: str,
    date: str | None = None,
    time: str | None = None
):
    ...
```

### Search courts

```python
def search_available_courts(
    date: str,
    start_time: str,
    duration_minutes: int
):
    ...
```

### Create booking

```python
def create_booking(
    customer_id: str,
    court_id: str,
    date: str,
    start_time: str,
    duration_minutes: int
):
    ...
```

### Cancel booking

```python
def cancel_booking(
    booking_id: str,
    reason: str | None = None
):
    ...
```

### Reschedule lesson

```python
def reschedule_lesson(
    booking_id: str,
    new_date: str,
    new_start_time: str
):
    ...
```

### Find replacement time

```python
def find_replacement_times(
    coach_id: str,
    original_booking_id: str
):
    ...
```

Before performing actions that affect a real booking, the system should request user confirmation.

---

## 25. Safety and Reliability

The AI assistant should follow several operational rules:

1. Do not claim a booking was created unless the booking system confirms it.
2. Do not claim a cancellation succeeded unless the database confirms it.
3. Do not invent coach or court availability.
4. Do not expose private customer information.
5. Request confirmation before making schedule changes.
6. Log booking-related actions.
7. Return a clear error when required information is missing.
8. Escalate uncertain cases to staff.
9. Use the knowledge base as the source of truth for policies.
10. Distinguish between information requests and real booking actions.

---

## 26. Evaluation Plan

The completed project should be evaluated at several levels.

### Retrieval evaluation

Measures whether the correct knowledge-base document is retrieved.

Metrics:

* Hit Rate
* Mean Reciprocal Rank
* Precision at K
* Recall at K

### Answer evaluation

Measures the quality of generated answers.

Criteria:

* Relevance
* Correctness
* Groundedness
* Completeness
* Clarity

### Operational evaluation

Measures application performance.

Metrics:

* Average response time
* Error rate
* Positive feedback percentage
* Negative feedback percentage
* Number of conversations
* Token usage

### Future booking evaluation

Once action tools are added, evaluate:

* Booking success rate
* Scheduling conflict rate
* Cancellation success rate
* Rescheduling success rate
* Number of cases escalated to staff

---

## 27. Future Improvements

Planned improvements include:

* Replace static availability data with a real scheduling database.
* Add structured tool calling.
* Add multi-step agent workflows.
* Add customer authentication.
* Add coach and staff dashboards.
* Add booking confirmation.
* Add cancellation confirmation.
* Add email or SMS notifications.
* Add Google Calendar integration.
* Add role-based access control.
* Add automated testing.
* Add CI/CD.
* Deploy the application to a cloud platform.
* Add multilingual support.
* Add fallback handling for unsupported questions.
* Add automatic evaluation reports.
* Add more Grafana dashboards and alerts.

---

## 28. Development Roadmap

### Phase 1 — Knowledge assistant

* Prepare facility data
* Build the knowledge base
* Implement semantic search
* Implement the RAG pipeline
* Evaluate retrieval
* Evaluate generated answers

### Phase 2 — Application and monitoring

* Build Flask API
* Store conversations in PostgreSQL
* Store user feedback
* Add Grafana monitoring
* Add Docker Compose

### Phase 3 — Booking agent

* Create structured booking tables
* Implement coach availability search
* Implement court availability search
* Implement booking creation
* Implement cancellation
* Implement rescheduling
* Add confirmation steps

### Phase 4 — Production readiness

* Authentication
* Permissions
* Automated tests
* Error monitoring
* Deployment
* Backups
* Security review
* Real booking-system integration

---

## 29. Current Development URLs

After running Docker Compose:

| Service | URL |
| --- | --- |
| Streamlit frontend | `http://localhost:8501` |
| Flask API | `http://localhost:5000` |
| Grafana | `http://localhost:3000` |
| PostgreSQL | `localhost:5432` |

Docker containers communicate internally using:

```text
frontend -> app:5000
app -> postgres:5432
grafana -> postgres:5432
```

---

## 30. References

This project follows concepts and examples from:

* DataTalksClub LLM Zoomcamp
* LLM Zoomcamp project-example lessons
* The Fitness Assistant demonstration project
* Retrieval-Augmented Generation workflows
* LLM evaluation and monitoring practices

---

## 31. Author

**Tony Weng**

LLM Zoomcamp Project
Badminton Court AI Agent

---

## 32. License

This project is currently intended for educational and portfolio purposes.

A formal open-source license can be added before public distribution.
