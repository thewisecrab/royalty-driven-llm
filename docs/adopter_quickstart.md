# Adopter Quickstart

Use this path when evaluating RDLLM as an open-source production baseline. The
same sequence works for individuals, companies, institutions, governments, model
providers, and public-sector operators; the role changes the production profile
and settlement claim the deployment is allowed to make.

## Pick A Role

| Operator role | Template | Settlement posture | Production claim |
| --- | --- | --- | --- |
| Individual | `individual` | Escrow-only | Local or self-hosted attribution with verified source footers and no direct payout claim. |
| Company | `company` | Instruction-only | Attribution, source-footer, and remittance-instruction generation without claiming payment execution. |
| Institution | `institution` | Instruction-only | Regulated or federated attribution with institutional governance and no direct payout execution claim. |
| Government | `government` | Escrow-only | Public-sector attribution with escrow-only settlement and public-sector controls. |
| Public sector with processor attestation | `public_sector` | Processor-attested | Direct settlement only when the configured external processor evidence is present and verified. |

## Install And Self-Test

Install from a source checkout or built wheel, then run the installed doctor:

```bash
python -m pip install .
rdllm-operator-doctor
```

`rdllm-operator-doctor` proves the package can load its embedded schemas,
templates, sample corpus, bootstrap path, runtime readiness checks, and
response-footer verification without relying on repository-only files.

Set user-owned paths for a rootless first run:

```bash
export RDLLM_HOME="${RDLLM_HOME:-$PWD/.rdllm/operator}"
export RDLLM_STATE="${RDLLM_STATE:-$PWD/.rdllm/state}"
export RDLLM_AUDIT_LOG="${RDLLM_AUDIT_LOG:-$RDLLM_STATE/audit/service.jsonl}"
mkdir -p "$RDLLM_HOME" "$RDLLM_STATE" "$(dirname "$RDLLM_AUDIT_LOG")"
```

## Bootstrap An Operator Root

Create an operator-controlled directory. Choose the `--operator-template` from
the role table.

```bash
rdllm-operator-bootstrap \
  --output-dir "$RDLLM_HOME" \
  --operator-template company \
  --operator-name "Acme RDLLM" \
  --security-contact security@example.com \
  --audit-log-path "$RDLLM_AUDIT_LOG" \
  --include-sample-corpus \
  --include-reference-artifacts
```

The bootstrap writes `production_readiness_profile.json`,
`production_readiness_report.json`, `service_config.json`, sample runtime data,
reference proof artifacts, `operator_bootstrap_manifest.json`, and local start
commands. Verify the directory before using it:

```bash
rdllm-operator-bootstrap --verify-dir "$RDLLM_HOME"
```

The verification output validates against
`schemas/operator_bootstrap_verification.schema.json`.

## Configure Runtime Secrets

The default service template expects a bearer-token hash, not a plaintext token.
Put the SHA-256 token hash in the configured environment variable before runtime
checks or service startup:

```bash
export RDLLM_SERVICE_TOKEN="${RDLLM_SERVICE_TOKEN:-rdllm-local-dev-token}"
export RDLLM_SERVICE_TOKEN_SHA256="$(python - <<'PY'
import hashlib
import os
print(hashlib.sha256(os.environ["RDLLM_SERVICE_TOKEN"].encode()).hexdigest())
PY
)"
```

Provider-backed routes also require provider API keys through each configured
`api_key_env`. Do not put plaintext provider keys, payment account details, raw
prompts, or raw source text into public artifacts.

## Start The Service

Start the installed service with the generated config:

```bash
rdllm-service --config "$RDLLM_HOME/service_config.json"
```

Before production traffic, save one attribution response from the deployment
under test. The response must include `source_footer`, `display`, and a clean
`ready` status:

```bash
curl -sS \
  -H "Authorization: Bearer $RDLLM_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What should royalty-bearing AI answers expose?",
    "output": "Every royalty-bearing AI answer should expose grounded sources, claim evidence, and payout or escrow state.",
    "gross_revenue": "1.00"
  }' \
  http://127.0.0.1:8765/v1/attribute > /tmp/rdllm-service-response.json
```

Verify the saved response before treating it as displayable:

