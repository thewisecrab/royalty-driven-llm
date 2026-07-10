# Operator Runbook

This runbook is for anyone deploying RDLLM as an open-source attribution and
royalty platform: an individual, company, institution, government, model
provider, marketplace, search product, RAG system, or agent platform.

## 1. Choose Deployment Profile

After installing RDLLM, run the operator doctor before creating production
assets:

```bash
rdllm-operator-doctor
```

This command uses packaged templates and sample proof artifacts to create a
temporary bootstrap directory, verify runtime readiness, generate a saved
attribution response, and verify the response footer and display surface. JSON
output validates against `docs/schemas/operator_doctor.schema.json`. From a
repository checkout, use `PYTHONPATH=src python3 tools/operator_doctor.py`.

For support, audit handoff, or incident triage, write a redacted diagnostic
bundle:

```bash
rdllm-operator-support-bundle --output rdllm-support-bundle.json
```

The bundle records package, environment, bootstrap, runtime, response-footer, and
display verification status plus public hashes and counts. Add
`--acceptance-report /var/lib/rdllm/operator_acceptance_report.json` for audit or
public handoff bundles that should verify the final production acceptance report.
It deliberately excludes raw prompts, generated outputs, raw source text,
evidence previews, rendered footers, bearer tokens, API keys, payment account
details, and exact local paths. The bundle validates against
`docs/schemas/operator_support_bundle.schema.json`. From a repository checkout, use
`PYTHONPATH=src python3 tools/operator_support_bundle.py`.

Before routing production traffic, run the launch gate against the deployment
profile, service config, optional bootstrap directory, and a saved attribution
response:

```bash
rdllm-operator-launch-gate \
  --profile /etc/rdllm/production_readiness_profile.json \
  --service-config /etc/rdllm/service_config.json \
  --service-root /etc/rdllm \
  --bootstrap-dir /etc/rdllm \
  --response /tmp/rdllm-service-response.json \
  --display-text /tmp/rdllm-copied-output.txt \
  --write-support-bundle /tmp/rdllm-support-bundle.json
```

The launch gate returns `ready` only when the profile is production-ready, the
service config is schema-valid, runtime readiness passes, the bootstrap
verification passes when supplied, and the saved response footer plus copied
public answer text verify. Use `--skip-response` only for a preflight check that
must not be treated as approval for production display traffic. Ensure the
service token hash environment variable is set before runtime checks. From a
repository checkout, use `PYTHONPATH=src python3 tools/operator_launch_gate.py`.
The JSON report validates against `docs/schemas/operator_launch_gate.schema.json`.

Create a complete operator bootstrap directory when starting a new deployment:

```bash
rdllm-operator-bootstrap \
  --output-dir /etc/rdllm \
  --operator-template company \
  --operator-name "Acme RDLLM" \
  --security-contact security@example.com \
  --corpus /srv/rdllm/corpus.json
rdllm-operator-bootstrap --verify-dir /etc/rdllm
```

The command writes `production_readiness_profile.json`,
`production_readiness_report.json`, `service_config.json`,
`operator_bootstrap_manifest.json`, and a local `README.md` with validation and
start commands. The verification command replays the manifest schema, profile
report, service config, included files, and optional runtime checks. The
verification output validates against
`docs/schemas/operator_bootstrap_verification.schema.json`.

For a local first-run self-test, add `--include-sample-corpus` and
`--include-reference-artifacts`. This writes the packaged sample corpus and
reference proof artifacts into the bootstrap directory so `/readyz` can be tested
before replacing them with operator-controlled production assets. Add
`--check-runtime` to `rdllm-operator-bootstrap --verify-dir ...` when the token
hash environment variable is set and the corpus/proof artifact files should be
confirmed on disk.

Generate an operator-specific profile from the closest template:

```bash
rdllm-operator-profile create \
  --template company \
  --operator-name "Acme RDLLM" \
  --security-contact security@example.com \
  --output path/to/production_readiness_profile.json \
  --write-report path/to/production_readiness_report.json
```

From a repository checkout, use
`PYTHONPATH=src python3 tools/operator_profile.py create` with the same flags.
The profile command output validates against
`docs/schemas/operator_profile_verification.schema.json`.

Use `--template individual`, `company`, `institution`, `government`, or
`public_sector`. The installed command uses packaged profile templates and the
packaged `production_readiness_profile` schema, evaluates all
production-readiness controls, verifies the report hash, and exits nonzero unless
the generated profile is ready.

If you need to edit a profile manually, choose the closest template:

- `examples/production_profiles/individual_escrow_only.json`
- `examples/production_profiles/company_instruction_only.json`
- `examples/production_profiles/institution_instruction_only.json`
- `examples/production_profiles/government_escrow_only.json`
- `examples/production_profiles/public_sector_processor_required.json`

