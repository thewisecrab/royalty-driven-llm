# RDLLM Project Attribution Map

RDLLM is an attribution system, so the project documentation must also be
attributed. This page explains what the repository was built from, where each
source class is recorded, how those sources shaped the system, and how a reader
can verify the claims.

## Short Version

- Code is in `src/rdllm` and is published under the repository `LICENSE`.
- Runtime examples are produced by repository commands, especially
  `rdllm.cli answer`, `tools/service_smoke.py`, `tools/provider_live_smoke.py`,
  and `tools/package_smoke.py`.
- Research and policy sources are indexed in `docs/references.md`,
  `docs/recent_research.md`, `docs/evidence.md`,
  `paper/rdllm_white_paper.md`, and `paper/references.bib`.
- Public proof artifacts are in `artifacts/` and hosted copies are exported under
  `docs/.well-known/rdllm/`.
- Machine-checkable schemas are in `docs/schemas/` and packaged copies are in
  `src/rdllm/data/schemas/`.
- The shipping gate is `PYTHONPATH=src python3 tools/ship_check.py`.

## What Was Built

RDLLM is a provider-neutral source-attribution, source-footer, and
royalty-settlement reference implementation for AI outputs. It contains:

- a Python package: `src/rdllm`;
- HTTP service and verifier commands: `rdllm-service`,
  `rdllm-service-response-verify`, and `rdllm-source-footer-verify`;
- public schemas: `docs/schemas`;
- sample corpora and service configs: `examples`;
- proof and discovery artifacts: `artifacts` and `docs/.well-known`;
- research notes and manuscript material: `docs` and `paper`;
- production gates and smoke tests: `tools` and `tests`.

## Source Classes

| Source class | Where it is attributed | How it shaped RDLLM |
| --- | --- | --- |
| Creator revenue and rights-management analogies | `docs/evidence.md`, `paper/references.bib` | Fixed creator-pool framing, payout/escrow language, rights-conflict handling, and registry-dispute handling. |
| Source attribution, citation, RAG, and claim-verification papers | `docs/recent_research.md`, `docs/references.md`, `paper/rdllm_white_paper.md`, `paper/references.bib` | Claim Evidence rows, citation-marker gates, answer-link gates, source-disagreement gates, source-footer verification, and answer-claim coverage. |
| Data valuation and influence research | `docs/evidence.md`, `paper/references.bib` | Training-value priors, residual attribution concepts, counterfactual checks, and model-signal boundaries. |
| Provenance, credentials, trace, and transparency standards | `docs/evidence.md`, `docs/references.md`, `docs/schemas` | Verifiable receipt formats, PROV-shaped exports, VC-shaped credentials, OpenTelemetry-style trace exchange, transparency-log language, and schema-first artifact design. |
| Rights, licensing, and machine-readable policy standards | `docs/evidence.md`, `docs/mechanism.md`, `docs/schemas` | ODRL/Croissant/SPDX-aligned rights metadata, source-access leases, creator license contracts, consent revocation, and escrow routing. |
| Production security and public-sector guidance | `docs/recent_research.md`, `docs/production_readiness.md`, `docs/operator_runbook.md` | NIST AI RMF, NIST SSDF, OWASP LLM Top 10, SLSA, launch gates, operator profiles, support bundles, and fail-closed production readiness. |
| Provider API and runtime documentation | `docs/provider_onboarding.md`, `docs/provider_compatibility_matrix.md` | Provider-family routing, usage-meter normalization, response-state normalization, streaming final-state requirements, and source annotation normalization. |
| Public documentation and discoverability guidance | `docs/recent_research.md`, `docs/github_start_here.md`, `docs/public_explainer.md` | GitHub start guide, public explainers, localized quickstarts, API examples, SEO/GEO notes, and docs-readiness audit. |
| Repository-authored code and tests | `src/rdllm`, `tools`, `tests` | Deterministic attribution engine, verifiers, service boundary, operator tooling, package smoke, and shipping gate. |

## How Sources Become Product Rules

RDLLM does not treat a paper, standard, or platform analogy as a feature by
itself. A source becomes part of the system only when it is converted into an
auditable rule:

