# Release Checklist

Use this checklist before tagging a GitHub release or deploying the hosted docs.

## Required Evidence

- `artifacts/certification_report.json` has summary status `passed`.
- The highest certification level is the current top level.
- `artifacts/proof_dependency_graph.json` is ready and binds all public
  artifacts.
- `artifacts/discovery_manifest.json` is ready and includes well-known paths for
  public surfaces.
- `artifacts/provider_attribution_card.json` discloses supported evidence
  channels and limitations.
- JSON artifacts validate against their schemas, including every public
  artifact listed in `artifacts/discovery_manifest.json`.
- The package builds from `pyproject.toml`, installs into an isolated virtual
  environment, the installed `rdllm` console script can run the bundled demo,
  `rdllm-operator-acceptance` can produce a final operator acceptance report,
  `rdllm-operator-doctor` can complete the installed self-test,
  `rdllm-operator-bootstrap` can create a complete operator bootstrap directory,
  `rdllm-operator-profile` can generate a ready operator profile from packaged
  templates, `rdllm-operator-recovery` can create and verify a recovery
  manifest, `rdllm-service-config` can generate a schema-valid service config
  from packaged templates, `rdllm-service-response-verify` can verify a saved
  attribution response, `rdllm-source-footer-verify` can verify a public source
  footer and copied output, `rdllm-service-audit-verify` can verify a hash-chained
  audit log, `rdllm-operator-launch-gate` can make a fail-closed go-live
  decision, and `rdllm-operator-support-bundle` can produce a redacted diagnostic
  bundle after wheel installation.
- `tools/package_metadata_audit.py` passes, proving public package metadata,
  console scripts, URLs, keywords, license, and production/stable classifier stay
  aligned with the production-readiness claim.
- The full test suite passes.
- `tools/e2e_smoke.py` passes, proving the bundled CLI demo, external-output
  attribution, source footer, signed receipt, public receipt, and L186 artifact
  readiness work together from the repository checkout.
- The hosted docs entry point exists at `docs/index.html`.
- `docs/adopter_quickstart.md` gives individuals, companies, institutions,
  governments, and public-sector operators a role-specific path from installed
  package self-test through launch gate, acceptance report, and redacted support
  bundle.
- `tools/adopter_quickstart_audit.py` passes, proving the quickstart remains
  rootless, copyable, role-complete, and runtime-probed through source-grounded
  attribution plus hash-chained service audit verification.
- The hosted well-known discovery entry point exists at
  `docs/.well-known/rdllm.json`, and every public artifact path advertised by
  `artifacts/discovery_manifest.json` is exported under `docs/.well-known/rdllm/`.
- Hosted discovery resolves every advertised artifact and schema path, and hosted
  artifact hashes match the discovery catalog.
- Hosted public artifacts and schema mirrors pass the privacy audit, proving they
  do not expose prompts, raw source text, private reasoning, secrets, customer
  records, payment details, or payout account data.
- Local Markdown and HTML documentation links resolve before static hosting.
- `tools/github_readiness.py` reports `ready` so GitHub workflows, Pages
  routing, source-package pruning, artifact sizes, and required public surfaces
  are checked before release.
- `tools/production_readiness.py` reports `ready` so production operator docs,
  deployment profile controls, runtime gates, security posture, governance,
  settlement, public-sector controls, and required proof artifacts are checked
  before production claims. Its repository-mode report must also include
  `acceptance_matrix_status: passed`, proving every supported operator role can
  bootstrap, emit a grounded response, bind audit/recovery evidence, and reach
  final acceptance. The report validates against
  `docs/schemas/production_readiness_repository_report.schema.json` and includes
  `repository_report_hash`.
- `tools/operator_profile.py validate` passes against a production profile and
  package smoke proves `rdllm-operator-profile` works after wheel installation,
  including its packaged verification schema, so operators can generate and
  verify deployment-specific readiness reports before release.
- `tools/source_footer_verify.py` passes against a standalone public source footer
  and copied output; package smoke proves `rdllm-source-footer-verify` works after
  wheel installation, so recipients can verify footer rows, hashes, deterministic
  handles, and copy/export preservation without receiving the full private
  response artifact.
- `tools/operator_doctor.py` passes and package smoke proves
  `rdllm-operator-doctor` works after wheel installation, including schema
  loading, so a new operator can prove packaged templates, bootstrap, runtime
  readiness, and response-footer and display verification without a repository
  checkout.
- `tools/operator_launch_gate.py` returns `ready` for a runtime-ready bootstrap,
  service config, profile, saved attribution response, and support-bundle output;
  package smoke proves `rdllm-operator-launch-gate` and its packaged schema load
  after wheel installation, so operators have one fail-closed go-live command
  and a verifiable JSON report before production display traffic.
