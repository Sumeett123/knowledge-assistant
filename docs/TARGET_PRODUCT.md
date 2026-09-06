# EvidenceLens: target product specification

## Product statement

EvidenceLens is a local-first academic PDF assistant that answers only when the
selected documents contain auditable support. Every factual answer is traceable
to document pages and chunks; when evidence is insufficient, the system abstains
instead of completing a plausible answer.

## User flow

```text
Create/select collection -> upload PDFs -> extract pages and chunk text
-> dense + lexical retrieval -> reciprocal-rank fusion -> optional reranking
-> grounded answer draft -> claim-to-evidence verification
-> cited answer and confidence explanation, or abstention
```

## Product behavior

- A collection isolates a user's documents and indexes.
- Upload shows document state: queued, extracting, indexing, ready, needs OCR,
  or failed.
- Queries return `ANSWERED` only when each displayed factual claim has supporting
  evidence. Otherwise they return `ABSTAINED` with a useful explanation.
- Inline citations open evidence cards that show the file name, page, chunk
  excerpt, and support status.
- Confidence is derived from calibrated retrieval/evidence signals, never from a
  raw vector distance displayed as a percentage.
- A reproducible evaluation workspace runs baseline and ablation variants on a
  fixed benchmark.

## Technical architecture

```text
React workspace
     |
FastAPI API and orchestration layer
     |
Ingestion -> page/chunk metadata -> FAISS dense index + BM25 sparse index
     |
Dense retrieval + BM25 retrieval -> RRF -> optional cross-encoder reranker
     |
Local generator -> claim segmentation -> evidence verifier -> confidence policy
     |
Auditable answer, citations, query trace, evaluation artifacts
```

## Initial technical choices

- Existing `all-MiniLM-L6-v2` embeddings and FAISS remain the dense baseline.
- BM25 plus deterministic Reciprocal Rank Fusion (RRF) provides lexical and
  semantic retrieval without a hosted service.
- An optional `cross-encoder/ms-marco-MiniLM-L-6-v2` reranker improves final
  evidence ordering when local hardware permits it.
- SQLite becomes the local source of truth for collections, documents, chunks,
  query traces, claims, and evaluations. FAISS/BM25 are rebuildable artifacts.
- FLAN-T5 remains the initial local generator behind an interface, so it can be
  replaced without changing retrieval or verification.

## Non-goals for the paper release

Multi-user authentication, cloud vector databases, foundation-model fine-tuning,
and real-time collaboration are out of scope. They do not strengthen the central
research claim and would delay evaluation.

## Release acceptance criteria

1. Collections do not leak documents into each other's retrieval results.
2. Every displayed factual claim has at least one page-level supporting citation,
   or the response abstains.
3. A benchmark runner can reproduce all reported baseline/ablation results from
   versioned inputs and configuration.
4. The interface lets a user inspect why an answer is supported or refused.
