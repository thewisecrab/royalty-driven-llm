# Changelog

## 1.0.0 - 2026-07-10

- Establishes a production-stable software baseline while requiring signed,
  externally trusted attestations before any operator may claim a production
  deployment or enable direct creator settlement.
- Adds publicly verifiable Ed25519 receipt signatures while retaining HMAC only
  for explicitly labelled synthetic fixtures.
- Raises the cryptography floor to 48.0.1 to exclude known-vulnerable releases.
- Grounds provider requests with source context before generation, captures
  provider request/response hashes and source annotations, and fails closed when
  returned source identifiers do not match the supplied context.
- Escrows allocations for unsupported, negated, numerically embellished, or
  over-warranted claims and labels post-hoc matching as review-only evidence.
- Adds public source-footer verification for standalone footer artifacts and
  copied/exported answer text.
- Tightens public footer verification against forged event bindings,
  public-verifier status drift, and non-verified footers.
- Adds package metadata auditing so release gates verify the production-stable
  classifier, package version, public URLs, console scripts, citation metadata,
  and cryptographic runtime dependency posture before shipping.

## 0.1.0 - 2026-07-01

- Initial shipping candidate for the RDLLM reference implementation.
- Includes RDLLM certification through `RDLLM-L186`.
- Adds universal provider response-state normalization so blocked, filtered,
  refused, truncated, tool-only, errored, or unknown provider terminal states
  cannot be rendered as grounded source-footer answers.
- Publishes reference artifacts, schemas, provider-neutral adapter contracts,
  certification report, proof dependency graph, README, research notes, and
  manuscript references.
