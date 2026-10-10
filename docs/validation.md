# Validation — 10 October 2026

## Checked

- Python 3.12: 13 backend regression tests passed.
- Ruff: backend, scripts and tests passed.
- Node: 2 frontend helper tests passed.
- Vite production build passed (about 76 KB gzip for JavaScript and 4 KB gzip for CSS).
- npm dependency audit: no known vulnerabilities in the installed frontend dependency tree.
- Chrome: sample document, source retrieval, persisted sessions, export, original PDF/help dialogs, unmatched questions and 390px overflow checks passed; no page errors.
- axe WCAG 2 A/AA and WCAG 2.1 AA scan on the study screen: no violations detected. This is an automated check, not certification of accessibility.
- Live local LM Studio: an explanation and a three-question practice set passed the structured-output/source-ID checks using only the original three-page sample. The explanation and practice answers were manually compared with those passages. This tiny smoke check is not an answer-accuracy benchmark.

The live test found and corrected two integration failures: the local provider requires `json_schema` rather than `json_object`, and practice mode needed a dedicated questions/answers schema rather than a generic answer string. Guided learning also requires a follow-up question. Provider failures and malformed output remain visible source-only results.

## Limits

No broad corpus evaluation, load test, full accessibility audit, Safari/Firefox test, deployment validation, or actual neural-model integration was performed. No user-provided textbooks or personal documents were used in tests. Large, scanned or complex-layout PDFs may require splitting or OCR.

The document boundary restricts retrieval and disables general-knowledge fallback; it does not prove every model claim is grounded. Source-ID checks do not establish semantic entailment or defeat prompt injection. All users of a shared workspace see the same library.

Screenshots use original sample study material, not private documents. Generated test sessions and runtime files are ignored by Git.
