"""Comprehensive edge-case tests for the Knowledge Assistant utility layer.

These tests exercise the pure-Python helpers in ``app.utils`` and require
**no model loading, no FAISS, and no network**.  They can be run instantly
with ``pytest tests/test_edge_cases.py -v``.
"""

import pytest

from app.utils import (
    answer_request_kind,
    document_scope,
    is_ambiguous_standalone_question,
    is_nonsense_input,
    split_compound_questions,
)

# ---------------------------------------------------------------------------
# 1. Different ways to ask the same question (synonym / phrasing coverage)
# ---------------------------------------------------------------------------

class TestDifferentPhrasings:
    """The retriever handles synonym overlap; here we verify the classifier
    helpers do not accidentally flag valid questions."""

    @pytest.mark.parametrize("question", [
        "What is machine learning?",
        "Define machine learning.",
        "Explain machine learning in brief.",
        "Describe machine learning.",
        "What do you mean by machine learning?",
        "Give the definition of machine learning.",
        "How would you define machine learning?",
        "What are the advantages of online banking?",
        "What is the importance of information systems?",
        "Explain the significance of information systems.",
        "What are the benefits of MIS?",
    ])
    def test_valid_phrasings_not_flagged(self, question: str):
        assert not is_ambiguous_standalone_question(question)
        assert not is_nonsense_input(question)


# ---------------------------------------------------------------------------
# 2. Empty, invalid, and unusual input
# ---------------------------------------------------------------------------

class TestNonsenseInput:
    """Catches emoji-only, symbol-only, repeated-char, and empty input."""

    @pytest.mark.parametrize("value", [
        "",
        "   ",
        "\t\n",
        "😀😂🤣",
        "🔥🔥🔥🔥",
        "????",
        "!!!!",
        "@#$%^&*()",
        "aaaaaaa",
        "hahahaha",
        "....",
        "----",
    ])
    def test_nonsense_rejected(self, value: str):
        assert is_nonsense_input(value)

    @pytest.mark.parametrize("value", [
        "What is AI?",
        "Explain",
        "MIS",
        "hi",
        "Give advantages of internet.",
        "a1",
    ])
    def test_real_input_accepted(self, value: str):
        assert not is_nonsense_input(value)


# ---------------------------------------------------------------------------
# 3. Multiple questions in one message
# ---------------------------------------------------------------------------

class TestCompoundQuestions:

    def test_semicolon_split(self):
        result = split_compound_questions("Explain MIS; Explain DSS")
        assert len(result) == 2

    def test_numbered_split(self):
        result = split_compound_questions("1. Explain MIS 2. Explain DSS")
        assert len(result) == 2

    def test_and_also_split(self):
        result = split_compound_questions("Explain MIS and also explain DSS")
        assert len(result) == 2

    def test_single_stays_single(self):
        result = split_compound_questions("What are advantages and disadvantages of AI?")
        assert len(result) == 1

    def test_too_many_raises(self):
        with pytest.raises(ValueError, match="at most 2"):
            split_compound_questions("Explain MIS; Explain DSS; Explain ERP", max_questions=2)

    def test_empty_string(self):
        result = split_compound_questions("")
        assert result == []

    def test_duplicate_removed(self):
        result = split_compound_questions("Explain MIS; Explain MIS")
        assert len(result) == 1

    def test_importance_and_pros_pair(self):
        result = split_compound_questions(
            "Explain the importance of information system to society and also its benefits"
        )
        assert len(result) == 2

    def test_what_is_and_advantages(self):
        result = split_compound_questions(
            "what is information system and its advantages and disadvantages"
        )
        assert len(result) == 2
        assert any("information system" in q.lower() for q in result)
        assert any("advantages" in q.lower() for q in result)


# ---------------------------------------------------------------------------
# 4. Ambiguous or incomplete questions
# ---------------------------------------------------------------------------

class TestAmbiguousQuestion:

    @pytest.mark.parametrize("question", [
        "explain it",
        "explain this",
        "tell me more",
        "what about it",
        "what is it",
        "give advantages",
        "give disadvantages",
        "make it simple",
        "summarize it",
        "give an example",
        "shorten it",
        "simplify this",
        "describe the above",
    ])
    def test_ambiguous_detected(self, question: str):
        assert is_ambiguous_standalone_question(question)

    @pytest.mark.parametrize("question", [
        "Explain machine learning",
        "What are the advantages of online banking?",
        "Describe the types of MIS",
        "Give an example of neural networks",  # has a concrete topic
    ])
    def test_concrete_not_ambiguous(self, question: str):
        assert not is_ambiguous_standalone_question(question)


