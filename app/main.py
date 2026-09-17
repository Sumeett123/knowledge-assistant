from pathlib import Path
from typing import Annotated
import hashlib
import re
import shutil
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.generator import generate_answer, rewrite_answer
from app.ingest import extract_pages_from_pdf
from app.utils import (answer_request_kind, chunk_text, document_scope, extract_direct_answer,
                       extract_question_bank_answer, is_ambiguous_standalone_question,
                       is_nonsense_input, split_compound_questions)
from app.vector_store import VectorStore

app = FastAPI(title="Knowledge Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
vector_store = VectorStore()
vector_store.load()
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)
    previous_answer: str | None = Field(default=None, max_length=12_000)


@app.post("/query")
def query_docs(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be blank.")
    if is_nonsense_input(question):
        return {
            "question": question,
            "answer": "Please type a real question using words. For example: 'What is machine learning?'",
            "sources": [],
        }
    if req.previous_answer:
        try:
            style = answer_request_kind(question)
            if style:
                answer = rewrite_answer(req.previous_answer, style)
            else:
                answer = generate_answer(
                    f"Follow-up question: {question}\nUse the prior answer below as context. "
                    "If it does not contain enough information, say exactly: I don't know.",
                    [req.previous_answer],
                )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"The answer model is unavailable: {exc}") from exc
        return {
            "question": question,
            "answer": answer or "I don't know",
            "sources": [],
        }
    if not vector_store.text_chunks:
        return {"question": question, "answer": "Upload a PDF before asking a question.", "sources": []}
    if is_ambiguous_standalone_question(question):
        return {
            "question": question,
            "answer": "Please mention the topic or select an earlier answer and use Ask follow-up. For example: ‘Explain the advantages of online banking’.",
            "sources": [],
        }
    try:
        subquestions = split_compound_questions(question)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    scope = document_scope(question, vector_store.filenames())
    scoped_records = [
        record for record in vector_store.records
        if (not scope.include or record.get("filename") in scope.include)
        and record.get("filename") not in scope.exclude
    ]
    if not scoped_records:
        return {"question": question, "answer": "I don't know", "sources": []}
    if scope.topic_search:
        # "Which PDF contains this topic?" — search each document and report matches.
        topic = re.sub(
            r"\bwhich\s+(?:pdf|document|file)s?\s+(?:contains?|has|have|mentions?|talks?\s+about|covers?|discusses?)\s*",
            "", question, flags=re.IGNORECASE,
        ).strip(" ?.,!")
        if not topic:
            return {"question": question, "answer": "Please specify the topic you are looking for.", "sources": []}
        hits: list[str] = []
        for filename in dict.fromkeys(r.get("filename") for r in scoped_records):
            doc_results = vector_store.search(topic, k=3, include_filenames=(filename,))
            if doc_results and doc_results[0].get("similarity", 0) >= 0.25:
                best = doc_results[0]
                page_info = f" (p.\u00a0{best['page']})" if best.get("page") else ""
                hits.append(f"{filename}{page_info}")
        if hits:
            answer = f"The topic '{topic}' appears in: {', '.join(hits)}."
        else:
            answer = f"None of the uploaded documents appear to cover '{topic}'."
        return {"question": question, "answer": answer, "sources": []}
    all_sources: list[dict] = []
    answers: list[dict[str, str]] = []
    for subquestion in subquestions:
        results = vector_store.search(
            subquestion, k=8, include_filenames=scope.include,
            exclude_filenames=scope.exclude, prefer_end=scope.prefer_end,
        )
        if not results or results[0].get("similarity", 0) < 0.18:
            answers.append({"question": subquestion, "answer": "I don't know"})
            continue
        # Question-bank continuity takes precedence: Q and Ans may be on different
        # pages/chunks.  Then try the faster same-chunk exact-answer path.
        answer = extract_question_bank_answer(subquestion, scoped_records)
        if answer is None:
            direct_answers = [extract_direct_answer(subquestion, item["text"]) for item in results]
            answer = next((item for item in direct_answers if item), None)
        try:
            if answer is None:
                answer = generate_answer(subquestion, [item["text"] for item in results])
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"The answer model is unavailable: {exc}") from exc
        answers.append({"question": subquestion, "answer": answer or "I don't know"})
        for source in results:
            if not any(
                existing["text"] == source["text"] and existing.get("filename") == source.get("filename")
                for existing in all_sources
            ):
                all_sources.append(source)

    if len(answers) == 1:
        response_answer = answers[0]["answer"]
    else:
        response_answer = "\n\n".join(
            # `subquestion` is an internal retrieval rewrite.  Showing it here
            # makes it look as though the assistant changed what the user asked.
            # Keep the user's wording intact and label only the answer parts.
            f"Answer {index}:\n\n{item['answer']}"
            for index, item in enumerate(answers, start=1)
        )
    return {"question": question, "answer": response_answer, "answers": answers, "sources": all_sources}


