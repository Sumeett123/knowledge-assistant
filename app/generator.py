import os
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
            "Answer the question using only the supplied sources. Synthesize all relevant "
            "sources, rather than copying one sentence. Give a complete, well-structured "
            "answer with a definition, explanation, and key points when the evidence supports them. "
            "For long-answer or exam-style questions, use short paragraphs or bullets. Do not invent facts. "
            "If the sources do not contain the answer, say exactly: I don't know."
        )
        # Reserve room for the question and instructions.  This avoids the old behavior
        # where tokenizer truncation removed the question and later PDF evidence.
        source_labels = "".join(f"[Source {index}]\n" for index in range(1, len(contexts) + 1))
        reserved = len(self.tokenizer.encode(instruction + question + source_labels + "Sources: Question: Answer:", add_special_tokens=True)) + 12
        available = max(24, MAX_INPUT_TOKENS - reserved)
        per_source = max(24, available // max(len(contexts), 1))
        source_blocks = []
        for index, context in enumerate(contexts, start=1):
            token_ids = self.tokenizer.encode(context, add_special_tokens=False)[:per_source]
            source_blocks.append(f"[Source {index}]\n{self.tokenizer.decode(token_ids, skip_special_tokens=True)}")
        sources = "\n\n".join(source_blocks)
        prompt = f"{instruction}\n\nSources:\n{sources}\n\nQuestion:\n{question}\n\nAnswer:"
    
        inputs = self.tokenizer(
        prompt,
        return_tensors="pt",
        truncation=False,
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
