# Production Readiness

## The Short Version

RDLLM 1.0 can be release-ready software without claiming that a particular
deployment is production-certified. Deployment approval is fail-closed:

1. the operator configures the required controls;
2. independent auditors sign current evidence with Ed25519 keys;
3. the operator supplies a separately managed trust store;
4. RDLLM verifies identity, deployment binding, expiry, evidence hashes, key
   permissions, and signatures;
5. direct settlement additionally requires a trusted payment-processor
   attestation.

Bundled profiles contain no trusted external attestations, so they correctly
report `production_grade_claim_allowed: false`. This is a safety result, not a
failed software release.

RDLLM is production-grade only when an operator can prove that attribution,
source grounding, rights enforcement, settlement controls, and public audit
surfaces are enforced in the live deployment. A green repository test suite is
necessary, but it is not enough by itself.

The production baseline is intended for individuals, companies, institutions,
governments, model providers, and public-sector deployments. Operators can run
RDLLM as an open-source attribution and royalty platform without having paying
customers, but they still need production controls before claiming direct creator
settlement, verified source reliance, or public-sector readiness.

## Baseline

Run the production-readiness gate:

```bash
PYTHONPATH=src python3 tools/production_readiness.py
PYTHONPATH=src python3 tools/production_profile_matrix.py
```

Run the production service smoke:

```bash
PYTHONPATH=src python3 tools/deployment_audit.py
PYTHONPATH=src python3 tools/service_smoke.py
PYTHONPATH=src python3 tools/service_load_smoke.py
PYTHONPATH=src python3 tools/provider_live_smoke.py
PYTHONPATH=src python3 tools/security_abuse_smoke.py
```

Evaluate only an operator profile:

```bash
PYTHONPATH=src python3 tools/production_readiness.py \
  --profile examples/production_readiness_profile.json \
  --profile-only
```

To evaluate external evidence, add the trust store explicitly:

```bash
PYTHONPATH=src python3 tools/production_readiness.py \
  --profile /etc/rdllm/production_readiness_profile.json \
  --trust-store /etc/rdllm/deployment_trust_store.json \
  --profile-only
```

The trust store follows
[`deployment_trust_store.schema.json`](schemas/deployment_trust_store.schema.json).
It must be controlled outside the deployment being evaluated. A profile cannot
trust its own signer.

Create an operator-specific profile and readiness report:

```bash
rdllm-operator-profile create \
  --template company \
  --operator-name "Acme RDLLM" \
  --security-contact security@example.com \
  --output artifacts/acme_production_profile.json \
  --write-report artifacts/acme_production_readiness_report.json
```

Validate an existing operator-controlled profile:

```bash
rdllm-operator-profile validate \
  --profile artifacts/acme_production_profile.json \
  --trust-store /etc/rdllm/deployment_trust_store.json \
  --write-report artifacts/acme_production_readiness_report.json
```

An independent auditor can create an evidence attestation, and the operator can
attach it without hand-editing JSON:

```bash
rdllm-deployment-attestation create \
  --profile artifacts/acme_production_profile.json \
  --attestation-type security_assessment \
  --issuer "Independent Security Auditor" \
  --key-id https://auditor.example/keys/2026-01 \
  --private-key /secure/auditor-ed25519-private.pem \
  --evidence audit/security-assessment.pdf \
  --evidence-uri https://auditor.example/reports/acme-2026 \
  --expires-at 2027-07-10T00:00:00Z \
  --output artifacts/security_assessment.attestation.json

rdllm-deployment-attestation attach \
  --profile artifacts/acme_production_profile.json \
  --attestation artifacts/security_assessment.attestation.json \
  --output artifacts/acme_production_profile.attested.json

rdllm-deployment-attestation verify \
  --profile artifacts/acme_production_profile.attested.json \
  --trust-store /etc/rdllm/deployment_trust_store.json
```

Repeat the create-and-attach step for each missing evidence type reported by the
verifier. The `payment_processor` type is required only when direct payout is
requested. Signing evidence does not execute a payment.

From a repository checkout, `PYTHONPATH=src python3 tools/operator_profile.py`
provides the same create and validate commands.
The command output validates against
`docs/schemas/operator_profile_verification.schema.json`.

Before production display traffic, run the installed launch gate against the
operator profile, service config, bootstrap manifest when present, and a saved
service attribution response:

```bash
rdllm-operator-launch-gate \
  --profile /etc/rdllm/production_readiness_profile.json \
  --trust-store /etc/rdllm/deployment_trust_store.json \
  --service-config /etc/rdllm/service_config.json \
  --service-root /etc/rdllm \
  --bootstrap-dir /etc/rdllm \
  --response /tmp/rdllm-service-response.json \
  --display-text /tmp/rdllm-copied-output.txt
```