`examples/production_readiness_profile.json` remains a compatibility alias for
the processor-attested public-sector profile.

Then copy it to an operator-controlled path and set:

- `deployment.deployment_id`
- `deployment.operator_name`
- `deployment.operator_type`
- `deployment.environment`
- `deployment.tenancy_model`
- `deployment.deployment_region_policy`

Validate the final operator-controlled profile:

```bash
rdllm-operator-profile validate \
  --profile path/to/production_readiness_profile.json \
  --write-report path/to/production_readiness_report.json
```

From a repository checkout, also run the template matrix and source-tree
readiness gate:

```bash
PYTHONPATH=src python3 tools/production_profile_matrix.py
PYTHONPATH=src python3 tools/production_readiness.py \
  --profile path/to/production_readiness_profile.json \
  --profile-only
```

Do not enable production traffic until the profile reports `ready`.

## 2. Prepare Runtime Boundary

Generate and validate an operator-controlled service config:

```bash
rdllm-service-config create \
  --template default \
  --corpus /srv/rdllm/corpus.json \
  --audit-log-path /var/lib/rdllm/audit/service.jsonl \
  --artifact-dir /srv/rdllm/artifacts \
  --output /etc/rdllm/service_config.json
rdllm-service-config validate --config /etc/rdllm/service_config.json
```

The validation output validates against
`docs/schemas/service_config_verification.schema.json`.

From a repository checkout, use
`PYTHONPATH=src python3 tools/service_config.py` with the same flags.

Verify every saved attribution response before a client renders or exports its
source footer:

```bash
rdllm-service-response-verify \
  --response path/to/response.json \
  --display-text path/to/copied-output.txt
rdllm-source-footer-verify \
  --footer path/to/source-footer.json \
  --display-text path/to/copied-output.txt
```

From a repository checkout, use
`PYTHONPATH=src python3 tools/service_response_verify.py --response path/to/response.json`.
Clients should render `display.rendered_text` only after verification passes.
The verifier recomputes that display surface from the raw answer plus
`source_footer.rendered_text` and checks `summary.display_hash`, so a response
with a detached, edited, or omitted footer fails before user display. It also
checks source-row and claim-row semantics: supported claim counts, minimum
support scores, evidence span hashes, and evidence previews must agree before a
footer can be treated as grounded. Every visible source row must also carry a
deterministic `rdllm://verify/source-footer/...` handle so copied or exported
answers retain a public verification pointer for the exact source row.
Supplying `--display-text` verifies an independently copied or exported answer
against the bound display text and fails if the footer or verification handles
were stripped.
Use `rdllm-source-footer-verify` for public footer artifacts that can be shared
without the full private response; it verifies footer row hashes, claim evidence
span hashes, deterministic source-row handles, footer hash, and copied-text
footer preservation.
`production_display_ready` is true only when the response verifier passes, the
response status is `ready`, and grounding is safe for display. The verifier also
publishes `source_grounding_acceptance`, which must be `passed` for production
display. It requires at least one visible verified source row, at least one
supported claim, no unsupported claim rows, minimum claim support of `0.75`,
matching non-escrow royalty-share coverage for every visible source,
verification handles for every source row, usage metrics and source-usage metric
profile/scope/method provenance for every visible source row, visible
URI/verify/hash locators for every source row, visible source identity binding to
event source-reference metadata for every source row,
visible evidence rows for every supported claim, claim-source closure between
each supported claim and its visible source row, evidence-force warrant
calibration for every supported claim, visible source-disagreement disclosure
for every supported claim, answer-claim coverage between displayed answer text
and footer claim rows, absence of unverified
model-internal reliance claims, closed consumed/credited attribution gap
coverage, temporal freshness metadata whenever the answer makes
current/latest/recent/as-of claims, and a rendered answer that includes the bound
source footer. It also requires unresolved inline citation-shaped markers and
unverified answer-link URIs in the answer text to be absent; answer markers must
resolve to verified source-footer source or claim labels. Numeric markers
resolve as source aliases, so `[1]` and `[Source: 1]` require verified source
row `S1`; numeric groups and ranges must fully resolve, while bracketed years
such as `[2026]` are ignored as non-citation text. Markdown links and bare
`scheme://...` URIs must resolve to verified footer `source_uri` values. The
verifier reports detected, resolved, and unresolved marker and answer-link URI
lists, answer-claim coverage counts, and model-reliance claim markers for
incident triage. The verification output validates against
`docs/schemas/service_response_verification.schema.json`; public footer
verification validates against
`docs/schemas/service_source_footer_verification.schema.json`.

