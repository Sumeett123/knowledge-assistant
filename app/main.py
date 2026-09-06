from pathlib import Path
from typing import Annotated
import shutil
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.generator import generate_answer
from app.ingest import extract_pages_from_pdf
from app.utils import chunk_text, document_scope, extract_direct_answer, extract_question_bank_answer, split_compound_questions
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


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)


@app.post("/query")
def query_docs(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be blank.")
    if not vector_store.text_chunks:
        return {"question": question, "answer": "Upload a PDF before asking a question.", "sources": []}
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
    all_sources: list[dict] = []
    answers: list[dict[str, str]] = []
    for subquestion in subquestions:
        results = vector_store.search(
            subquestion, k=8, include_filenames=scope.include,
            exclude_filenames=scope.exclude, prefer_end=scope.prefer_end,
        )
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
            source["question"] = subquestion
            if not any(
                existing["text"] == source["text"] and existing.get("filename") == source.get("filename")
                for existing in all_sources
            ):
                all_sources.append(source)

    if len(answers) == 1:
        response_answer = answers[0]["answer"]
    else:
        response_answer = "\n\n".join(
            f"Question {index}: {item['question']}\n\n{item['answer']}"
            for index, item in enumerate(answers, start=1)
        )
    return {"question": question, "answer": response_answer, "answers": answers, "sources": all_sources}


@app.get("/health")
def health():
    return {"status": "ok", "indexed_chunks": len(vector_store.text_chunks)}


def _prepare_upload(upload: UploadFile) -> tuple[dict, list[str]]:
    filename = Path(upload.filename or "document.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail=f"{filename} is not a PDF.")
    destination = UPLOAD_DIR / f"{uuid.uuid4().hex}_{filename}"
    try:
        with destination.open("wb") as target:
            shutil.copyfileobj(upload.file, target)
        pages = extract_pages_from_pdf(destination)
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not read {filename}: {exc}") from exc
    finally:
        upload.file.close()
    chunks = [
        {"text": chunk, "filename": filename, "page": page_number}
        for page_number, page_text in pages
        for chunk in chunk_text(page_text)
    ]
    if not chunks:
        raise HTTPException(
            status_code=422,
            detail=f"{filename} has no extractable text. It may be a scanned PDF and needs OCR.",
        )
    preview = " ".join(page_text for _, page_text in pages)[:300]
    return {"filename": filename, "num_chunks": len(chunks), "text_preview": preview}, chunks


@app.post("/upload")
def upload_files(
    file: Annotated[UploadFile | None, File()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
):
    """Accept the old single `file` field and the new multi-file `files` field."""
    uploads = ([file] if file else []) + (files or [])
    if not uploads:
        raise HTTPException(status_code=422, detail="Select at least one PDF.")
    prepared = [_prepare_upload(upload) for upload in uploads]
    processed = [item for item, _ in prepared]
    # Add only after every selected PDF has been successfully validated.
    vector_store.add_texts([chunk for _, chunks in prepared for chunk in chunks])
    vector_store.save()
    return {
        "message": "Files uploaded and indexed successfully",
        "files": processed,
        **processed[0],  # compatibility with the existing separate frontend
        "total_chunks": sum(item["num_chunks"] for item in processed),
    }
