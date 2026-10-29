# Royalty Driven LLM (RDLLM)

[![CI](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/ci.yml/badge.svg)](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/ci.yml)
[![Pages](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/pages.yml/badge.svg)](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/pages.yml)

RDLLM is a beta reference implementation for visible source evidence and
auditable creator allocation on AI answers. It records which sources were
supplied, how strongly a claim overlaps their text, how a creator pool was
divided, and whether settlement is eligible, held, or escrowed.

It does not discover hidden training-data use. It does not execute payments.
It has not been validated against live model-provider APIs, and it has not
been scored on a public attribution benchmark.

Version `1.0.0`. MIT licensed. Created and maintained by Siddharth Nilesh Patel.
The white paper is [paper/rdllm_white_paper.md](paper/rdllm_white_paper.md)
(PDF: [paper/arxiv/rdllm_white_paper.pdf](paper/arxiv/rdllm_white_paper.pdf)).

## Status

The package classifier is `Development Status :: 4 - Beta`. The 1.x interfaces
are in use. No production deployment has been externally attested.
`production_grade_claim_allowed` stays `false` on the bundled profile so the
software cannot certify its own deployment.

`RDLLM-L0` through `RDLLM-L186` is the project's internal conformance suite
(187 self-checked cases). It is not a third-party certification.