Verify service audit-log continuity after attribution traffic:

```bash
rdllm-service-audit-verify \
  --audit-log /var/lib/rdllm/audit/service.jsonl
```

This verifier rejects malformed JSONL, schema drift, broken previous-entry
hashes, entry-hash mismatches, invalid timestamps, and optional expected-count
mismatches. It also rejects `ready` audit entries with audit errors and
`blocked` audit entries with no audit errors, so a hash-valid row cannot imply a
clean production answer when the status evidence disagrees. From a repository checkout, use
`PYTHONPATH=src python3 tools/service_audit_verify.py`.
Each JSONL entry validates against `docs/schemas/service_audit_entry.schema.json`,
and the verification output validates against
`docs/schemas/service_audit_verification.schema.json`.

Every production request should enter through one controlled runtime boundary:

- authenticated API or application session
- tenant scope
- provider route allowlist
- model alias allowlist
- source registry version
- rights registry version
- response-state normalization
- source footer requirement
- settlement meter requirement
- trace ID and audit log ID

Unknown, refused, blocked, filtered, truncated, tool-only, errored, or
unverified provider states must fail closed. The output can be shown as an
ungrounded answer or error, but it must not carry a verified source footer or
direct creator settlement decision.

## 3. Bind Provider Routes

For each provider route:

- map request, response, source, safety, usage, streaming, and telemetry fields.
- replay the provider conformance runner fixtures.
- publish the provider route in the compatibility matrix or an operator-local
  extension.
- bind native usage meters to RDLLM settlement meters.
- bind native citation/source annotations to RDLLM verified footer rows.
- record failure behavior for refusal, moderation, truncation, missing usage,
  unavailable source, stale source, and unsupported claim cases.

Run:

```bash
PYTHONPATH=src python3 tools/provider_family_audit.py
PYTHONPATH=src python3 tools/provider_matrix.py --check
```

## 4. Configure Rights Registry

The rights registry must track:

- creator or owner identity
- work identity and content hash commitments
- allowed AI uses
- attribution duties
- quote or snippet policy
- minimum creator-pool terms
- revocation state
- duplicate claim status
- dispute or appeal status

Revocations must propagate across retrieval indexes, cached contexts,
persistent memory, private reasoning stores, post-training signal stores,
source footers, exchange manifests, downstream ledgers, and settlement queues.

## 5. Configure Source Footer Enforcement

For every displayed footer row:

- source identity must resolve.
- source material must be available or explicitly marked unavailable.
- claim support must be verified.
- source-selection rationale must be present.
- rights state must permit the use.
- settlement state must be payable, escrowed, or held with a reason.
- copy/export preservation must keep the source footer attached to the answer.

Footer rows that cannot meet this bar should be downgraded to warning, escrow,
or omitted states. They should not be shown as verified support.

Runtime responses fail closed for non-display-safe grounding. `ready` now means
the grounding verdict is `verified` and the grounded-source acceptance profile
passes. Unattributed, warning, failed, policy-blocked, and registry-disputed
verdicts return `blocked`, include a `grounding_quality:` audit error when
grounding is unsafe, and render unsupported claim hashes or escrow state before
any customer display or copy/export. `rdllm-service-response-verify` can still
verify such a blocked response as internally consistent, but the operator launch
gate rejects it for production traffic unless `production_display_ready` is true.

## 6. Configure Settlement

RDLLM can operate in three settlement modes:

- `processor_attested`: direct payout only after an external payment or escrow
  processor attests execution.
- `instruction_only`: RDLLM emits remittance instructions and hash commitments,
  while the operator executes payment outside RDLLM.
- `escrow_only`: RDLLM records payable and disputed value without direct payout.

`instruction_only` and `escrow_only` can be production-grade without claiming
that money moved. Direct creator settlement is allowed only for
`processor_attested` profiles with direct payout enabled and external processor
attestation.

For direct payout:

- raw payment accounts stay outside public artifacts.
- payment account references are hash commitments.
- processor records are reconciled against remittance rows.
- duplicate processor records fail verification.
- unresolved attribution, rights, or ownership conflicts remain in escrow.

Operators remain responsible for tax, sanctions, payment licensing, consumer
protection, procurement, and sector-specific legal requirements.

## 7. Publish Public Surfaces

Publish:

- `/.well-known/rdllm.json`
- provider attribution card
- certification report
- discovery manifest
- proof dependency graph
- public schemas
- production-readiness report if the operator chooses to publish it
- security contact
- license and terms

Run:

```bash
PYTHONPATH=src python3 tools/hosting_export.py --write
PYTHONPATH=src python3 tools/hosted_surface_audit.py
PYTHONPATH=src python3 tools/public_surface_privacy_audit.py
```

