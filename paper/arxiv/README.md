# RDLLM arXiv Submission Package

Author-produced PDF:

- `rdllm_white_paper.pdf`, rendered 2026-10-29 from `paper/rdllm_white_paper.md`
  (document version 2026-10-29) by `tools/build_arxiv_white_paper.py`

Recommended arXiv metadata:

- Title: `RDLLM: Verifiable Source Attribution and Creator-Value Accounting for Grounded AI Outputs`
- Authors: `Siddharth Nilesh Patel`
- Suggested primary category: `cs.AI`
- Suggested cross-lists: `cs.CL`, `cs.IR`, `cs.CY`
- Comments: `Public technical white paper. Reference implementation and artifacts: https://github.com/thewisecrab/royalty-driven-llm`
- Report number: leave blank unless the author has an institutional report number
- Journal reference: leave blank
- DOI: leave blank

Abstract:

Royalty Driven LLM Model (RDLLM) is a beta, provider-neutral reference
implementation for visible source evidence and auditable creator allocation.
The default claim score is text overlap (`rdllm-claim-text-overlap/v1`). An
optional entailment channel (`rdllm-nli-support/v1`) defaults to a deterministic
stub and has not been evaluated with MiniCheck, AlignScore, or a public
benchmark. Shapley and normalized Banzhaf allocation are opt-in. RSL 1.0,
IETF aipref Content-Usage, and robots/TDM signals can be parsed. The package is
not on PyPI. Provider families in the repository are design fixtures; the
provider smoke uses a localhost mock. The internal conformance suite through
RDLLM-L186 is self-checked, not a third-party certification.

The repository's tests establish software and schema invariants over synthetic
fixtures. They do not constitute a comparative attribution benchmark, a user
study, legal validation, or evidence that a payment executed. No benchmark
accuracy is stated in the paper.

License:

The author must choose this during arXiv submission. arXiv states that the
license choice is irrevocable and that the submitter must certify they have the
right to grant it.
