# RDLLM arXiv Submission Package

Author-produced PDF:

- `rdllm_white_paper.pdf`

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

Royalty Driven LLM Model (RDLLM) is a provider-neutral reference architecture for
making AI answers visibly grounded, auditable, and economically accountable. When
an AI product uses registered sources, retrieved evidence, generated text, or
provider-native source metadata to produce a public answer, RDLLM makes the
system show users which sources support the answer, explain observable source
usage in allocation terms, and route creator value to processor instruction,
review, or escrow rather than silently absorbing it. The design combines user-facing
source footers, claim-evidence rows, usage metrics with method provenance,
creator-pool allocation, escrow paths, response hashes, Ed25519 signatures,
external deployment attestations, public schemas, and verifier commands. RDLLM
does not claim hidden model-internal
reliance by default; it reports observable support and settlement allocation
unless separate provider telemetry proves internal reliance.

The repository's tests establish software and schema invariants over synthetic
fixtures. They do not constitute a comparative attribution benchmark, a user
study, legal validation, or evidence that a payment executed.

License:

The author must choose this during arXiv submission. arXiv states that the
license choice is irrevocable and that the submitter must certify they have the
right to grant it.