1. The source is recorded in `docs/recent_research.md`, `docs/evidence.md`,
   `docs/references.md`, or `paper/references.bib`.
2. The rule is implemented in `src/rdllm` or `tools`.
3. The runtime output or artifact shape is captured in `docs/schemas`.
4. Tests or smoke scripts prove the behavior.
5. User-facing docs show the exact field names that users will see.

Example: source-disagreement research becomes
`rdllm-visible-source-disagreement/v1`, visible `disagreement`,
`agreements`, and `conflicts` fields in Claim Evidence rows, verifier failures
when visible sources plainly contradict claims, schema fields, tests, and README
runtime examples.

## Code Attribution

The repository code is authored for this project and distributed under the
repository license. The Python package has no required runtime dependencies in
`pyproject.toml`; development checks use optional tooling such as `build` and
`jsonschema`.

Important code locations:

- `src/rdllm/engine.py`: core attribution engine and CLI answer rendering.
- `src/rdllm/service.py`: dependency-free HTTP service boundary.
- `src/rdllm/service_response_verifier.py`: full response/display verifier.
- `src/rdllm/source_footer_verifier.py`: standalone public footer verifier.
- `src/rdllm/source_footer_rendering.py`: user-visible source-footer rendering.
- `src/rdllm/source_usage_metrics.py`: observable source usage metric profile.
- `src/rdllm/source_disagreement.py`: conservative visible source-disagreement
  check.
- `tools/ship_check.py`: release gate.
- `tools/github_docs_readiness_audit.py`: public documentation readiness gate.

## Paper And Research Attribution

The paper source is `paper/royalty_driven_llm_paper.md`. The public concept
white paper is `paper/rdllm_white_paper.md`; it explains the state-of-the-art
evidence base, runtime architecture, allocation mechanism, threat model, and
public-readiness posture. The BibTeX bibliography is `paper/references.bib`.
The public human-readable reference index is `docs/references.md`. Current
implementation-facing research notes are in `docs/recent_research.md`.

When a new research source changes behavior, the repository should update:

- the relevant code or verifier;
- the schema;
- tests or smoke checks;
- public docs;
- `docs/recent_research.md` or `paper/references.bib`.

## Runtime Example Attribution

Runtime examples in public docs should be derived from commands, not invented:

```bash
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
PYTHONPATH=src python3 tools/service_smoke.py
PYTHONPATH=src python3 tools/provider_live_smoke.py
PYTHONPATH=src python3 tools/package_smoke.py
```

These commands produce source rows, support scores, text-match values, Claim
Evidence rows, payout fields, display hashes, and verifier statuses used in the
README and example docs.

## Public Artifact Attribution

Public artifacts are generated and verified through the repository gates. The
canonical source files are in `artifacts/`. Hosted copies for static discovery
are exported to `docs/.well-known/rdllm/` and indexed by
`docs/.well-known/rdllm.json`.

Verify hosted artifacts:

```bash
PYTHONPATH=src python3 tools/hosting_export.py --check
PYTHONPATH=src python3 tools/hosted_surface_audit.py
PYTHONPATH=src python3 tools/public_surface_privacy_audit.py
```

## Documentation Attribution

Public-facing docs follow a layered model:

- `docs/public_explainer.md`: language and explanation-depth selector.
- `docs/i18n/*/explainer.md`: ELI5, Simple, Non-Technical, and Technical
  explanations.
- `docs/github_start_here.md`: public GitHub entry point.
- `examples/live_use_cases/README.md`: runtime commands and visible outputs.
- `examples/api_clients/README.md`: JavaScript, Python, TypeScript, Java, and C#
  API examples.

The public docs are checked by:

```bash
PYTHONPATH=src python3 tools/github_docs_readiness_audit.py
PYTHONPATH=src python3 tools/docs_link_audit.py
```

## Verification Commands

Use these commands to audit the repository's public-facing claims:

```bash
PYTHONPATH=src python3 tools/github_docs_readiness_audit.py
PYTHONPATH=src python3 tools/docs_link_audit.py
PYTHONPATH=src python3 tools/ship_check.py --skip-tests --skip-regenerate
PYTHONPATH=src python3 -m unittest discover -s tests
```

If any command fails, the corresponding public claim should not be treated as
ready.
