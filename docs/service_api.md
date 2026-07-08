# Service API

RDLLM includes a dependency-free HTTP service boundary for production operators.
It is intentionally small: run it behind the operator's normal reverse proxy,
identity provider, TLS termination, and observability stack. The service also
enforces its own protected-endpoint rate limit so a missing ingress rule does
not turn attribution, metrics, or provider calls into an unbounded surface.

## Start

Set the bearer-token hash. The service stores only the SHA-256 hash, not the raw
token.

```bash
rdllm-service-config create \
  --template default \
  --corpus /srv/rdllm/corpus.json \
  --audit-log-path /var/lib/rdllm/audit/service.jsonl \
  --artifact-dir /srv/rdllm/artifacts \
  --output /etc/rdllm/service_config.json
rdllm-service-config validate --config /etc/rdllm/service_config.json
export RDLLM_SERVICE_TOKEN="replace-with-local-token"
export RDLLM_SERVICE_TOKEN_SHA256="$(python3 - <<'PY'
import hashlib
import os
print(hashlib.sha256(os.environ["RDLLM_SERVICE_TOKEN"].encode()).hexdigest())
PY
)"
rdllm-service --config /etc/rdllm/service_config.json
```

The service-config validation output validates against
`docs/schemas/service_config_verification.schema.json`.

From a repository checkout, `PYTHONPATH=src python3 tools/service_config.py`
provides the same create and validate commands, and
`PYTHONPATH=src python3 -m rdllm.service --config path/to/service_config.json`
starts the service. For real deployments, replace the local token, keep the raw
token in a secret manager, and provide only the hash through
`RDLLM_SERVICE_TOKEN_SHA256`.

## Endpoints

`GET /healthz`

Liveness check. Does not require authentication.

`GET /readyz`

Readiness check. Does not require authentication. It verifies service config,
auth hash availability, engine load, certification report, discovery manifest,
provider attribution card, production-readiness report, production invocation
admission, runtime conformance receipt, and source-grounded response receipt.

`GET /.well-known/rdllm.json`

Serves the configured discovery manifest. Does not require authentication.

`GET /openapi.json`

Serves a compact OpenAPI description. Does not require authentication.

`POST /v1/attribute`

Authenticated attribution endpoint. If `output` is supplied, RDLLM attributes
the externally generated text. If `output` is omitted, RDLLM generates a
deterministic demo answer from the registered corpus and returns the verified
source footer.

Example:

```bash
curl -sS \
  -H "Authorization: Bearer ${RDLLM_SERVICE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What should royalty-bearing AI answers expose?",
    "output": "Every royalty bearing AI answer should have a provenance record. The record should include source identifiers, content hashes, retrieval scores, output citations, payout weights, and an event hash that allows auditors to replay the attribution.",
    "gross_revenue": "1.00"
  }' \
  http://127.0.0.1:8765/v1/attribute
```

Response shape:

- `schema`: `rdllm-service-attribution-response/v1`
- `status`: `ready` or `blocked`
- `summary`: event hash, source count, source-footer hash, royalty share count,
  grounding verdict, and attribution-gap verdict
- `source_footer`: client-renderable footer with source rows, claim-evidence
  rows, rendered footer text, footer hash, verifier handles, source URIs, content
  hashes, evidence-span hashes, confidence labels, and settlement status. The
  footer is derived from the authenticated event and is not a separate attribution
  decision. Each displayed source row carries a deterministic
  `rdllm://verify/source-footer/...` handle that binds the event, source label,
  and content-hash prefix for copied or exported answers.
- `display`: the exact answer-plus-footer surface that clients should render or
  preserve on copy/export. `ready` means the grounding verdict is display-safe;
  unsupported or weakly grounded claims are disclosed in the footer and block
  production display.
- `audit_errors`: fail-closed verifier errors
- `event`: full authenticated usage event for the requesting tenant

The response is described by
`docs/schemas/service_attribution_response.schema.json`.

Save a response and verify that the event, footer rows, rendered footer text,
footer hash, and summary bindings still agree before showing or copying it:

```bash
rdllm-service-response-verify \
  --response response.json \
  --display-text copied-output.txt
rdllm-source-footer-verify \
  --footer source-footer.json \
  --display-text copied-output.txt
```