- `tools/operator_acceptance.py` returns `ready` for launch readiness, saved
  response display verification, audit-log continuity, audit-to-response
  binding to a clean ready audit row, and recovery verification; package smoke proves
  `rdllm-operator-acceptance` can also verify the saved acceptance report and
  load its packaged verification schema after wheel installation, so operators
  can publish one final deployment acceptance report with a schema-valid
  verification result before production handoff.
- `tools/operator_acceptance_matrix.py` returns `passed` only when the installed
  workflow bootstraps, verifies, accepts, and role-checks individual, company,
  institution, government, and public-sector operator roots, so release evidence
  proves RDLLM is usable beyond one happy-path organization.
- `tools/operator_recovery.py` creates and verifies a recovery manifest for an
  operator root; package smoke proves `rdllm-operator-recovery` and its packaged
  schemas work after wheel installation, so operators can prove backup/restore
  files still match before incident, audit, or settlement recovery.
- `tools/operator_support_bundle.py` writes a redacted diagnostic bundle and
  package smoke proves `rdllm-operator-support-bundle` works after wheel
  installation, including schema loading and verification of a saved final
  acceptance report, so operators can escalate support or audit evidence without
  disclosing prompts, generated outputs, raw source text, tokens, API keys,
  payment account details, or exact local paths.
- `tools/operator_bootstrap.py` creates and verifies a ready bootstrap directory
  so a new operator can generate profile, report, service config, manifest, and
  local instructions in one command; package smoke also proves the installed
  command can load its packaged verification schema, export bundled sample
  corpus, and verify reference proof artifacts.
- `tools/service_config.py validate` passes against a service config and package
  smoke proves `rdllm-service-config` works after wheel installation and can
  load its packaged verification schema, so operators can generate and validate
  service configs without a repository checkout.
- `tools/service_response_verify.py` passes against a saved service response and
  package smoke proves `rdllm-service-response-verify` works after wheel
  installation and can load the packaged verification schema, so clients can
  verify the rendered answer, copied source footer, source-row/claim-row
  semantics, evidence span hashes, unresolved inline citation-marker rejection,
  marker-list diagnostics, and `display_hash` without running the service.
- `tools/service_audit_verify.py` passes against a hash-chained service audit log
  and rejects missing row fields, status/error-count contradictions, and
  footer/display binding gaps. Package smoke proves `rdllm-service-audit-verify`
  works after wheel installation and can load the packaged audit-entry and
  verification schemas, so operators can verify runtime audit continuity and
  clean/blocked audit semantics before incident, audit, or settlement review.
- `tools/production_profile_matrix.py` passes so individual, company,
  institution, government, public-sector, escrow-only, instruction-only, and
  processor-attested profile templates stay production-ready.
- `tools/service_smoke.py` passes so the installable HTTP service starts,
  reports readiness, rejects unauthenticated protected calls, attributes an
  answer, exposes metrics, and writes a hash-chained audit log.
- `tools/service_load_smoke.py` passes so concurrent attribution requests
  preserve readiness, metrics, and audit-log hash-chain continuity.
- `tools/provider_live_smoke.py` passes so the guarded provider-call path can
  invoke an OpenAI-compatible provider, hash the provider response, and attribute
  the generated answer before release.
- `tools/security_abuse_smoke.py` passes so protected routes fail closed for
  unauthorized access, invalid economics, request limits, provider failures, and
  rate limiting before release.
- `tools/deployment_audit.py` passes so Docker, Compose, Kubernetes, environment,
  and container service-config templates preserve secure deployment defaults.
- `tools/provider_family_audit.py` passes so provider-family names across
  runtime, adoption, binding, discovery, conformance, and production-admission
  layers map to the canonical provider taxonomy.
- README, contributing, security, license, and changelog files exist.

## Commands