The launch gate returns `blocked` unless the profile is ready, runtime service
readiness passes, the bootstrap verifies when supplied, and the saved response
footer plus copied/exported public answer text pass verification. A response is
display-ready only when grounding quality is `verified`,
`source_grounding_acceptance` is `passed`, and copied text verification is
`passed`; unattributed, warning, failed, policy-blocked, or registry-disputed
grounding blocks production display. Unsafe grounding must surface in
`audit_errors`. Internally consistent blocked responses may be verified for
audit, but `rdllm-operator-launch-gate` requires the saved response itself to be
`ready` before it allows traffic.
`--skip-response` is only for profile/config preflight and should not be used as
production display approval.
Runtime checks
require `RDLLM_SERVICE_TOKEN_SHA256` or the configured token-hash environment
variable to be set.

For backup and restore controls, create a recovery manifest over the operator
root and verify it after restore:

```bash
rdllm-operator-recovery create \
  --root /etc/rdllm \
  --output /var/lib/rdllm/recovery_manifest.json
rdllm-operator-recovery verify \
  --manifest /var/lib/rdllm/recovery_manifest.json \
  --root /etc/rdllm
```

For final production acceptance, aggregate launch, response-display, audit, and
recovery evidence into one report:

```bash
rdllm-operator-acceptance \
  --profile /etc/rdllm/production_readiness_profile.json \
  --service-config /etc/rdllm/service_config.json \
  --service-root /etc/rdllm \
  --bootstrap-dir /etc/rdllm \
  --response /tmp/rdllm-service-response.json \
  --display-text /tmp/rdllm-copied-output.txt \
  --audit-log /var/lib/rdllm/audit/service.jsonl \
  --recovery-manifest /var/lib/rdllm/recovery_manifest.json \
  --recovery-root /etc/rdllm \
  --output /var/lib/rdllm/operator_acceptance_report.json
```

Then verify the saved report hash and evidence bindings:

```bash
rdllm-operator-acceptance verify \
  --report /var/lib/rdllm/operator_acceptance_report.json
```

The acceptance report is production-ready only when the response-bound audit row
is clean: `latest_entry_status` must be `ready` and
`latest_audit_error_count` must be `0`. A hash-valid audit log with a blocked
latest row remains useful for audit, but it must not approve production handoff.

Cross-role release evidence must also pass the operator acceptance matrix:

```bash
rdllm-operator-acceptance-matrix \
  --output-dir /var/lib/rdllm/acceptance-matrix \
  --write-report /var/lib/rdllm/operator_acceptance_matrix.json
```

The matrix bootstraps and accepts `individual`, `company`, `institution`,
`government`, and `public_sector` roles. It fails if any role cannot produce a
ready acceptance report, a production-display-ready sourced response, matching
audit/recovery evidence, or the expected settlement/public-sector posture.

Operator templates are available under `examples/production_profiles/`:

- `individual_escrow_only.json`: local or self-hosted escrow-only operation.
- `company_instruction_only.json`: company deployment that emits remittance
  instructions without claiming direct payout execution.
- `institution_instruction_only.json`: regulated or federated institutional
  deployment.
- `government_escrow_only.json`: government deployment with public-sector
  controls and escrow-only settlement.
- `public_sector_processor_required.json`: public-sector configuration that
  requests direct settlement but remains blocked until a trusted external
  payment-processor attestation verifies.

`examples/production_readiness_profile.json` is retained as a compatibility
alias for the public-sector processor-attested profile used by the checked-in
readiness report.

Write a machine-readable report:

```bash
PYTHONPATH=src python3 tools/production_readiness.py \
  --write-report artifacts/repository_production_readiness_report.json
PYTHONPATH=src python3 tools/production_readiness.py \
  --verify-report artifacts/repository_production_readiness_report.json
rdllm-production-readiness-verify \
  --report artifacts/repository_production_readiness_report.json
PYTHONPATH=src python3 tools/production_readiness.py \
  --profile-only \
  --write-report artifacts/production_readiness_report.json
```

Profiles use `rdllm-production-readiness-profile/v1` and are described by
`docs/schemas/production_readiness_profile.schema.json`; the installed
`rdllm-operator-profile` command includes a packaged copy of the same templates
and profile schema. Reports use
`rdllm-production-readiness-report/v1` and are described by
`docs/schemas/production_readiness_report.schema.json`. The default repository
audit also checks docs, profile-matrix coverage, cross-role operator acceptance,
and proof-pack artifact prerequisites before allowing production claims. Its JSON
summary includes `acceptance_matrix_status`,
`acceptance_matrix_operator_template_count`, `acceptance_matrix_passed_count`,
and `acceptance_matrix_production_acceptance_allowed_count`. Repository-mode
output uses `rdllm-production-readiness-repository-report/v1`, validates against
`docs/schemas/production_readiness_repository_report.schema.json`, and includes
`repository_report_hash`. `--verify-report` verifies a saved repository-mode
report after handoff or publication; installed-package users can run
`rdllm-production-readiness-verify --report <report.json>` without a source
checkout.

## External Control Anchors

RDLLM maps its production controls to current public baselines:

- NIST AI RMF Generative AI Profile, NIST AI 600-1: AI risk management, trust,
  measurement, governance, and public-sector deployment review.
- NIST SSDF, SP 800-218: secure software development, vulnerability handling,
  provenance, release discipline, and maintenance.
- OWASP Top 10 for LLM Applications 2025: prompt injection, insecure output
  handling, training-data poisoning, supply-chain risk, sensitive information
  disclosure, excessive agency, and model denial of service.
- SLSA: supply-chain integrity, tamper resistance, build provenance, and release
  artifact confidence.

These anchors do not replace local law, procurement, payment, tax, accessibility,
records, or sector-specific duties. They define the minimum technical posture
RDLLM requires before a deployment may claim production-grade operation.

## Required Controls

Deployment identity:

- deployment ID, operator name, operator type, production environment, tenancy
  model, and deployment region policy are declared.
- supported operator types include individual, company, institution, government,
  model provider, public sector, and nonprofit.
- supported tenancy models include single tenant, multi-tenant, federated, and
  offline single-user deployments.

Public surfaces:

- well-known discovery manifest is published.
- provider attribution card is published.
- schema base URL is published.
- transparency log URL is published.
- security contact and license URL are published.

Runtime controls:

- authentication and rate limits are enabled.
- tenant isolation is enabled.
- provider routes use an allowlist.
- unknown provider states fail closed.
- service abuse cases fail closed for authorization, request limits, provider
  failures, and rate limits.
- source footer, response envelope, and streaming emission gates are required.
- raw prompts are not published.
- abuse monitoring is enabled.

Security controls:

- secrets are externalized from source and artifacts.
- CI and dependency update policy are required.
- supply-chain provenance is required.
- vulnerability reporting path exists.
- immutable audit logs, backup restore tests, incident response, privacy
  redaction, and audited admin actions are required.

Evidence controls:

- claim-source verification is required.
- source-selection rationale is required for every footer row.
- footer copy/export preservation is required.
- public proof pack and discovery manifest are required.
- third-party audit and negative fixture replay are required.
- model response states are normalized before display or settlement.

Governance controls:

- creator onboarding policy exists.
- rights registry is required.
- duplicate ownership claims have a dispute path.
- disputed or unattributed value goes to escrow.
- human review and appeals exist for conflicts.
- consent revocation process and public terms exist.

Settlement controls:

- settlement mode is `processor_attested`, `instruction_only`, or `escrow_only`.
- production-grade operation is allowed without paying customers when the
  deployment uses `instruction_only` or `escrow_only`.
- direct creator settlement is a separate claim and requires
  `processor_attested`, direct payout enabled, and external payment processor
  attestation.
- creator-pool rate is declared.
- raw payment accounts are never public.
- payout reconciliation, settlement report, and escrow rows are required.
- operators accept that tax, payment, sanctions, and legal compliance remain
  their responsibility.

Public-sector controls for government and public-sector operators:

- procurement evidence export is enabled.
- records-retention policy is defined.
- accessibility review is required.
- data-residency policy is defined.
- public-interest review policy is defined.

Operational SLOs:

- revocation propagation SLA is at most 24 hours.
- incident triage SLA is at most 24 hours.
- footer verification latency budget is at most 2000 ms.
- transparency publication SLA is at most 60 minutes.
- backup restore tests run at least every 90 days.

## Production Claim Rules

A deployment may claim RDLLM production-grade operation only when:

- `tools/ship_check.py` passes.
- `tools/production_readiness.py` passes.
- `tools/production_profile_matrix.py` passes across individual, company,
  institution, government, public-sector, escrow-only, instruction-only, and
  processor-attested profiles.
- `tools/operator_acceptance_matrix.py` passes across the same operator roles
  with full bootstrap, response, audit, recovery, launch-gate, and final
  acceptance evidence.
- `tools/production_readiness.py` reports `acceptance_matrix_status: passed` and
  `acceptance_matrix_passed_count: 5`.
- all production profile controls are ready.
- hosted discovery, public schemas, and proof artifacts are reachable.
- private prompts, source text, private reasoning, customer records, secrets,
  and raw payment account details are absent from public artifacts.
- live provider calls are covered by production invocation admission and runtime
  conformance receipts.
- the deployable service boundary passes health, readiness, auth, attribution,
  metrics, and audit-log smoke tests.
- Docker, Compose, and Kubernetes deployment templates pass secure-default
  audits.
- concurrent service requests preserve metrics and audit-log hash-chain
  continuity.
- provider-backed attribution routes pass a live mock OpenAI-compatible provider
  smoke before operators bind real provider API keys.
- security abuse smoke proves unauthorized requests, invalid economics, request
  limits, provider failure modes, and rate limiting block answer release.
- visible source footers carry verified source identity, claim support, rights
  state, settlement state, source-selection rationale, and matching non-escrow
  royalty-share coverage.

If any control fails, the deployment may still be used as a development or pilot
system, but it must not claim production-grade direct creator settlement,
government readiness, or verified source reliance.
