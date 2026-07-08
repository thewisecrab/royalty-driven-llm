# Royalty Driven LLM (RDLLM)

[![CI](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/ci.yml/badge.svg)](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/ci.yml)
[![Pages](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/pages.yml/badge.svg)](https://github.com/thewisecrab/royalty-driven-llm/actions/workflows/pages.yml)

RDLLM is an open-source attribution and royalty-settlement layer for AI
answers. It helps an AI product show which sources support an answer, which
claims those sources support, and how creator value is allocated or held for
review.

The short version: AI answers should not just cite sources. They should show the
source footer, bind claims to evidence, expose the usage metrics, and make
creator settlement auditable.

## Start Here

Install and run the guided demo:

```bash
python -m pip install .
rdllm-first-run
```

Expected first line:

```text
rdllm_first_run status: passed
```

The demo prints:

- an answer with visible source labels such as `[S1]`;
- source rows with `support`, `text_match`, `payout`, and hash fields;
- Claim Evidence rows that connect each claim to source evidence;
- `disagreement=passed` when visible sources do not contradict the claim.

## What RDLLM Does

- Shows sources in the answer footer.
- Connects answer claims to evidence spans.
- Measures observable source usage.
- Allocates a creator pool across credited sources.
- Routes uncertain value to escrow or review instead of silently dropping it.
- Verifies that APIs, copy/export paths, and public proof artifacts preserve the
  source footer.

## What RDLLM Does Not Claim

RDLLM does not claim hidden model-internal reliance by default. The default
profile reports observable source support and settlement allocation:

```text
observable_support_allocation_not_model_internal_reliance
```

If a provider wants to claim model-internal reliance, it needs separate verified
telemetry.

## Common Use Cases

- AI search or chat answers with source footers.
- RAG systems that need claim-level attribution.
- Creator platforms that need usage-based payout or escrow evidence.
- Enterprise assistants that need verifiable provenance.
- Model-provider or gateway routes that need public attribution receipts.
- Public-sector or regulated deployments that need audit trails.

## Documentation

Start with these:

- [GitHub Start Here](docs/github_start_here.md)
- [First 5 Minutes](docs/first_5_minutes.md)
- [Public explainer](docs/public_explainer.md)
- [Project attribution map](docs/project_attribution.md)
- [White paper](paper/rdllm_white_paper.md)
- [Live use cases](examples/live_use_cases/README.md)
- [API client examples](examples/api_clients/README.md)

Multilingual quickstarts:

- [English](docs/i18n/en/quickstart.md)
- [French](docs/i18n/fr/quickstart.md)
- [Vietnamese](docs/i18n/vi/quickstart.md)
- [All language explainers](docs/public_explainer.md)

Deeper technical references:

- [Mechanism](docs/mechanism.md)
- [Evidence map](docs/evidence.md)
- [Recent research](docs/recent_research.md)
- [References](docs/references.md)
- [Service API](docs/service_api.md)
- [Deployment](docs/deployment.md)
- [Production readiness](docs/production_readiness.md)
- [Release checklist](docs/release_checklist.md)

## Verify The Repo

Run the public-facing checks:

```bash
PYTHONPATH=src python3 tools/docs_link_audit.py
PYTHONPATH=src python3 tools/github_docs_readiness_audit.py
PYTHONPATH=src python3 tools/production_readiness.py
PYTHONPATH=src python3 tools/ship_check.py --skip-tests --skip-regenerate --skip-package
```

Run the full test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Project Status

RDLLM is packaged as `royalty-driven-llm` version `1.0.0` with no required
runtime dependencies. The repository includes CLI tools, an HTTP service,
schemas, proof artifacts, live examples, multilingual docs, and public release
gates.

Read the white paper for the full concept and evidence base:
[paper/rdllm_white_paper.md](paper/rdllm_white_paper.md).