```bash
PYTHONPATH=src python tools/github_readiness.py
PYTHONPATH=src python tools/artifact_schema_audit.py
PYTHONPATH=src python tools/hosting_export.py --write
PYTHONPATH=src python tools/hosting_export.py --check
PYTHONPATH=src python tools/hosted_surface_audit.py
PYTHONPATH=src python tools/public_surface_privacy_audit.py
PYTHONPATH=src python tools/docs_link_audit.py
PYTHONPATH=src python tools/adopter_quickstart_audit.py
PYTHONPATH=src python tools/package_metadata_audit.py
PYTHONPATH=src python tools/package_smoke.py
PYTHONPATH=src python tools/production_readiness.py \
  --write-report /tmp/rdllm-repository-readiness.json
PYTHONPATH=src python tools/production_readiness.py \
  --verify-report /tmp/rdllm-repository-readiness.json
rdllm-production-readiness-verify \
  --report /tmp/rdllm-repository-readiness.json
PYTHONPATH=src python tools/operator_doctor.py
PYTHONPATH=src python tools/operator_support_bundle.py \
  --output /tmp/rdllm-support-bundle.json
PYTHONPATH=src python tools/operator_bootstrap.py \
  --output-dir /tmp/rdllm-operator-bootstrap \
  --operator-template company \
  --operator-name "Release RDLLM" \
  --security-contact security@example.com \
  --include-sample-corpus \
  --include-reference-artifacts
PYTHONPATH=src python tools/operator_bootstrap.py \
  --verify-dir /tmp/rdllm-operator-bootstrap
# Replace these response/display paths with artifacts from the deployment under
# test, and ensure RDLLM_SERVICE_TOKEN_SHA256 is set.
PYTHONPATH=src python tools/operator_launch_gate.py \
  --profile /tmp/rdllm-operator-bootstrap/production_readiness_profile.json \
  --service-config /tmp/rdllm-operator-bootstrap/service_config.json \
  --service-root /tmp/rdllm-operator-bootstrap \
  --bootstrap-dir /tmp/rdllm-operator-bootstrap \
  --response /tmp/rdllm-service-response.json \
  --display-text /tmp/rdllm-copied-output.txt
PYTHONPATH=src python tools/operator_recovery.py create \
  --root /tmp/rdllm-operator-bootstrap \
  --output /tmp/rdllm-recovery-manifest.json
PYTHONPATH=src python tools/operator_recovery.py verify \
  --manifest /tmp/rdllm-recovery-manifest.json \
  --root /tmp/rdllm-operator-bootstrap
PYTHONPATH=src python tools/operator_profile.py validate \
  --profile examples/production_readiness_profile.json
PYTHONPATH=src python tools/service_config.py validate \
  --config examples/service_config.json
# Replace this path with the service audit log from the deployment under test.
PYTHONPATH=src python tools/service_audit_verify.py \
  --audit-log /tmp/rdllm-service-audit.jsonl
PYTHONPATH=src python tools/operator_acceptance.py \
  --profile /tmp/rdllm-operator-bootstrap/production_readiness_profile.json \
  --service-config /tmp/rdllm-operator-bootstrap/service_config.json \
  --service-root /tmp/rdllm-operator-bootstrap \
  --bootstrap-dir /tmp/rdllm-operator-bootstrap \
  --response /tmp/rdllm-service-response.json \
  --display-text /tmp/rdllm-copied-output.txt \
  --audit-log /tmp/rdllm-service-audit.jsonl \
  --recovery-manifest /tmp/rdllm-recovery-manifest.json \
  --recovery-root /tmp/rdllm-operator-bootstrap \
  --output /tmp/rdllm-operator-acceptance.json
PYTHONPATH=src python tools/operator_acceptance.py verify \
  --report /tmp/rdllm-operator-acceptance.json
PYTHONPATH=src python tools/operator_support_bundle.py \
  --skip-doctor \
  --acceptance-report /tmp/rdllm-operator-acceptance.json \
  --output /tmp/rdllm-acceptance-support-bundle.json
PYTHONPATH=src python tools/operator_acceptance_matrix.py \
  --output-dir /tmp/rdllm-acceptance-matrix \
  --write-report /tmp/rdllm-operator-acceptance-matrix.json
PYTHONPATH=src python tools/production_profile_matrix.py
PYTHONPATH=src python tools/deployment_audit.py
PYTHONPATH=src python tools/service_smoke.py
PYTHONPATH=src python tools/service_load_smoke.py
PYTHONPATH=src python tools/provider_live_smoke.py
PYTHONPATH=src python tools/security_abuse_smoke.py
PYTHONPATH=src python tools/provider_family_audit.py
PYTHONPATH=src python tools/e2e_smoke.py
PYTHONPATH=src python tools/provider_matrix.py --write
PYTHONPATH=src python tools/regenerate_reference_artifacts.py
PYTHONPATH=src python tools/ship_check.py
```

Optional package build:

```bash
python -m pip install -U build
python -m build
```

## Release Notes

Each release should state:

- highest RDLLM certification level
- artifact hash for `certification_report.json`
- artifact hash for `proof_dependency_graph.json`
- provider families covered by the binding matrix
- new or changed public schemas
- production-readiness profile status
- known limitations
- references added or updated

## Current Known Limitation

The repository is an open-source production baseline and proof framework. Live
provider API keys, production billing exports, legal payment rails, and private
customer data are intentionally not included. Production operators must bind
their own provider telemetry, invoices, rights registries, payout rails, tenant
identity, incident process, and jurisdiction-specific compliance controls
through the published adapter, operator profile, and verification contracts.