The verifier reports `production_display_ready`, which is true only when
verification passes, the response status is `ready`, and grounding is safe for
display. It also reports `source_grounding_acceptance`, which must be `passed`
for any grounded or royalty-bearing user display. That acceptance profile checks
source materialization, supported claim evidence, minimum support score,
non-escrow royalty-share coverage, and answer-plus-footer display binding. A
blocked response can still verify as internally consistent for audit, but launch
approval requires `production_display_ready: true`,
`source_grounding_acceptance.status: passed`, and response `status: ready`.
The acceptance profile also reports `answer_citation_marker_count`,
`resolved_answer_citation_marker_count`, `citation_marker_status`,
`answer_citation_markers`, `resolved_answer_citation_markers`, and
`unresolved_answer_citation_markers`; unresolved inline citation markers in the
answer text fail production display unless they match verified source-footer
source or claim labels. Numeric markers resolve as source aliases, so `[1]` and
`[Source: 1]` are accepted only when source row `S1` is verified. Numeric groups
and ranges must fully resolve; four-digit bracketed years such as `[2026]` are
ignored as non-citation text. The same profile reports `answer_link_uris`,
`resolved_answer_link_uris`, `unresolved_answer_link_uris`, URI counts, and
`answer_link_status`; Markdown links and bare `scheme://...` URIs in the answer
fail production display unless they match verified source-footer `source_uri`
values.
Verification also checks footer semantics: source rows must match the supported
claim rows they summarize, and supported claim evidence previews must be visible
in the rendered claim-evidence footer and reproduce their declared evidence span
hashes. Claim-evidence rows also expose `claim_preview`, `claim_warrant_profile`,
`claim_force_flags`, `evidence_force_flags`, `warrant_mismatch_flags`, and
`warrant_strength_status`; a ready response is rejected when related evidence
does not carry the same relation, modality, scope, temporal, or numeric force as
the displayed claim. They also expose `source_disagreement_profile`,
`agreement_source_labels`, `disagreement_source_labels`, and
`source_disagreement_status`; a ready response is rejected when a visible source
plainly contradicts a supported claim. A ready response is also rejected if a
visible source row omits or forges its verification handle. Rendered source rows
expose `uri`, `verify`, and `hash`
locators, plus `support`, `text_match`, `weight`, and `payout`. They also expose
`usage_metric_profile`, `usage_metric_scope`, and the method identifiers for
each usage metric, so the copied/exported answer shows both where the source can
be checked and which observable metric profile produced the allocation numbers.
These are observable grounding and settlement-allocation metrics, not hidden
model-internal reliance claims unless a provider supplies separately verified
model-signal telemetry.
`source_grounding_acceptance` reports `source_usage_metric_names`,
`source_usage_metric_row_count`, `source_usage_metric_status`,
`source_usage_metric_profile`, `source_usage_metric_scope`,
`source_usage_metric_methods`, `source_usage_metric_provenance_count`,
`source_usage_metric_provenance_status`,
`source_locator_count`, `source_locator_status`, `source_identity_count`, and
`source_identity_status`; grounded display fails if a visible source row omits
required usage metrics, omits or changes the metric profile/scope/method
disclosure, does not render its URI, verification handle, and content-hash
prefix, or does not match the event source-reference metadata it claims to
expose. It also reports `temporal_claim_markers`,
`source_temporal_metadata_count`, and `temporal_grounding_status`; grounded
display fails when temporal answer wording such as `current`, `latest`,
`recent`, `today`, `now`, or `as of` appears without source freshness metadata
on every visible source row. It also reports
`answer_claim_unit_count`, `answer_claim_row_coverage_count`,
`uncovered_answer_claim_hashes`, `extra_claim_row_hashes`, and
`answer_claim_coverage_status`; grounded display fails if the answer text's
claim units do not exactly match the footer claim rows. It also reports
`model_reliance_claim_markers`, `model_reliance_claim_marker_count`, and
`model_reliance_claim_status`; grounded display fails if the answer surface
claims hidden model use, reasoning, or source influence beyond observable
support/allocation fields. It also reports
`claim_evidence_row_count` and `claim_evidence_status`; grounded display fails
if any supported claim lacks a visible Claim Evidence row with a matching claim
hash, support score, evidence span hash, character offsets, and evidence
preview. It also reports `claim_warrant_profile`,
`claim_warrant_strength_count`, and `claim_warrant_strength_status`; grounded
display fails if any supported claim has over-strong wording relative to its
evidence. It also reports `source_disagreement_profile`,
`claim_source_disagreement_count`, and `claim_source_disagreement_status`;
grounded display fails if a supported claim has visible high-overlap source
disagreement. It also reports `claim_source_closure_count` and
`claim_source_closure_status`; grounded display fails if a supported claim's
source label, work ID, or chunk ID does not match the visible source row it is
attributed to. It also reports `attribution_gap_status`,
`attribution_gap_verdict`, accessed/credited source counts, and open-gap failure
counts; grounded display fails unless the event's consumed, visible, and paid
source coverage is closed. When `--display-text` is provided, the verifier also checks
that the copied or exported text exactly matches `display.rendered_text`;
stripping the footer or verification handles fails the report.
For public handoff, `rdllm-source-footer-verify` validates a standalone
`source_footer` artifact without requiring the private full response. It checks
row hashes, claim evidence span hashes, deterministic verification handles,
footer hash, event-id/event-hash consistency, footer-status/public-verifier
consistency, and whether copied/exported text still contains the exact footer.
The standalone footer report passes only for a verified, public-reliance-ready
footer.