# ---------------------------------------------------------------------------
# 5. Follow-up questions (answer_request_kind)
# ---------------------------------------------------------------------------

class TestFollowUpDetection:

    def test_simplify_followup(self):
        assert answer_request_kind("Explain this more simply") == "simple"

    def test_short_followup(self):
        assert answer_request_kind("Give a short summary") == "short"

    def test_bullets_followup(self):
        assert answer_request_kind("Give bullet points") == "bullets"

    def test_example_followup(self):
        assert answer_request_kind("Give one real-life example") == "example"

    def test_unrelated_returns_none(self):
        assert answer_request_kind("What is machine learning?") is None


# ---------------------------------------------------------------------------
# 6. Answer format and understanding level
# ---------------------------------------------------------------------------

class TestAnswerFormat:

    @pytest.mark.parametrize("phrase,expected", [
        ("Explain simply.", "simple"),
        ("Make it simpler.", "simple"),
        ("Easy words please.", "simple"),
        ("Explain in 2 lines.", "short"),
        ("Give a brief answer.", "short"),
        ("Summarize it.", "short"),
        ("Give bullet points.", "bullets"),
        ("Give key points.", "bullets"),
        ("Give an exam answer.", "exam"),
        ("Give a 5-mark answer.", "exam"),
        ("Give a 10-mark answer.", "exam"),
        ("Give a 2-mark answer.", "exam"),
        ("Five mark answer please.", "exam"),
        ("Give one real-life example.", "example"),
        ("Give a practical example.", "example"),
        ("Explain for a school student.", "student"),
        ("Explain for a kid.", "student"),
        ("Explain for a child.", "student"),
        ("Tell me like a class 5 student.", "student"),
        ("Compare in a table.", "table"),
        ("Show as a comparison table.", "table"),
        ("Give in tabular form.", "table"),
    ])
    def test_style_detected(self, phrase: str, expected: str):
        assert answer_request_kind(phrase) == expected


# ---------------------------------------------------------------------------
# 7. Questions about uploaded documents
# ---------------------------------------------------------------------------

_FILENAMES = ["notes.pdf", "ml_unit_2.pdf", "lecture3.pdf"]


class TestDocumentScope:

    def test_first_pdf(self):
        scope = document_scope("Answer from the first PDF.", _FILENAMES)
        assert scope.include == ("notes.pdf",)

    def test_pdf_2(self):
        scope = document_scope("Answer from PDF 2.", _FILENAMES)
        assert scope.include == ("ml_unit_2.pdf",)

    def test_last_document(self):
        scope = document_scope("Use the last document.", _FILENAMES)
        assert scope.include == ("lecture3.pdf",)

    def test_second_pdf_explicit(self):
        scope = document_scope("Answer from the second PDF.", _FILENAMES)
        assert scope.include == ("ml_unit_2.pdf",)

    def test_unit_name_scoping(self):
        scope = document_scope("Answer only from ML Unit 2.", _FILENAMES)
        assert "ml_unit_2.pdf" in scope.include

    def test_ignore_first_pdf(self):
        scope = document_scope("Ignore the first PDF.", _FILENAMES)
        assert "notes.pdf" in scope.exclude
        assert "notes.pdf" not in scope.include

    def test_skip_second_pdf(self):
        scope = document_scope("Skip the second PDF.", _FILENAMES)
        assert "ml_unit_2.pdf" in scope.exclude

    def test_cross_document_default(self):
        """A question without naming a document should search all."""
        scope = document_scope("Compare the definition in both documents.", _FILENAMES)
        assert scope.include == ()
        assert scope.exclude == ()

    def test_which_pdf_contains(self):
        scope = document_scope("Which PDF contains neural networks?", _FILENAMES)
        assert scope.topic_search is True

    def test_which_document_has(self):
        scope = document_scope("Which document has this topic?", _FILENAMES)
        assert scope.topic_search is True

    def test_normal_question_no_topic_search(self):
        scope = document_scope("What is AI?", _FILENAMES)
        assert scope.topic_search is False

    def test_last_page(self):
        scope = document_scope("Answer from the last page.", _FILENAMES)
        assert scope.prefer_end is True

    def test_end_of_second_pdf(self):
        scope = document_scope("Use the end of the second PDF.", _FILENAMES)
        assert scope.prefer_end is True
        assert scope.include == ("ml_unit_2.pdf",)

    def test_exclude_by_filename(self):
        scope = document_scope("Ignore notes", _FILENAMES)
        assert "notes.pdf" in scope.exclude
