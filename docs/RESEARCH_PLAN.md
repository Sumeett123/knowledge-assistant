# Research execution plan

## Research question

Does hybrid retrieval plus claim-level evidence verification reduce unsupported
answers while preserving answer quality in a local academic-PDF RAG system?

## Hypotheses

- Hybrid FAISS + BM25 retrieval improves Recall@k and MRR over dense-only
  retrieval, particularly on terminology and exact-detail questions.
- Cross-encoder reranking improves the relevance of final evidence.
- Claim-level verification and calibrated abstention reduce unsupported claims
  and increase citation precision.

## System variants

| ID | Variant |
| --- | --- |
| B0 | Existing dense FAISS retrieval + local generation |
| B1 | BM25 retrieval + local generation |
| B2 | Dense + BM25 hybrid retrieval (RRF) |
| B3 | Hybrid retrieval + reranking |
| B4 | Hybrid + reranking + verification/confidence abstention |

## Benchmark

Build `AcademicPDF-QA` from openly redistributable sources: 12–15 English
academic PDFs, 120 answerable questions, and 30 plausible but unanswerable
questions. Each answerable question records its reference answer and page-level
evidence. Source manifests retain URL, access date, checksum, and license.

## Measures

- Retrieval: Recall@5/10, MRR@10, nDCG@10.
- Answer quality: blinded 0/1/2 correctness rubric.
- Trust: citation precision/recall, unsupported-claim rate, verifier F1,
  answerable abstention rate, unanswerable abstention accuracy, selective risk.
- Operations: P50/P95 latency and local resource footprint.

## Delivery phases

1. **Baseline stabilization:** freeze the current dense-only behavior, add
   configuration, source IDs, test coverage, and a benchmark schema.
2. **Hybrid retrieval:** implement BM25, RRF, retrieval traces, and B0–B2
   evaluation.
3. **Reranking:** introduce configurable cross-encoder reranking and evaluate
   B3 latency/quality.
4. **Trust layer:** implement claim verification, confidence calibration, safe
   abstention, and B4 evaluation.
5. **Professional UX:** add collections, document states, evidence cards,
   confidence explanations, and accessible error/loading states.
6. **Paper package:** lock the dataset/configuration, reproduce experiments,
   generate tables/figures, document limitations and write the paper.

## Research discipline

The paper will claim improvement on this controlled benchmark, not universal
hallucination elimination. All variants use the same corpus, chunking, prompt,
generator, hardware, and retrieval candidate count where applicable.