From a source checkout, use
`PYTHONPATH=src python3 tools/service_response_verify.py --response response.json`.
The verification outputs validate against
`docs/schemas/service_response_verification.schema.json` and
`docs/schemas/service_source_footer_verification.schema.json`.

`POST /v1/provider/attribute`

Authenticated provider-backed attribution endpoint. The service calls a
configured OpenAI-compatible chat-completions provider route, captures the
generated answer, hashes the provider response, and then runs RDLLM attribution
before returning or releasing the answer.

Example payload:

```json
{
  "provider_id": "openai-compatible-default",
  "messages": [
    {
      "role": "user",
      "content": "What should royalty-bearing AI answers expose?"
    }
  ],
  "gross_revenue": "1.00"
}
```

Provider routes are allowlisted in `providers[]` in the service config. Provider
API keys must be supplied through the configured `api_key_env`; they are never
stored in the config, response, audit log, or public proof artifacts.

Provider-backed responses use the same `source_footer` object. Clients should
render `source_footer.rendered_text` or reconstruct their own UI from
`source_footer.source_rows` and `source_footer.claim_rows`, then preserve
`source_footer.footer_hash` in copied/exported output.

`GET /v1/metrics`

Authenticated JSON counters:

- `requests_total`
- `attribution_requests_total`
- `blocked_requests_total`
- `audit_errors_total`
- `provider_requests_total`
- `provider_route_count`
- `rate_limited_requests_total`
- `ready_status`
- `uptime_seconds`

`GET /v1/metrics/prometheus`

Authenticated Prometheus-compatible text counters for the same service metrics.

## Security Defaults

- bearer-token authentication by SHA-256 hash
- fail-closed readiness before attribution
- request-size, prompt-size, and output-size limits
- per-client sliding-window rate limiting on protected endpoints
- no CORS headers by default
- no-store cache header
- content-sniffing disabled
- restrictive content security policy
- request ID response header
- hash-chained audit log for attribution requests
- installed audit-log verifier for chain continuity and entry-hash validation

## Smoke Test

Run:

```bash
PYTHONPATH=src python3 tools/service_smoke.py
PYTHONPATH=src python3 tools/service_load_smoke.py
PYTHONPATH=src python3 tools/provider_live_smoke.py
PYTHONPATH=src python3 tools/security_abuse_smoke.py
```

The smoke starts the real service, verifies liveness, readiness, security
headers, unauthorized rejection, authenticated attribution, metrics, and
hash-chained audit logging. The load smoke sends concurrent authenticated
attribution requests and verifies metrics plus audit-chain continuity using the
same verifier exposed as `rdllm-service-audit-verify`.
The provider smoke starts a local OpenAI-compatible mock provider and verifies
provider invocation, provider response hashing, attribution, metrics, and audit
logging without requiring external API keys.
The security abuse smoke verifies that unauthenticated calls, oversized prompts,
negative revenue, unknown providers, missing provider keys, filtered provider
responses, malformed provider responses, oversized provider output, and rate
limits fail closed before a response can be treated as grounded.