The package is not on PyPI. The published GitHub Release
[v1.0.0](https://github.com/thewisecrab/royalty-driven-llm/releases/tag/v1.0.0)
ships the 2026-07-10 wheel and sdist. That release does not include the
unreleased entailment channel, eval harness, Shapley/Banzhaf options, or
license parsers described below. Those are in this source tree. See `CHANGELOG.md`.

## Install and quickstart

Install from a checkout of this GitHub repository, not from PyPI:

```bash
git clone https://github.com/thewisecrab/royalty-driven-llm.git
cd royalty-driven-llm
python -m pip install .
rdllm-first-run
```

The first line of the demo should be:

```text
rdllm_first_run status: passed
```

The demo is synthetic. Its creators, works, URLs, revenue, and allocations are
fictitious. No model provider is called and no money moves. On the bundled
corpus the same command reports 3 visible sources, 6 supported claim-evidence
rows, and 3 candidate allocation rows. One source row from that run is:

```text
[S1] Provenance Ledgers for AI Outputs - Arjun Rao; claims=2; support=0.295; text_match=0.900; payout=0.183279
```

`support` on that row is text overlap (`rdllm-claim-text-overlap/v1`), not an
entailment judgment. `payout` is an allocation amount, not proof that a payment
executed. Direct settlement additionally requires a trusted external
payment-processor attestation.

To install only the published 1.0.0 artifacts, use the wheel or sdist attached
to the GitHub Release above. Do not run `pip install royalty-driven-llm`.

[Follow the five-minute walkthrough](docs/first_5_minutes.md)

## What you get

- an answer with visible source labels such as `[S1]`;
- claim-to-evidence rows with hashes and character spans;
- a text-overlap score, kept separate from an optional entailment channel;
- observable usage metrics for retrieval, matching, citations, and allocation;
- a source footer that can be re-verified after API delivery, copy, or export; stripped or altered footers are detected;
- Ed25519-signed receipts that a third party can verify offline;
- a settlement decision that fails closed when evidence is weak or missing.

## Text overlap and the optional entailment channel

The score that decides whether a claim is `supported` is lexical. Its metric id
is `rdllm-claim-text-overlap/v1`. The older id
`rdllm-claim-overlap-support/v1` is no longer written on new rows. A separate
n-gram / longest-common-subsequence score remains
`rdllm-ngram-lcs-text-match/v1`.

`rdllm-nli-support/v1` is an optional claim-versus-document score in the style
of MiniCheck and AlignScore: the evidence is the premise and the claim is the
hypothesis. The default backend is `rdllm-deterministic-entailment-stub`
version `1`. It does not import torch. Naming `minicheck` or `alignscore`
lazy-imports that package and, if the package or a local scorer is missing,
falls back to the same stub and records why. The stub does not change the
`supported` bit. No accuracy on a public benchmark has been measured.

## Eval harness

`tools/eval_support_checker.py` scores a local JSON or JSONL file of
claim/document rows (the field shape used by AttributionBench and
LLM-AggreFact). It can download `lytang/LLM-AggreFact` only when you ask, and
that dataset is gated. Nothing from it is committed here.

The file `tests/fixtures/support_eval/synthetic_factcheck.jsonl` is a synthetic
fixture for the loader. It is not a benchmark sample and not a measured result.
This repository does not publish precision, recall, or balanced accuracy.

```bash
PYTHONPATH=src python3 tools/eval_support_checker.py sources
PYTHONPATH=src python3 tools/eval_support_checker.py score tests/fixtures/support_eval/synthetic_factcheck.jsonl
```

## Payout allocation

The default allocator is still the fixed-coefficient utility in the engine
(`fixed_coefficients`). Pass `allocation_method="shapley"` or
`allocation_method="banzhaf"` to use exact Shapley values (Monte Carlo past 10
players) or a normalized Banzhaf index. The reference value function is
output-token coverage. Method ids:

- `rdllm-fixed-coefficient-allocation/v1`
- `rdllm-shapley-context-allocation/v1`
- `rdllm-normalized-banzhaf-context-allocation/v1`

These are classical cooperative values. They are not the polynomial MaxShapley
algorithm and not Cluster Shapley clustering. Unit tests check efficiency,
symmetry, and the null player on small games. They are not a fairness study,
and the weights are not calibrated on a public dataset. The service footer
still records the default payout metric
`rdllm-creator-pool-weighted-allocation/v1` unless a caller selects another
engine method.

## Licensing and opt-out signals

`src/rdllm/licensing_signals.py` parses:

- RSL 1.0 XML (`https://rslstandard.org/rsl`);
- IETF `Content-Usage` dictionaries from draft-ietf-aipref-vocab-08
  (`train-ai`, `ai-use`, `search`, tokens `y` and `n`);
- robots.txt groups, `tdm-reservation`, and embedded `Content-Usage` lines.

A content-protocol record uses that parse only when `parse_machine_readable`
is true. Records that already carry labels are left alone. The mapping into
RDLLM use names is an engineering interpretation for the policy checker. It is
not a legal opinion about whether an opt-out is effective.

## Three ways to use it

**Ground a provider response:** RDLLM retrieves allowed source context before
generation, requires the provider to return matching source IDs or native
annotations, and binds request, response, context, and evidence hashes. That
path is tested against an OpenAI-compatible mock. It has not been validated
against live provider APIs. The 16 provider families in
[docs/provider_compatibility_matrix.md](docs/provider_compatibility_matrix.md)
are design fixtures.

**Audit existing text:** RDLLM can measure observable overlap after generation,
but labels that result `post_hoc_observable_match` and holds settlement for
review. It does not present similarity as proof of model reliance.

**Allocate creator value:** verified context-grounded claims can produce a
settlement instruction. Unsupported, negated, numerically embellished, disputed,
or rights-blocked claims route value to escrow.

[See 15 runnable use cases with screenshots](examples/live_use_cases/README.md).
The screenshots are local runs on synthetic data. `provider-live-smoke` uses a
mock provider on localhost.

## What is and isn't validated

Validated in this repository, on synthetic fixtures and offline checks:

- unit tests for the mechanism, service, signatures, and the new scoring,
  allocation, parsing, and harness code;
- the internal conformance suite through `RDLLM-L186`;
- schema checks, footer re-verification, and fail-closed settlement on the
  bundled adversarial fixtures;
- a deterministic entailment stub, including cases where word overlap is high
  and the stub still marks a negation as not entailed;
- Shapley and normalized Banzhaf properties on small explicit value functions;
- parsers for the small RSL, aipref, and robots/TDM fixtures in
  `tests/fixtures/licensing`.

Not validated, and not claimed:

- accuracy of the entailment stub or of MiniCheck/AlignScore on AttributionBench,
  LLM-AggreFact, or any other public set (those runs were not done);
- any live provider API (OpenAI, Anthropic, Gemini, or the other families in
  the design matrix);
- legal correctness of a royalty, opt-out, or licence interpretation;
- a user study of footer comprehension;
- that a `payout` figure was paid;
- that text overlap or the stub measures what the model relied on internally;
- origin hosting of `/.well-known/rdllm.json` (the files exist under
  `docs/.well-known`; GitHub project Pages does not serve them at the origin
  well-known path).

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 tools/build_public_site.py --check
PYTHONPATH=src python3 tools/production_readiness.py --json
PYTHONPATH=src python3 tools/ship_check.py
```

Python 3.10 or newer. Runtime dependency: `cryptography>=50.0.0,<51`.
Development extras (`jsonschema`, `markdown`, `build`, `pip-audit`) are the
`dev` extra in `pyproject.toml`.

## Trust boundary

An operator deployment is not production-attested merely because its
configuration passes. Production claims require signed third-party evidence
verified against an independently managed trust store. Bundled artifacts are
synthetic fixtures, and shared-secret HMAC is never accepted as a public
production signature.

RDLLM reports observable source use and allocation by default:

```text
observable_support_allocation_not_model_internal_reliance
```

## Integrate

- [API guide](docs/service_api.md)
- [API client examples](examples/api_clients/README.md)
- [Provider onboarding](docs/provider_onboarding.md)
- [Deployment and external attestations](docs/production_readiness.md)
- [Receipt protocol](docs/attribution_receipt_protocol.md)

## Understand

- [GitHub Start Here](docs/github_start_here.md)
- Quickstarts: [English](docs/i18n/en/quickstart.md), [French](docs/i18n/fr/quickstart.md), [Vietnamese](docs/i18n/vi/quickstart.md)
- [Plain-language and multilingual explanations](docs/public_explainer.md)
- [Mechanism and formulas](docs/mechanism.md)
- [Evidence and limitations](docs/evidence.md)
- [Recent research](docs/recent_research.md)
- [White paper](paper/rdllm_white_paper.md) and [PDF](paper/arxiv/rdllm_white_paper.pdf)
- [Project attribution map](docs/project_attribution.md)
