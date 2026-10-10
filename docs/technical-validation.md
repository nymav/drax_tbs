# DRAX v3 validation

Validated locally on macOS with Python 3.12, Chrome, and an existing LM Studio Mistral 7B model. All document tests use original synthetic/sample content.

| Upgrade | Validation |
| --- | --- |
| Structured ingestion | Real PDF with a ruled table, font-sized heading, nested outline, and exact page coordinates; aligned visual lines reconstruct into body passages |
| Hybrid retrieval | Actual MiniLM embeddings and MS MARCO cross encoder; 12 labelled queries, including four paraphrases, compared with lexical search |
| Hierarchy and summaries | Persisted section tree, nested parent relationship, section-scoped abstention, extractive digest and a completed live background study-note job |
| Claim evidence | Invalid quotes rejected; schema binds each allowed quote to the actual source; generated free prose is discarded; live answer contained two valid quotes |
| Durable jobs | Active-job deduplication, restart recovery, three-attempt limit, failed index preserving prior content, and termination of a real running child process |
| Context budgeting | Loaded context verified as 4,096; tokenizer/template counting; lower-ranked evidence removed before generation; overflow rejected without provider call |
| Index versions | File change rejection; extractor, embedding model and vector-dimension metadata retained |
| Regression evaluation | Recall@3, MRR, unrelated-query abstention, warm latency and Python-tracked memory; lexical CI gate and optional neural comparison gate |
| Storage reliability | Unversioned migration preserves data and rebuilds FTS IDs; concurrent turns retained; verified backup/restore and checksum tampering rejection |

27 backend tests and 2 frontend tests pass, along with Ruff, the production frontend build, and the lexical regression gate. Chrome checks found zero JavaScript errors, zero WCAG A/AA axe violations in the tested study view, and no horizontal overflow at 390px. Desktop/mobile screenshots are in `docs/images/`.

The live full-document job completed on its first attempt: six indexed passages, three submitted body passages, two cited passages, one batch. This explicitly measures submissions and citations separately; it does not claim every detail was summarised.

The labelled corpus is small. Hybrid recall@3 and MRR were 1.00, compared with lexical 0.917 and 0.875 on the same 12 questions. These are regression results, not production accuracy estimates. Timing varies by host and model warmup; native tensor memory is not included in the Python memory metric.

Exact quote membership does not establish semantic entailment. Humans must review generated explanations. Inference cancellation in LM Studio is controlled by that server; cancelling a note job terminates the DRAX worker and prevents further batches/results, while index cancellation directly stops extraction/embedding work. Backup/restore requires a stopped server and a new destination directory. SQLite remains suited to a small personal workspace, not a multi-tenant service.
