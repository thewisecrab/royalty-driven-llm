# Royalty Driven LLM (RDLLM)

[![CI](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/ci.yml/badge.svg)](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/ci.yml)
[![Pages](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/pages.yml/badge.svg)](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/pages.yml)

RDLLM adds visible source evidence and auditable creator allocation to AI
answers. It records which sources were supplied, which claims they support, how
much value was allocated, and whether settlement is eligible, held, or escrowed.

## Try It

```bash
python -m pip install .
rdllm-first-run
```

The first line should be:

```text
rdllm_first_run status: passed
```

The demo is deliberately synthetic. Its creators, works, URLs, revenue, and
allocations are fictitious; no model provider is called and no money moves.

[Follow the five-minute walkthrough](docs/first_5_minutes.md)

## What You Get

- an answer with visible source labels such as `[S1]`;
- claim-to-evidence rows with hashes and character spans;
- observable usage metrics for retrieval, matching, citations, and allocation;
- a source footer that survives API, copy, and export verification;
- a settlement decision that fails closed when evidence is weak or missing;
- publicly verifiable Ed25519 receipts for production integrations.

Example footer row:

```text
[S1] Provenance Ledgers for AI Outputs; claims=2; support=0.900;
weight=1.000000; payout=0.550000; settlement=allocated_not_executed
```

`payout` is an allocation amount, not proof that a payment executed. Direct
settlement additionally requires a trusted external payment-processor
attestation.

## Three Ways To Use It

**Ground a provider response:** RDLLM retrieves allowed source context before
generation, requires the provider to return matching source IDs or native
annotations, and binds request, response, context, and evidence hashes.

**Audit existing text:** RDLLM can measure observable overlap after generation,
but labels that result `post_hoc_observable_match` and holds settlement for
review. It does not present similarity as proof of model reliance.

**Allocate creator value:** verified context-grounded claims can produce a
settlement instruction. Unsupported, negated, numerically embellished, disputed,
or rights-blocked claims route value to escrow.

[See 15 runnable use cases with screenshots](examples/live_use_cases/README.md)

## Trust Boundary

RDLLM 1.0 is production-stable software. An operator deployment is not
production-attested merely because its configuration passes. Production claims
require signed third-party evidence verified against an independently managed
trust store. Bundled artifacts are synthetic fixtures and shared-secret HMAC is
never accepted as a public production signature.

RDLLM reports observable source support and allocation by default:

```text
observable_support_allocation_not_model_internal_reliance
```

It does not claim to discover hidden training-data use or causal model reliance
from output similarity.

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
- [White paper](paper/rdllm_white_paper.md)
- [Project attribution map](docs/project_attribution.md)

## Verify The Release

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 tools/build_public_site.py --check
PYTHONPATH=src python3 tools/production_readiness.py --json
PYTHONPATH=src python3 tools/ship_check.py
```

The repository release may be ready while `production_grade_claim_allowed` is
`false`. That is expected for the bundled unattested profile and prevents the
software from certifying its own deployment.

Version `1.0.0`. MIT licensed. Created and maintained by Siddharth Nilesh Patel.
