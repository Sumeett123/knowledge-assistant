# Knowledge Assistant (RAG-based)

## Overview

This project is an **end-to-end Knowledge Assistant** built using **Retrieval-Augmented Generation (RAG)**. It allows users to upload documents (PDFs), ask natural-language questions, and receive **grounded answers backed by source chunks**. The system is designed to minimize hallucinations by combining semantic retrieval with confidence-based abstention.

This is a **systems-focused AI project**, emphasizing correctness, robustness, and real-world design choices rather than toy demos.

---

## Key Features

* 📄 **Single or multi-PDF ingestion** with text extraction
* ✂️ **Sentence-aware chunking** with overlap for context preservation
* 🔍 **Metadata-aware semantic search** using SentenceTransformers + FAISS cosine similarity
* 📄 **Cross-document retrieval** that considers the best matching evidence from every uploaded PDF
* 🧠 **Local LLM generation** using FLAN-T5 (GPU/CPU fallback)
* 📚 **Source-grounded answers** with document-name, page, and similarity citations
* 💾 **Persistent vector store** (survives server restarts)
* ⚡ **FastAPI backend** with structured request validation

---

## Architecture

```
User Query
   ↓
FastAPI (/query)
   ↓
VectorStore.search() — broad retrieval + per-document evidence coverage
   ↓
Top-k chunks + distances
   ↓ (threshold check)
LocalGenerator (FLAN-T5)
   ↓
Final Answer + Sources
```

---

## Tech Stack

* **Backend**: FastAPI
* **Embeddings**: SentenceTransformers (`all-MiniLM-L6-v2`)
* **Vector Database**: FAISS (L2 similarity)
* **LLM**: FLAN-T5 Large (local inference)
* **NLP Utilities**: NLTK
* **Persistence**: FAISS index + JSON metadata

---

## Design Decisions

### Why FAISS?

* Lightweight and fast for local vector search
* No external service dependency
* Industry-standard for similarity search

### Evaluation & Hallucination Control
The system uses normalized cosine similarity for ranking, but does not pretend a
single global distance cutoff is a reliable confidence score. It retrieves a broad
candidate set, preserves the strongest evidence from each uploaded PDF, and tells
the generator to abstain when supplied evidence does not answer the question.
Every returned chunk retains its document name and one-based PDF page number so a
reader can audit the answer.


### Why sentence-based chunking?

* Preserves semantic meaning better than fixed-length splits
* Reduces context fragmentation

### Why cross-document retrieval?

* A long or repetitive document cannot monopolize the result list
* The answer can use evidence from another uploaded PDF when the first PDF is irrelevant
* Page-level provenance makes results suitable for evaluation and research reporting

### Why local LLM?

* No API costs
* Full control over inference
* Demonstrates system-level understanding

---

## API Example

### Query Endpoint

```http
POST /query
Content-Type: application/json

{
  "question": "What is FAISS?"
}
```

### Response

```json
{
  "question": "What is FAISS?",
  "answer": "FAISS is a library for efficient similarity search...",
  "sources": [
    {
      "text": "FAISS is a library developed by Meta...",
      "distance": 0.23
    }
  ]
}
```

---

## Persistence

The vector store is persisted to disk:

* `data/index/faiss.index`
* `data/index/text_chunks.json`

This ensures:

* Knowledge survives server restarts
* PDFs do not need to be re-uploaded

---

## Limitations

* Uses character-based distance instead of token-level scoring
* No re-ranking step
* Single-user, local setup
* No frontend UI (yet)

---

## Future Work

* Add minimal frontend (Streamlit / HTML)
* Implement reranking for retrieved chunks
* Add evaluation metrics for retrieval quality
* Dockerize for deployment

---

## How to Run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# In another terminal:
streamlit run streamlit_app.py
```

Select one or more PDFs in Streamlit, then click **Process selected PDFs**.
The first model startup may take longer because FLAN-T5 is loaded locally.

---


### Deployment Notes
The system is designed for local inference due to the size of the LLM.
In production, the generator can be swapped with an API-based model
(OpenAI, Azure, etc.) while keeping retrieval unchanged.


## Author

Built as a flagship applied AI/ML project focusing on **real-world RAG system design**.
