"""Persistent, metadata-aware vector retrieval for the knowledge base."""

from __future__ import annotations

import json
import os
from typing import Any

import faiss
from sentence_transformers import SentenceTransformer

INDEX_PATH = "data/index/faiss.index"
TEXT_PATH = "data/index/text_chunks.json"
os.makedirs("data/index", exist_ok=True)


class VectorStore:
    """FAISS store that preserves the document and page behind every chunk."""

    def __init__(self, dim: int = 384):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = faiss.IndexFlatIP(dim)
        self.records: list[dict[str, Any]] = []

    @property
    def text_chunks(self) -> list[str]:
        return [record["text"] for record in self.records]

    def add_texts(self, chunks: list[dict[str, Any] | str]) -> None:
        records = [chunk if isinstance(chunk, dict) else {"text": chunk, "filename": "Unknown document", "page": None} for chunk in chunks]
        records = [record for record in records if record.get("text", "").strip()]
        if not records:
            return
        embeddings = self.model.encode([record["text"] for record in records], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        self.index.add(embeddings)
        self.records.extend(records)

    def filenames(self) -> list[str]:
        """Return unique document names in their ingestion order."""
        return list(dict.fromkeys(record.get("filename", "Unknown document") for record in self.records))

    def search(
        self, query: str, k: int = 8, candidate_k: int = 32,
        include_filenames: tuple[str, ...] = (), exclude_filenames: tuple[str, ...] = (),
        prefer_end: bool = False,
    ) -> list[dict[str, Any]]:
        """Retrieve evidence, optionally constrained to explicitly named documents."""
        if not self.records:
            return []
        query_embedding = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        # A named PDF must be searched across the entire corpus; otherwise its best
        # chunk can be outside the global top-32 due to a repetitive other document.
        search_size = len(self.records) if include_filenames else min(max(candidate_k, k), len(self.records))
        similarities, indices = self.index.search(query_embedding, search_size)
        candidates = []
        for similarity, index in zip(similarities[0], indices[0]):
            if 0 <= index < len(self.records):
                candidate = dict(self.records[index])
                candidate["similarity"] = float(similarity)
                candidate["distance"] = float(1 - similarity)  # compatibility with existing frontends
                filename = candidate.get("filename") or "Unknown document"
                if include_filenames and filename not in include_filenames:
                    continue
                if filename in exclude_filenames:
                    continue
                candidates.append(candidate)
        if prefer_end and candidates:
            # Preserve semantic ranking, while ensuring the trailing chunks of the
            # requested document are available for "end/last page" questions.
            allowed = {item.get("filename") for item in candidates}
            tail = [dict(record) for record in self.records if record.get("filename") in allowed][-max(k * 2, 8):]
            for item in tail:
                item["similarity"] = float(item.get("similarity", -1.0))
                item["distance"] = float(1 - item["similarity"])
            known = {(item.get("filename"), item["text"]) for item in candidates}
            candidates.extend(item for item in tail if (item.get("filename"), item["text"]) not in known)
            tail_keys = {(item.get("filename"), item["text"]) for item in tail}
            candidates.sort(key=lambda item: (0 if (item.get("filename"), item["text"]) in tail_keys else 1, -item["similarity"]))
        return candidates[:k]

    def save(self) -> None:
        faiss.write_index(self.index, INDEX_PATH)
        with open(TEXT_PATH, "w", encoding="utf-8") as file:
            json.dump({"version": 2, "records": self.records}, file, ensure_ascii=False)

    def load(self) -> None:
        if not (os.path.exists(INDEX_PATH) and os.path.exists(TEXT_PATH)):
            return
        with open(TEXT_PATH, "r", encoding="utf-8") as file:
            stored = json.load(file)
        if isinstance(stored, list):
            self.records = [{"text": text, "filename": "Previously uploaded documents", "page": None} for text in stored]
            old_records = self.records
            self.records = []
            self.add_texts(old_records)
            self.save()
        else:
            self.records = stored.get("records", [])
            self.index = faiss.read_index(INDEX_PATH)
