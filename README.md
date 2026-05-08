# GDPR RAG System

A Retrieval-Augmented Generation system for GDPR compliance analysis. Upload GDPR-related documents, search the knowledge base semantically, and get AI-powered answers with verifiable source references.

## Quick Start

```bash
# 1. Set your OpenAI API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the API
uvicorn main:app
```

The API will be available at `http://localhost:8000`.

The system uses in-memory Qdrant (no external database needed). Seed data loads automatically on startup.

## Web UI

Visit `http://localhost:8000` for the interactive chat interface featuring:
- Dark purple sci-fi themed design
- Multi-turn conversation with context memory
- `/risk` command for visual risk assessment dashboard
- Clickable dimension scores with expandable explanations
- Source citations for every answer

## API Endpoints

### POST /text — Upload plain text

```bash
curl -X POST http://localhost:8000/text \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Article 5 of GDPR requires that personal data shall be processed lawfully, fairly and in a transparent manner.",
    "source": "gdpr_article_5",
    "metadata": {"topic": "gdpr", "type": "principles", "article": "Art.5"}
  }'
```

### POST /document — Upload PDF/TXT file

```bash
curl -X POST http://localhost:8000/document \
  -F "file=@gdpr_full_text.pdf" \
  -F 'metadata={"topic": "gdpr", "type": "regulation"}'
```

### GET /search — Semantic search with optional filtering

```bash
# Basic search
curl "http://localhost:8000/search?q=data+minimization&top_k=3"

# With metadata filter
curl "http://localhost:8000/search?q=consent&topic=gdpr&type=rights"
```

### POST /chat — Ask questions with source references

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the lawful bases for processing personal data under GDPR?",
    "metadata_filter": {"topic": "gdpr"},
    "history": [{"role": "user", "content": "previous question"}, {"role": "assistant", "content": "previous answer"}],
    "language": "Chinese"
  }'
```

Supports:
- **Multi-turn conversation**: Pass `history` array for contextual follow-up questions
- **Language preference**: Set `language` to get responses in your preferred language

### POST /risk — GDPR risk analysis with multi-dimensional scoring

```bash
curl -X POST http://localhost:8000/risk \
  -H "Content-Type: application/json" \
  -d '{
    "project_description": "We are building an AI chatbot that collects user email, browsing history, and location data to provide personalized recommendations. We store data indefinitely and share it with third-party advertisers."
  }'
