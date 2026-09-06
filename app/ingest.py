from pathlib import Path

from pypdf import PdfReader


def extract_pages_from_pdf(file_path: str | Path) -> list[tuple[int, str]]:
    """Extract text with its one-based PDF page number for verifiable citations."""
    reader = PdfReader(str(file_path))
    pages: list[tuple[int, str]] = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((number, text))
    return pages


def extract_text_from_pdf(file_path: str | Path) -> str:
    return "\n".join(text for _, text in extract_pages_from_pdf(file_path)).strip()