@app.get("/health")
def health():
    return {"status": "ok", "indexed_chunks": len(vector_store.text_chunks)}


def _prepare_upload(upload: UploadFile) -> tuple[dict, list[dict], str, Path]:
    filename = Path(upload.filename or "document.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail=f"{filename} is not a PDF.")
    destination = UPLOAD_DIR / f"{uuid.uuid4().hex}_{filename}"
    try:
        with destination.open("wb") as target:
            shutil.copyfileobj(upload.file, target)
        if destination.stat().st_size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"{filename} is larger than the 50 MB upload limit.")
        with destination.open("rb") as saved_file:
            document_hash = hashlib.file_digest(saved_file, "sha256").hexdigest()
        pages = extract_pages_from_pdf(destination)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not read {filename}: {exc}") from exc
    finally:
        upload.file.close()
    chunks = [
        {"text": chunk, "filename": filename, "page": page_number, "document_hash": document_hash}
        for page_number, page_text in pages
        for chunk in chunk_text(page_text)
    ]
    if not chunks:
        raise HTTPException(
            status_code=422,
            detail=f"{filename} has no extractable text. It may be a scanned PDF and needs OCR.",
        )
    preview = " ".join(page_text for _, page_text in pages)[:300]
    return {"filename": filename, "num_chunks": len(chunks), "text_preview": preview}, chunks, document_hash, destination


@app.post("/upload")
def upload_files(
    file: Annotated[UploadFile | None, File()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
):
    """Accept the old single `file` field and the new multi-file `files` field."""
    uploads = ([file] if file else []) + (files or [])
    if not uploads:
        raise HTTPException(status_code=422, detail="Select at least one PDF.")
    prepared: list[tuple[dict, list[dict], str, Path]] = []
    try:
        for upload in uploads:
            prepared.append(_prepare_upload(upload))
    except Exception:
        # A multi-file upload is atomic: do not leave earlier temporary PDFs behind
        # when a later file is invalid, corrupt, or scanned without OCR text.
        for _, _, _, destination in prepared:
            destination.unlink(missing_ok=True)
        raise
    existing_hashes = {record.get("document_hash") for record in vector_store.records}
    incoming_hashes = [document_hash for _, _, document_hash, _ in prepared]
    if len(set(incoming_hashes)) != len(incoming_hashes) or any(document_hash in existing_hashes for document_hash in incoming_hashes):
        for _, _, _, destination in prepared:
            destination.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="This PDF has already been indexed. Upload a different document to avoid duplicate answers.")
    processed = [item for item, _, _, _ in prepared]
    # Add only after every selected PDF has been successfully validated.
    vector_store.add_texts([chunk for _, chunks, _, _ in prepared for chunk in chunks])
    vector_store.save()
    return {
        "message": "Files uploaded and indexed successfully",
        "files": processed,
        **processed[0],  # compatibility with the existing separate frontend
        "total_chunks": sum(item["num_chunks"] for item in processed),
    }