```bash
python - <<'PY'
import json
from pathlib import Path
response = json.loads(Path("/tmp/rdllm-service-response.json").read_text())
Path("/tmp/rdllm-copied-output.txt").write_text(
    response["display"]["rendered_text"],
    encoding="utf-8",
)
Path("/tmp/rdllm-source-footer.json").write_text(
    json.dumps(response["source_footer"]),
    encoding="utf-8",
)
PY
rdllm-service-response-verify \
  --response /tmp/rdllm-service-response.json \
  --display-text /tmp/rdllm-copied-output.txt
rdllm-source-footer-verify \
  --footer /tmp/rdllm-source-footer.json \
  --display-text /tmp/rdllm-copied-output.txt
```

`production_display_ready` must be `true` before any user-facing answer can be
shown as grounded or royalty-bearing. The verifier also emits
`source_grounding_acceptance`; it must be `passed` before a response can claim a
grounded footer because it checks visible source rows, claim support, support
score floor, royalty-share coverage, source-row verification handles, and
answer-plus-footer display binding. It also fails unresolved inline
citation-shaped answer markers, so labels in the answer cannot imply support
unless they resolve to verified footer rows. Numeric markers resolve as source
aliases, so `[1]` and `[Source: 1]` require verified source row `S1`; numeric
groups and ranges must fully resolve, while bracketed years such as `[2026]` are
ignored as non-citation text. It also fails Markdown links or bare
`scheme://...` URIs in the answer unless they match verified footer `source_uri`
values. The verifier reports detected, resolved, and unresolved marker and
answer-link URI lists for debugging. Rendered source rows also expose
`support`, `text_match`, `weight`, and `payout`, giving users and auditors a
visible source-usage and allocation explanation rather than a bare citation
list. They also expose the source-usage metric profile, scope, and per-metric
method identifiers, so the numbers can be audited as observable
support/allocation outputs rather than implied hidden model reliance.
`source_locator_status` must be `passed` before production display can claim
source-located attribution; each visible source row must render its URI,
verification handle, and content-hash prefix. `source_identity_status` must also
be `passed`; each visible source row must match the event source-reference
metadata it claims to expose. `temporal_grounding_status` must also be `passed`;
answers that say `current`, `latest`, `recent`, `today`, `now`, or `as of`
must carry source freshness metadata before they can be shown as grounded.
`source_usage_metric_status` must also be `passed` before production display can
claim usage-explained source attribution.
`source_usage_metric_provenance_status` must also be `passed`; each visible
source row must carry and render the expected metric profile, scope, and method
identifiers.
`claim_evidence_status` must also be `passed`; every supported
claim must have a visible Claim Evidence row whose claim hash, support score,
span hash, character offsets, and evidence preview match the verifier payload.
`claim_warrant_strength_status` must also be `passed`; every supported claim
must render the claim text, evidence text, warrant status, and any force
mismatch across relation, modality, scope, temporal validity, or numeric
specificity.
`claim_source_disagreement_status` must also be `passed`; every supported claim
must disclose the visible source labels that agree with it and fail if any
visible high-overlap source plainly contradicts it.
`claim_source_closure_status` must also be `passed`; each supported claim must
bind to the visible source row with the same source label, work ID, and chunk ID.
`answer_claim_coverage_status` must also be `passed`; the answer text's claim
units must exactly match the footer claim rows before the response can imply all
displayed assertions are covered.
`model_reliance_claim_status` must also be `passed`; answer text must not claim
hidden model use, reasoning, or source influence beyond observable footer support
and allocation fields.
`attribution_gap_status` must also be `passed`; the event must close the gap
between consumed, visible, and paid sources before the answer can be presented
as grounded or royalty-bearing.
Use `--display-text` when validating copied or exported output; the check fails
if the footer or verification handles were stripped. Publishable footer checks
validate against
`schemas/service_source_footer_verification.schema.json` and reject forged
event-id or public-verifier status bindings. They pass only for verified
public-reliance-ready footers; full response checks validate against
`schemas/service_response_verification.schema.json`.

## Gate Production Traffic

Run the fail-closed launch gate against the profile, config, bootstrap
directory, saved response, and optional support bundle output:

```bash
rdllm-operator-launch-gate \
  --profile "$RDLLM_HOME/production_readiness_profile.json" \
  --service-config "$RDLLM_HOME/service_config.json" \
  --service-root "$RDLLM_HOME" \
  --bootstrap-dir "$RDLLM_HOME" \
  --response /tmp/rdllm-service-response.json \
  --display-text /tmp/rdllm-copied-output.txt \
  --write-support-bundle /tmp/rdllm-support-bundle.json
```