## 8. Incident Response

Create an incident when any of these occur:

- source footer is missing, fabricated, stale, or weakly supportive.
- private prompt, private source text, private reasoning, secret, customer
  record, or raw payment account appears in a public surface.
- provider route bypasses admission, conformance, telemetry, or settlement
  gates.
- revocation does not propagate within SLA.
- creator dispute, duplicate ownership claim, or appeal affects settlement.
- payment processor attestation does not reconcile with remittance rows.

Immediate actions:

- stop verified source-footer claims for affected routes.
- hold direct settlement for affected works and tenants.
- preserve logs and proof artifacts.
- publish correction or reliance-revocation artifacts when public users may
  have relied on the affected proof.
- rotate affected keys or secrets.
- replay negative fixtures before reopening the route.

## 9. Backup and Recovery

backup scope:

- rights registry
- source registry
- settlement ledger
- audit logs
- transparency logs
- public proof artifacts
- operator deployment profile

Run restore tests at least every 90 days. Recovery is acceptable only when the
restored system preserves ledger hashes, public artifact hashes, revocation
state, settlement holds, and dispute state.

Create a recovery manifest before backup and verify it after restore:

```bash
rdllm-operator-recovery create \
  --root /etc/rdllm \
  --output /var/lib/rdllm/recovery_manifest.json
rdllm-operator-recovery verify \
  --manifest /var/lib/rdllm/recovery_manifest.json \
  --root /etc/rdllm
```

The manifest and verification output validate against
`docs/schemas/operator_recovery_manifest.schema.json` and
`docs/schemas/operator_recovery_verification.schema.json`.

The default recovery scope covers the generated deployment profile, readiness
report, service config, bootstrap manifest, local README, proof artifacts,
sample or operator corpus files, and runtime files under the operator root. Use
`--include` and `--include-dir` for operator-controlled rights registries,
source registries, settlement ledgers, transparency logs, and off-root audit-log
exports staged into the recovery root.

Create the final operator acceptance report before production traffic, customer
handoff, or audit handoff:

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

Verify the saved report before handoff or publication:

```bash
rdllm-operator-acceptance verify \
  --report /var/lib/rdllm/operator_acceptance_report.json
```

The acceptance-verification JSON output validates against
`docs/schemas/operator_acceptance_verification.schema.json`.

Acceptance returns `ready` only when launch readiness, response display
verification, audit-log continuity, audit-to-response binding, and recovery
verification all pass. By default the latest audit event must match the saved
response under test; use `--allow-nonlatest-response-event` only for an existing
deployment where later verified traffic has already been appended. Verification
recomputes the report hash and checks that response display hashes, audit event
hashes, and recovery counts still match the report evidence. Final acceptance
proves one operator root and requires the response-bound latest audit row to
have `status: ready` and `audit_error_count: 0`; a hash-valid but blocked audit
row is audit evidence, not production handoff evidence.

For open-source release evidence or institutional evaluation, also run the
operator acceptance matrix:

```bash
rdllm-operator-acceptance-matrix \
  --output-dir /var/lib/rdllm/acceptance-matrix \
  --write-report /var/lib/rdllm/operator_acceptance_matrix.json
```

The matrix report validates against
`docs/schemas/operator_acceptance_matrix.schema.json` and must be `passed`
before claiming that the release path works for individuals, companies,
institutions, governments, and public-sector operators.

For support or audit handoff, include this saved report in the redacted support
bundle with `rdllm-operator-support-bundle --acceptance-report ...`.

## 10. Upgrade Procedure

For every upgrade:

- run full tests and `tools/ship_check.py`.
- run `tools/production_readiness.py` against the operator profile.
- run `tools/deployment_audit.py` against container and Kubernetes templates.
- run `tools/service_smoke.py` against the service boundary.
- run `tools/service_load_smoke.py` against concurrent attribution requests.
- run `tools/provider_live_smoke.py` against the guarded provider-call path.
- run `tools/security_abuse_smoke.py` against fail-closed abuse cases.
- regenerate reference artifacts if artifact-producing code changed.
- run public privacy audit.
- replay provider conformance and negative fixtures.
- compare new proof hashes against the previous release.
- publish release notes with known limitations.

## 11. Government and Institution Use

Government and institution deployments should additionally require:

- procurement evidence export.
- records-retention policy.
- accessibility review.
- data-residency policy.
- public-interest review policy.
- named security contact.
- auditable administrator actions.
- documented appeal and dispute process.

These controls are part of the production-readiness profile because the platform
must be usable by public-sector operators without relying on private vendor
assertions.
