# RDLLM Explained

## ELI5

Imagine an AI answer is a school report. RDLLM makes the AI show which books it
used, which sentence came from which book, and whether the people who made those
books should get credit or payment. If the proof is missing, the answer should
not pretend to be fully sourced.

## Simple

RDLLM is an open-source layer for AI products. It adds a visible source footer to
an answer, checks that the sources really support the claims, and records how
source usage maps to payout or escrow.

Use it when you are building a chatbot, RAG app, search assistant, agent, model
API, marketplace, or creator platform and you want users to see where an answer
came from.

## Non-Technical

RDLLM helps three groups:

- Users see sources, claim evidence, and confidence signals instead of a bare AI
  answer.
- Creators and publishers get attribution evidence and settlement records.
- Operators get verification gates before showing an answer as grounded or
  royalty-bearing.

The system does not claim that it can read a model's hidden thoughts. It reports
observable evidence: visible source support, answer-to-source overlap, claim
evidence, source-disagreement checks, and payout allocation.

## Technical

At runtime, RDLLM takes an answer, source references, and revenue context. It
builds a source footer with source rows and Claim Evidence rows. Each claim row
includes a claim hash, support score, evidence span hash, character offsets,
evidence preview, warrant status, source-disagreement status, and source label.

Before display, verifiers recompute the display hash, footer hash, row hashes,
source usage metrics, claim evidence, citation markers, answer links,
claim-source closure, model-reliance wording, attribution-gap closure, and source
disagreement. The response is public-facing only when
`production_display_ready` is true and `source_grounding_acceptance` is passed.

For implementation, start with:

- [Quickstart](quickstart.md)
- [GitHub Start Here](../../github_start_here.md)
- [Live use cases](../../../examples/live_use_cases/README.md)
- [API client examples](../../../examples/api_clients/README.md)