Traffic is allowed only when the launch-gate JSON report has
`status: "ready"` and `summary.traffic_decision: "allow"`. The report validates
against `schemas/operator_launch_gate.schema.json`.

## Preserve Recovery And Audit Evidence

Create a recovery manifest over the same operator root:

```bash
rdllm-operator-recovery create \
  --root "$RDLLM_HOME" \
  --output "$RDLLM_STATE/recovery_manifest.json"
rdllm-operator-recovery verify \
  --manifest "$RDLLM_STATE/recovery_manifest.json" \
  --root "$RDLLM_HOME"
```

The manifest and verification output validate against
`schemas/operator_recovery_manifest.schema.json` and
`schemas/operator_recovery_verification.schema.json`.

Verify the service audit log before final acceptance:

```bash
rdllm-service-audit-verify \
  --audit-log "$RDLLM_AUDIT_LOG"
```

The latest response-bound audit row must be `ready` with zero audit errors for
production handoff. Blocked rows can be retained for audit, but they do not
approve traffic. Each JSONL row validates against
`schemas/service_audit_entry.schema.json`, and the verification output validates
against `schemas/service_audit_verification.schema.json`.

## Publish Final Acceptance

Create and verify one final operator acceptance report:

```bash
rdllm-operator-acceptance \
  --profile "$RDLLM_HOME/production_readiness_profile.json" \
  --service-config "$RDLLM_HOME/service_config.json" \
  --service-root "$RDLLM_HOME" \
  --bootstrap-dir "$RDLLM_HOME" \
  --response /tmp/rdllm-service-response.json \
  --display-text /tmp/rdllm-copied-output.txt \
  --audit-log "$RDLLM_AUDIT_LOG" \
  --recovery-manifest "$RDLLM_STATE/recovery_manifest.json" \
  --recovery-root "$RDLLM_HOME" \
  --output "$RDLLM_STATE/operator_acceptance_report.json"
rdllm-operator-acceptance verify \
  --report "$RDLLM_STATE/operator_acceptance_report.json"
```

Treat the deployment as production-grade only when the acceptance report has
`status: "ready"` and
`summary.production_acceptance_decision: "allow"`. The verification output
validates against `schemas/operator_acceptance_verification.schema.json`.

For a release, distribution, or institutional evaluation, also run the
acceptance matrix. It bootstraps and accepts all supported operator roles
(`individual`, `company`, `institution`, `government`, and `public_sector`) and
checks that each role reaches the correct settlement and public-sector posture:

```bash
rdllm-operator-acceptance-matrix \
  --output-dir "$RDLLM_STATE/acceptance-matrix" \
  --write-report "$RDLLM_STATE/operator_acceptance_matrix.json"
```

Treat open-source release evidence as incomplete unless the matrix report has
`status: "passed"`. The report validates against
`schemas/operator_acceptance_matrix.schema.json`.

## Share A Redacted Bundle

For maintainer, auditor, or public handoff, produce a redacted support bundle
that verifies the final acceptance report without exposing sensitive payloads:

```bash
rdllm-operator-support-bundle \
  --acceptance-report "$RDLLM_STATE/operator_acceptance_report.json" \
  --output /tmp/rdllm-support-bundle.json
```

The bundle keeps public hashes, counts, package status, runtime status, and
acceptance verification status. It excludes raw prompts, generated outputs, raw
source text, rendered footers, tokens, API keys, payment account details, and
exact local paths.

## Keep The Boundaries Clear

- A green repository test suite is necessary, but the operator still needs a
  ready launch gate and ready acceptance report for the deployed environment.
- `--skip-response` is only a profile/config preflight; it must not approve
  production display traffic.
- Escrow-only and instruction-only profiles can be production-grade without
  claiming direct creator payout execution.
- Direct creator settlement requires processor-attested evidence and should use
  the `public_sector` profile pattern or an equivalent verified profile.
- Government and institutional deployments should also complete the public-sector
  and governance controls in `production_readiness.md`.

For deeper operational procedures, use `operator_runbook.md`; for service
endpoints, use `service_api.md`; for release evidence, use
`release_checklist.md`.
