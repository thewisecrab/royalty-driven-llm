# Changelog

## 1.0.0 - 2026-07-02

- Promotes RDLLM to a production-grade open-source baseline for individuals,
  companies, institutions, governments, public-sector operators, and model
  providers.
- Adds public source-footer verification for standalone footer artifacts and
  copied/exported answer text.
- Tightens public footer verification against forged event bindings,
  public-verifier status drift, and non-verified footers.
- Adds package metadata auditing so release gates verify the production/stable
  classifier, package version, public URLs, console scripts, citation metadata,
  and runtime dependency posture before shipping.

## 0.1.0 - 2026-07-01

- Initial shipping candidate for the RDLLM reference implementation.
- Includes RDLLM certification through `RDLLM-L186`.
- Adds universal provider response-state normalization so blocked, filtered,
  refused, truncated, tool-only, errored, or unknown provider terminal states
  cannot be rendered as grounded source-footer answers.
- Publishes reference artifacts, schemas, provider-neutral adapter contracts,
  certification report, proof dependency graph, README, research notes, and
  manuscript references.
