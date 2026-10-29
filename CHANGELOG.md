# Changelog

## Unreleased

- Marks RDLLM 1.0 as a beta reference implementation. The PyPI classifier is
  `Development Status :: 4 - Beta`. No production deployment has been
  externally attested. The package metadata gate now requires that Beta
  classifier.
- Relabels lexical claim scoring as text overlap
  (`rdllm-claim-text-overlap/v1`). Adds an optional entailment channel
  (`rdllm-nli-support/v1`, MiniCheck/AlignScore-style premise/hypothesis
  setup). The default backend is a deterministic stub. A named MiniCheck or
  AlignScore backend is imported only on request and falls back to the stub
  when the package or a local scorer is absent. No benchmark accuracy is
  published with this change.
- Adds `tools/eval_support_checker.py` to score that checker on a local
  claim/document file. The committed file under `tests/fixtures/support_eval`
  is a synthetic fixture, not a public benchmark and not a measured result.
  LLM-AggreFact can be downloaded on request and is not vendored.
- Adds exact and Monte Carlo Shapley values, and a normalized Banzhaf index,
  as opt-in creator-pool allocators beside the fixed coefficients. The default
  allocator is unchanged. The reference value function is output-token
  coverage. It is not an implementation of MaxShapley or Cluster Shapley, and
  it has not been calibrated on a public dataset.
- Parses RSL 1.0 XML, IETF draft-ietf-aipref-vocab-08 Content-Usage
  dictionaries, and robots.txt / TDM reservation signals when a protocol
  record sets `parse_machine_readable`.
- Describes `RDLLM-L0` through `RDLLM-L186` as the project's internal
  conformance suite, not third-party certification. Provider-family rows are
  design fixtures and have not been validated against live provider APIs.
- Marks `paper/royalty_driven_llm_paper.md` as a superseded historical draft.
  The current paper is `paper/rdllm_white_paper.md`. The exported
  `docs/.well-known` tree is not claimed as a hosted origin `/.well-known`
  surface.
- Raises the cryptography floor from `>=48.0.1,<49` to `>=50.0.0,<51`.
  `cryptography` 48.0.1 is flagged by current pip-audit (PYSEC-2026-3552,
  PYSEC-2026-3553, PYSEC-2026-3554). A clean environment with 50.0.0 and the
  dev extras reported no known vulnerabilities. Python 3.10 through 3.13 remain
  in the classifiers; cryptography 50.0.0 still publishes 3.10 and 3.11 wheels.
- Corrects bibliography entries `syta2015cosi`, `wu2026aioEcosystem`,
  `permissiveWashing2026`, and `gadWild2026` to the arXiv records for those
  ids. Removes `hu2026aibom` because arXiv:2605.19755 is a different paper and
  the cited Hu and Wang work could not be confirmed.

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
- Includes the project's internal conformance suite through `RDLLM-L186`
  (self-checked; no third-party certification).
- Adds universal provider response-state normalization so blocked, filtered,
  refused, truncated, tool-only, errored, or unknown provider terminal states
  cannot be rendered as grounded source-footer answers.
- Publishes reference artifacts, schemas, provider-neutral adapter contracts,
  certification report, proof dependency graph, README, research notes, and
  manuscript references.