```

Or use the Web UI:
```
/risk We are building an AI chatbot that collects user email, browsing history, and location data to provide personalized recommendations. We store data indefinitely and share it with third-party advertisers.
```

![Risk Assessment Demo](sample.png)

Returns structured JSON with:
- **Overall risk score** (1-10)
- **8 dimension scores** with explanations:
  - ⚖️ Lawful Basis
  - 📉 Data Minimization
  - ✅ Consent & Transparency
  - 👤 Data Subject Rights
  - 🌍 International Transfers
  - 🔒 Security & Breach
  - 🏥 Special Categories
  - 🤖 Automated Decisions
- **Individual risk findings** with level (High/Medium/Low), description, relevant article, and recommendation
- **Top 3 priorities** for compliance

## Knowledge Base (Seed Data)

The system comes pre-loaded with 23 GDPR articles and guidance documents:

| File | Coverage |
|------|----------|
| art4_definitions.txt | Key GDPR definitions, anonymisation vs pseudonymisation |
| art5_principles.txt | Core data processing principles |
| art6_lawful_basis.txt | Six lawful bases for processing |
| art7_consent.txt | Conditions for valid consent |
| art9_special_categories.txt | Health, biometric, genetic data protections |
| art12_transparency.txt | Transparent communication requirements |
| art13_information.txt | Information to provide at data collection |
| art15_right_of_access.txt | Data subject access rights |
| art16_18_21_rights.txt | Rectification, restriction, and objection rights |
| art17_right_to_erasure.txt | Right to be forgotten |
| art20_data_portability.txt | Data export and portability rights |
| art22_automated_decisions.txt | Profiling and automated decision-making |
| art25_data_protection_by_design.txt | Privacy by design and default |
| art28_processor.txt | Data processor obligations and contracts |
| art30_records.txt | Records of processing activities |
| art32_security.txt | Security of processing |
| art33_data_breach_notification.txt | 72-hour breach notification to authorities |
| art34_breach_communication.txt | Breach communication to data subjects |
| art35_dpia.txt | Data Protection Impact Assessment |
| art37_39_dpo.txt | Data Protection Officer requirements |
| art44_49_international_transfers.txt | Cross-border data transfer rules |
| art83_fines.txt | Penalties up to €20M/4% turnover + real cases |
| gdpr_ai_guidance.txt | GDPR implications for AI/ML systems |

## Architecture & Design Choices

### Why Qdrant (in-memory mode)?
- Purpose-built vector database with native filtering support
- In-memory mode requires zero external dependencies — no Docker needed
- Payload-based metadata enables flexible filtering without schema migrations
- Automatic seed loading on startup ensures knowledge base is always ready

### Why `text-embedding-3-small`?
- 1536 dimensions — good balance of quality vs. cost
- Outperforms `ada-002` at lower price
- Sufficient for document-level semantic similarity in a domain-specific corpus

### Why semantic chunking?
- Splits text at paragraph and sentence boundaries instead of fixed character counts
- Preserves complete thoughts and legal clauses in each chunk
- Merges small paragraphs to avoid under-sized chunks
- Results in more precise retrieval with less noise

### Why `gpt-4o-mini`?
- Cost-effective for a compliance Q&A system
- Strong instruction-following for citation format and JSON output
- Fast response times suitable for interactive chat

### Data Model

```
Document (logical, tracked in Qdrant payload):
├── document_id (UUID)
├── source (filename or label)
├── metadata (topic, type, article, etc.)
└── created_at

Chunk (stored as Qdrant point):
├── id (UUID)
├── vector (1536-dim embedding)
├── text (chunk content)
├── document_id (reference to parent)
├── chunk_index (position in document)
├── source
└── meta_* (flattened metadata for filtering)
```

## What's Implemented vs. Not

### ✅ Implemented
- Full RAG pipeline (ingest → chunk → embed → store → retrieve → generate)
- **Semantic chunking** — paragraph/sentence-aware splitting
- **Multi-turn conversation** — context memory across messages
- **Multi-dimensional risk scoring** — 8 dimensions with 1-10 scores
- **Interactive risk dashboard** — clickable dimensions with expandable explanations
- **Language preference** — respond in user's preferred language
- **Deduplication** — search results filtered for unique content
- Metadata support on upload and filtering on search
- Source references in LLM output (verifiable chunk + document)
- Persistent knowledge base with 23 GDPR articles + AI guidance
- Web chat UI with dark sci-fi theme
- PDF and plain text ingestion

### ❌ Not Implemented (and why)
- **Graph representation**: Would add Neo4j dependency and entity extraction complexity; not justified for a focused Q&A system within the time constraint
- **Hybrid search (BM25 + vector)**: Qdrant supports keyword filtering but not full BM25; would require adding Elasticsearch, increasing infra complexity
- **Re-ranking**: Would improve precision but adds latency and another model dependency (e.g., Cohere reranker)
- **Streaming responses**: FastAPI supports SSE but adds client-side complexity; not critical for a backend API
- **Auth**: Trivial to add (API key header middleware) but omitted to keep the focus on RAG quality
- **Persistent storage**: Using in-memory Qdrant for simplicity; production would use file-based or server mode

## AI Collaboration

This project was built with AI assistance (Amazon Q Developer):
- AI generated the initial structure and core logic
- I reviewed and identified gaps against requirements (metadata, data model, filtering, docker-compose, README)
- AI then filled those gaps based on my direction
- The architecture decisions (Qdrant, chunk size, embedding model) were discussed and confirmed before implementation
- AI assisted with expanding seed data, adding multi-dimensional risk scoring, and building the interactive UI
