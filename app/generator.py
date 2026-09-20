import os
import re
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_NAME = os.getenv("KNOWLEDGE_ASSISTANT_MODEL", "google/flan-t5-large")
# FLAN-T5 was trained with a 512-token input window.  Keep this capped even if
# an environment variable is accidentally set higher.
MAX_INPUT_TOKENS = min(int(os.getenv("MAX_INPUT_TOKENS", "512")), 512)
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "768"))

class LocalGenerator:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_NAME,
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32,
        ).to(self.device)
        self.model.eval()

    def generate(self, question: str, contexts: list[str]) -> str:
        # A very long query must not consume the evidence window.  API validation still
        # accepts natural-language questions up to 4,000 characters.
        question = self.tokenizer.decode(
            self.tokenizer.encode(question, add_special_tokens=False)[:160], skip_special_tokens=True
        )
        instruction = (
            "Use only the supplied sources. Answer the question using related facts even if "
            "the wording differs. Give a complete answer with the important definitions and "
            "details supported by the sources. Do not invent facts. If the sources do not "
            "contain the answer, say exactly: I don't know."
        )
        if re.search(r"\b(different|types?|levels?|steps?|stages?|phases?|categories?)\b", question, re.IGNORECASE):
            instruction += (
                " The question asks about multiple items. Identify every distinct item named "
                "in the sources and explain each one in a numbered list. Do not answer with "
                "only a general introductory sentence."
            )
        # Reserve room for the question and instructions.  This avoids the old behavior
        # where tokenizer truncation removed the question and later PDF evidence.
        source_labels = "".join(f"[Source {index}]\n" for index in range(1, len(contexts) + 1))
        reserved = len(self.tokenizer.encode(instruction + question + source_labels + "Sources: Question: Answer:", add_special_tokens=True)) + 12
        available = max(24, MAX_INPUT_TOKENS - reserved)
        # Retrieved chunks are already ranked. Give the strongest half more room so
        # multi-concept questions retain explanations instead of only headings.
        source_count = max(len(contexts), 1)
        priority_count = max(1, (source_count + 1) // 2)
        weighted_slots = source_count + priority_count
        base_source_tokens = max(24, available // weighted_slots)
        source_blocks = []
        for index, context in enumerate(contexts, start=1):
            token_budget = base_source_tokens * (2 if index <= priority_count else 1)
            token_ids = self.tokenizer.encode(
                context, add_special_tokens=False, truncation=True, max_length=token_budget,
            )
            source_blocks.append(f"[Source {index}]\n{self.tokenizer.decode(token_ids, skip_special_tokens=True)}")
        sources = "\n\n".join(source_blocks)
        # Keep the question before the evidence so tokenizer truncation never
        # removes the user's intent when adjacent chunks are long.
        prompt = f"{instruction}\n\nQuestion:\n{question}\n\nSources:\n{sources}\n\nAnswer:"
    
        inputs = self.tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_INPUT_TOKENS,
        ).to(self.device)

        with torch.inference_mode():
            outputs = self.model.generate(
            **inputs,
            max_new_tokens=MAX_OUTPUT_TOKENS,
            do_sample=False,
            num_beams=2,
            early_stopping=True,
            )

        return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    def simplify(self, previous_answer: str) -> str:
        """Restate an existing grounded answer without running document retrieval again."""
        instruction = (
            "Rewrite the answer below in simple, clear language for a student. "
            "Keep the important facts, use short bullets when useful, and do not add facts."
        )
        available = max(24, MAX_INPUT_TOKENS - len(self.tokenizer.encode(instruction + "\nAnswer:", add_special_tokens=True)) - 12)
        answer_tokens = self.tokenizer.encode(previous_answer, add_special_tokens=False)[:available]
        prompt = f"{instruction}\n\nAnswer:\n{self.tokenizer.decode(answer_tokens, skip_special_tokens=True)}\n\nSimple version:"
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=False).to(self.device)
        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=MAX_OUTPUT_TOKENS,
                do_sample=False,
                num_beams=2,
                early_stopping=True,
            )
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    def rewrite(self, previous_answer: str, style: str) -> str:
        """Change presentation while keeping the previous grounded answer as the only source."""
        instructions = {
            "simple": "Rewrite this answer in very simple, clear student-friendly language. Keep the facts and do not add facts.",
            "short": "Give a short summary of this answer in no more than four clear sentences. Keep only facts present in the answer.",
            "bullets": "Rewrite this answer as concise bullet points. Keep the facts and do not add facts.",
            "example": "Give one simple example that explains the answer. Use only facts already stated or an explicitly generic illustration; do not claim new document facts.",
            "exam": "Rewrite this as a neat exam-style answer with a short introduction and clear bullet points. Keep the facts and do not add facts.",
            "student": "Rewrite this answer as if explaining to a school student. Use very simple words, short sentences, and one relatable everyday analogy. Keep facts accurate and do not add new facts.",
            "table": "Rewrite this answer as a comparison table in plain-text markdown format using | column | separators. Rows should cover the key points. Keep facts accurate and do not add new facts.",
        }
        instruction = instructions.get(style, instructions["simple"])
        available = max(24, MAX_INPUT_TOKENS - len(self.tokenizer.encode(instruction + "\nAnswer:", add_special_tokens=True)) - 12)
        answer_tokens = self.tokenizer.encode(previous_answer, add_special_tokens=False)[:available]
        prompt = f"{instruction}\n\nAnswer:\n{self.tokenizer.decode(answer_tokens, skip_special_tokens=True)}\n\nRewritten answer:"
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=False).to(self.device)
        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs, max_new_tokens=MAX_OUTPUT_TOKENS, do_sample=False,
                num_beams=2, early_stopping=True,
            )
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

#outputs actually returns in batch for and we want the first generated sequence also we have one prompt so there'll only be one generated seq.


#singleton (load once)
generator = LocalGenerator()

def generate_answer(question: str, contexts: list[str]) -> str:
    return generator.generate(question, contexts)


def simplify_answer(previous_answer: str) -> str:
    return generator.simplify(previous_answer)


def rewrite_answer(previous_answer: str, style: str) -> str:
    return generator.rewrite(previous_answer, style)
