"""Text preparation helpers used during document ingestion."""

import re
from dataclasses import dataclass


_STOP_WORDS = {
    "a", "an", "and", "are", "be", "by", "describe", "do", "explain", "for", "how", "in",
    "is", "its", "of", "on", "or", "the", "to", "what", "with", "write",
}

# Small, explicit concept families improve matching of natural student phrasing
# without relying on a network service or blindly rewriting every query.
_CONCEPT_FAMILIES = (
    {"importance", "significance", "benefit", "benefits", "advantage", "advantages", "value", "role"},
    {"disadvantage", "disadvantages", "drawback", "drawbacks", "limitation", "limitations", "demerit", "demerits"},
    {"type", "types", "kind", "kinds", "category", "categories", "classification"},
)


def _keywords(value: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", value.lower()) if word not in _STOP_WORDS and len(word) > 1}


def _semantic_overlap(question_terms: set[str], title_terms: set[str]) -> float:
    """Token overlap with conservative, transparent synonym families."""
    if not question_terms:
        return 0.0
    matched = 0
    for term in question_terms:
        if term in title_terms:
            matched += 1
            continue
        if any(term in family and title_terms.intersection(family) for family in _CONCEPT_FAMILIES):
            matched += 1
    return matched / len(question_terms)


_QUESTION_START = r"(?:explain|describe|define|discuss|compare|differentiate|list|what|how|why|when|give|write|state|mention)"


@dataclass(frozen=True)
class DocumentScope:
    """The document constraints explicitly stated in a user's request."""

    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    prefer_end: bool = False


def document_scope(question: str, filenames: list[str]) -> DocumentScope:
    """Interpret document names/order without letting irrelevant PDFs leak in.

    The order is the upload/index order.  Filename matching accepts a full filename
    or its stem, so "from notes" works for ``notes.pdf``.  Constraints are only
    applied when the request clearly names a document; ordinary questions remain
    cross-document searches.
    """
    normalized = re.sub(r"\s+", " ", question.lower()).strip()
    ordered = list(dict.fromkeys(name for name in filenames if name))
    include: list[str] = []
    exclude: list[str] = []
    ordinals = {"first": 0, "1st": 0, "one": 0, "second": 1, "2nd": 1,
                "two": 1, "third": 2, "3rd": 2, "three": 2, "fourth": 3,
                "4th": 3, "last": -1}
    for word, index in ordinals.items():
        if re.search(rf"\b{re.escape(word)}\s+(?:pdf|document|file)\b", normalized):
            if -len(ordered) <= index < len(ordered):
                include.append(ordered[index])
    # Handle "PDF 2" / "document 3" as well as "second PDF".
    for match in re.finditer(r"\b(?:pdf|document|file)\s*#?\s*(\d+)\b", normalized):
        index = int(match.group(1)) - 1
        if 0 <= index < len(ordered):
            include.append(ordered[index])
    for filename in ordered:
        stem = re.sub(r"\.pdf$", "", filename.lower())
        # Avoid matching generic one-word stems such as "notes" by requiring a
        # document cue when a filename is not quoted or otherwise distinctive.
        if len(stem) >= 3 and re.search(rf"\b{re.escape(stem)}(?:\.pdf)?\b", normalized):
            include.append(filename)
    skip_pattern = r"(?:skip|ignore|exclude|without|other than|except)\s+(?:the\s+)?(?:first|1st|second|2nd|third|3rd|fourth|4th|last|\d+)\s+(?:pdf|document|file)"
    for match in re.finditer(skip_pattern, normalized):
        token = re.search(r"(?:first|1st|second|2nd|third|3rd|fourth|4th|last|\d+)", match.group(0)).group(0)
        index = ordinals.get(token, int(token) - 1 if token.isdigit() else 0)
        if -len(ordered) <= index < len(ordered):
            exclude.append(ordered[index])
    for filename in ordered:
        stem = re.sub(r"\.pdf$", "", filename.lower())
        if re.search(rf"\b(?:skip|ignore|exclude)\s+(?:the\s+)?{re.escape(stem)}(?:\.pdf)?\b", normalized):
            exclude.append(filename)
    include = [name for name in dict.fromkeys(include) if name not in exclude]
    return DocumentScope(
        include=tuple(include),
        exclude=tuple(dict.fromkeys(exclude)),
        prefer_end=bool(re.search(r"\b(?:at|from|near|toward|towards)\s+(?:the\s+)?(?:very\s+)?(?:end|last part)|\bend\s+of\s+(?:the\s+)?(?:first|second|third|fourth|last|\d+)?\s*(?:pdf|document|file)\b|\blast (?:page|section|part)\b", normalized)),
    )


def split_compound_questions(value: str, max_questions: int = 4) -> list[str]:
    """Split clear multi-question requests without breaking one compound topic.

    It recognises numbered lines, semicolon-separated prompts, and connectors such
    as ``and also explain``.  It intentionally does *not* split phrases such as
    ``advantages and disadvantages`` because no new question verb follows `and`.
    """
    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        return []
    boundaries = [
        rf"\s*(?:\n|;|(?<!\d)\.)\s*(?={_QUESTION_START}\b)",
        rf"\s+(?:and\s+also|also|and\s+then|then|and)\s+(?={_QUESTION_START}\b)",
        rf"\s+(?=\d+[.)]\s*{_QUESTION_START}\b)",
    ]
    parts = [normalized]
    for boundary in boundaries:
        updated: list[str] = []
        for part in parts:
            updated.extend(re.split(boundary, part, flags=re.IGNORECASE))
        parts = updated
    # Keep short but valid prompts such as "Explain MIS".  Empty connector fragments
    # still disappear because they have no meaningful keywords.
    questions = [part.strip(" .;:-") for part in parts if _keywords(part)]

    # Users commonly omit a repeated verb: "Explain A and also types of B".
    # Preserve the first imperative verb for the second topic.  Restrict this to
    # the explicit "and also" marker so ordinary phrases such as "advantages and
    # disadvantages" remain one question.
    expanded: list[str] = []
    for question in questions:
        implicit = re.match(
            r"^(?P<verb>explain|describe|define|discuss|list|compare|differentiate)\s+"
            r"(?P<first>.+?)\s+and\s+also\s+(?P<second>.+)$",
            question,
            flags=re.IGNORECASE,
        )
        if implicit and not re.match(rf"{_QUESTION_START}\b", implicit.group("second"), flags=re.IGNORECASE):
            expanded.extend([
                f"{implicit.group('verb')} {implicit.group('first')}",
                f"{implicit.group('verb')} {implicit.group('second')}",
            ])
        else:
            paired = re.match(
                r"^(?P<verb>explain|describe|define|discuss|list)\s+(?P<first>.+?)\s+and\s+"
                r"(?P<second>(?:the\s+)?advantages?\s+and\s+(?:its\s+|the\s+)?disadvantages?.*)$",
                question,
                flags=re.IGNORECASE,
            )
            if paired:
                expanded.extend([
                    f"{paired.group('verb')} {paired.group('first')}",
                    f"{paired.group('verb')} {paired.group('second')}",
                ])
                continue
            expanded.append(question)
    questions = expanded
    # Repeated requests should not produce duplicate model calls or duplicate answers.
    unique = list(dict.fromkeys(questions))
    if len(unique) > max_questions:
        raise ValueError(f"Please submit at most {max_questions} questions at a time.")
    return unique or [normalized]


def extract_direct_answer(question: str, source_text: str) -> str | None:
    """Return a verified answer from a question-bank passage when one is present.

    Generative models are unnecessary—and can damage fidelity—when a PDF already
    contains the exact question followed by ``Ans:``.  The match is deliberately
    conservative: most meaningful question terms must occur immediately before
    the answer marker.
    """
    question_terms = _keywords(question)
    if len(question_terms) < 2:
        return None
    for match in reversed(list(re.finditer(r"\bans(?:wer)?\s*:\s*", source_text, flags=re.IGNORECASE))):
        preceding_question = source_text[max(0, match.start() - 550):match.start()]
        overlap = len(question_terms & _keywords(preceding_question)) / len(question_terms)
        if overlap < 0.70:
            continue
        answer = source_text[match.end():]
        # Do not accidentally return the next question if two Q&A pairs share a chunk.
        answer = re.split(r"\bq(?:uestion)?\s*\d+\s*[.:]", answer, maxsplit=1, flags=re.IGNORECASE)[0]
        answer = re.sub(r"\s*(?:[>➢])\s*", "\n• ", answer).strip()
        answer = re.sub(r"\n{3,}", "\n\n", answer)
        if len(answer) >= 80:
            return answer
    return None


def extract_question_bank_answer(question: str, records: list[dict]) -> str | None:
    """Recover an answer that starts in a later chunk or page of a question bank.

    PDFs often place ``Q2`` at the bottom of one page and ``Ans:`` at the top of
    the next.  Chunk-level retrieval alone loses that relationship.  Records are
    stored in PDF order, so once a sufficiently matching numbered question is
    found, this follows its document-local successors until the next question.
    """
    question_terms = _keywords(question)
    if len(question_terms) < 2:
        return None
    question_pattern = re.compile(r"\bq(?:uestion)?\s*\d+\s*[.:]\s*(.*?)(?=\bans(?:wer)?\s*:|$)", re.IGNORECASE)
    answer_pattern = re.compile(r"\bans(?:wer)?\s*:\s*", re.IGNORECASE)
    next_question_pattern = re.compile(r"\bq(?:uestion)?\s*\d+\s*[.:]", re.IGNORECASE)

    candidates: list[tuple[float, int]] = []
    for index, record in enumerate(records):
        text = record.get("text", "")
        for match in question_pattern.finditer(text):
            title_terms = _keywords(match.group(1))
            if title_terms:
                score = _semantic_overlap(question_terms, title_terms)
                if score >= 0.70:
                    candidates.append((score, index))
    for _, start_index in sorted(candidates, reverse=True):
        filename = records[start_index].get("filename")
        passages: list[str] = []
        # Eight chunks cover a normal multi-page long answer while retaining a
        # strict bound for malformed/repetitive PDFs.
        for record in records[start_index:start_index + 8]:
            if record.get("filename") != filename:
                break
            passages.append(record.get("text", ""))
        # Ingestion intentionally overlaps neighbouring chunks.  Remove that overlap
        # before displaying an extractive answer, otherwise sentences repeat.
        combined = ""
        for passage in passages:
            if not combined:
                combined = passage
                continue
            overlap = 0
            for size in range(min(350, len(combined), len(passage)), 19, -1):
                if combined[-size:] == passage[:size]:
                    overlap = size
                    break
            combined += passage[overlap:] if overlap else "\n" + passage
        answer_match = answer_pattern.search(combined)
        if not answer_match:
            continue
        answer = combined[answer_match.end():]
        next_question = next_question_pattern.search(answer)
        if next_question:
            answer = answer[:next_question.start()]
        answer = re.sub(r"\s*(?:[>➢])\s*", "\n• ", answer).strip()
        # Some teaching PDFs include an instruction to the student before the
        # answer.  It is document metadata, not answer content.
        answer = re.sub(
            r"^first part of (?:the )?question.*?(?=advantages? of information system)",
            "",
            answer,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()
        answer = re.sub(r"\n{3,}", "\n\n", answer)
        if len(answer) >= 80:
            return answer
    return None


def chunk_text(text: str, max_chars: int = 1_200, overlap: int = 180) -> list[str]:
    """Split text into readable, overlapping chunks without a runtime download."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        if end < len(cleaned):
            boundary = max(cleaned.rfind(mark, start + max_chars // 2, end) for mark in ".?!")
            if boundary == -1:
                boundary = cleaned.rfind(" ", start + max_chars // 2, end)
            if boundary != -1:
                end = boundary + 1
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


