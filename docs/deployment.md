# Deployment

This guide describes the reference deployment path for RDLLM as an open-source
royalty and source-attribution platform. The bundled service is dependency-free
and can run anywhere Python runs. Production operators should still place it
behind their normal ingress, TLS, identity, monitoring, and backup systems.

The reference HTTP process is intentionally single-tenant and single-process. Its
shared bearer token, in-memory rate limiter, and local JSONL audit sink are defense
in depth for one operator boundary, not a multi-tenant identity or durable storage
system. Multi-tenant deployments require an external identity gateway, tenant
isolation, distributed rate limiting, and durable append-only storage. Those
controls must be covered by trusted `runtime_controls` and `audit_log_integrity`
attestations before the deployment can claim production readiness.

## Runtime Components

Required:

- Python 3.10 or newer
- installed `royalty-driven-llm` package or repository checkout with
  `rdllm-service`, `rdllm-service-config`, `rdllm-operator-profile`,
  `rdllm-operator-launch-gate`, and `rdllm-operator-support-bundle` available
- service config generated into an operator-controlled path
- source corpus or registered source index
- public proof artifacts
- `RDLLM_SERVICE_TOKEN_SHA256` from a secret manager
- writable audit log path

Recommended production envelope:

- TLS termination at a reverse proxy or platform ingress
- authentication broker or API gateway before RDLLM
- built-in per-process rate limiting, plus distributed rate limiting and request-size
  enforcement at ingress
- tenant identity propagated into operator logs
- central log shipping for the RDLLM hash-chained audit log
- backup for rights registry, source registry, settlement ledger, and audit log
- health/readiness probes using `/healthz` and `/readyz`

## Deployment Templates

The repository includes:

- `Dockerfile`: production image template for the RDLLM service.
- `compose.yaml`: local or single-node Docker Compose deployment.
- `.env.example`: token-hash environment template.
- `deploy/docker/service_config.container.json`: container service config.
- `examples/service_config.openai_compatible.json`: provider-route service
  config example with API keys read from environment variables.
- `deploy/kubernetes/`: Kubernetes namespace, config map, deployment, service,
  persistent volume claim, network policy, and secret example.

The installed package also includes `rdllm-service-config`, which can generate
`default`, `openai_compatible`, or `container` service configs without relying on
a repository checkout.

For a new operator deployment, start with the combined bootstrap command:

```bash
rdllm-operator-bootstrap \
  --output-dir /etc/rdllm \
  --operator-template company \
  --operator-name "Acme RDLLM" \
  --security-contact security@example.com \
  --corpus /srv/rdllm/corpus.json
rdllm-operator-bootstrap --verify-dir /etc/rdllm
```

It creates the operator profile, readiness report, service config, proof-artifact
directory, runtime directory, manifest, and local README in one pass. The
verification command replays the generated manifest, profile report, and service
config before traffic is routed to the deployment. Its output validates against
`docs/schemas/operator_bootstrap_verification.schema.json`.
For local self-tests, add `--include-sample-corpus` and
`--include-reference-artifacts` to export packaged demo inputs into the output
directory. Replace those files with operator-controlled corpus and production
proof artifacts before production traffic.

Before production traffic, save one attribution response from the deployment
under test and run the installed launch gate:

```bash
rdllm-operator-launch-gate \
  --profile /etc/rdllm/production_readiness_profile.json \
  --trust-store /etc/rdllm/deployment_trust_store.json \
  --service-config /etc/rdllm/service_config.json \
  --service-root /etc/rdllm \
  --bootstrap-dir /etc/rdllm \
  --response /tmp/rdllm-service-response.json \
  --display-text /tmp/rdllm-copied-output.txt \
  --write-support-bundle /tmp/rdllm-support-bundle.json
```

The launch gate is the final fail-closed go-live decision. The support bundle is
the redacted artifact to share with auditors or maintainers when the gate blocks;
after final acceptance, include the saved acceptance report with
`--acceptance-report` so handoff diagnostics verify the production decision hash.
Launch-gate JSON reports validate against
`docs/schemas/operator_launch_gate.schema.json`.
Runtime checks require `RDLLM_SERVICE_TOKEN_SHA256` or the configured token-hash
environment variable to be set from the operator secret manager.
Create a recovery manifest for the same operator root before backup and verify
it after restore:

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

After the launch gate, audit verifier, and recovery verifier pass, write the
operator acceptance report:

```bash
rdllm-operator-acceptance \
  --profile /etc/rdllm/production_readiness_profile.json \
  --trust-store /etc/rdllm/deployment_trust_store.json \
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

The verification output validates against
`docs/schemas/operator_acceptance_verification.schema.json`.

Do not approve traffic from an acceptance report unless
`audit_response_binding.latest_entry_status` is `ready` and
`audit_response_binding.latest_audit_error_count` is `0`.

Audit the templates:

```bash
PYTHONPATH=src python3 tools/deployment_audit.py
```

## Minimal Local Run

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
PYTHONPATH=src python3 tools/service_config.py create \
  --template default \
  --corpus examples/sample_corpus.json \
  --output runtime/service_config.json
export RDLLM_SERVICE_TOKEN="replace-with-local-token"
export RDLLM_SERVICE_TOKEN_SHA256="$(python3 - <<'PY'
import hashlib
import os
print(hashlib.sha256(os.environ["RDLLM_SERVICE_TOKEN"].encode()).hexdigest())
PY
)"
rdllm-service --config runtime/service_config.json
```

In another shell:

```bash
curl -sS http://127.0.0.1:8765/readyz
```

## Production Configuration

Before calling a deployment production-ready, follow the signed-evidence workflow
in [Production Readiness](production_readiness.md). The bundled profiles are
unattested templates and intentionally do not authorize a production claim.

Generate a config and change the operator-specific fields:

```bash
rdllm-service-config create \
  --template default \
  --corpus /srv/rdllm/corpus.json \
  --audit-log-path /var/lib/rdllm/audit/rdllm_service_audit.jsonl \
  --artifact-dir /srv/rdllm/artifacts \
  --output /etc/rdllm/service_config.json
rdllm-service-config validate --config /etc/rdllm/service_config.json
```

The validation output validates against
`docs/schemas/service_config_verification.schema.json`.

Review:

- `corpus`
- `audit_log_path`
- `creator_pool_rate`
- `jurisdiction`
- proof artifact paths, or use `--artifact-dir` / repeated
  `--artifact name=path` overrides
- request limits
- `rate_limit_requests_per_window` and `rate_limit_window_seconds`
- host and port

For provider-backed attribution, start from the packaged provider template:

```bash
rdllm-service-config create \
  --template openai_compatible \
  --corpus /srv/rdllm/corpus.json \
  --artifact-dir /srv/rdllm/artifacts \
  --provider-id acme-provider \
  --provider-base-url https://provider.example \
  --provider-model acme-model \
  --provider-api-key-env ACME_PROVIDER_KEY \
  --output /etc/rdllm/service_config.json
```

Do not put raw tokens in config. Keep `auth.token_sha256_env` and inject the hash
through the runtime environment.

## Docker Compose

```bash
cp .env.example .env
# Set RDLLM_SERVICE_TOKEN_SHA256 to a SHA-256 hash of your bearer token.
docker compose up --build
```

The Compose template runs the service with a read-only filesystem, dropped
capabilities, no-new-privileges, a writable audit-log volume, and `/readyz`
health checks.

## Kubernetes

```bash
kubectl create namespace rdllm
kubectl -n rdllm create secret generic rdllm-service-secret \
  --from-literal=token_sha256="$RDLLM_SERVICE_TOKEN_SHA256"
kubectl apply -k deploy/kubernetes
```

The Kubernetes template uses non-root execution, runtime default seccomp,
read-only root filesystem, dropped capabilities, persistent audit storage,
readiness/liveness probes, resource requests/limits, and a restrictive ingress
NetworkPolicy. `deploy/kubernetes/secret.example.yaml` is documentation only and
is intentionally excluded from `kustomization.yaml`.

## Health and Readiness

Use `/healthz` for process liveness.

Use `/readyz` for serving readiness. It must report `ready` before routing
traffic. Readiness verifies:

- service config schema
- auth token hash availability
- engine load
- configured audit-log path writability
- certification report
- discovery manifest
- provider attribution card
- production-readiness report
- production invocation admission
- runtime conformance receipt
- source-grounded response receipt

If readiness is blocked, the service refuses `/v1/attribute` with HTTP 503.

## Observability

`GET /v1/metrics` returns authenticated JSON counters. Operators should scrape or
ship these counters into their observability system:

- request volume
- attribution request volume
- blocked request volume
- verifier/audit error volume
- rate-limited request volume
- readiness status
- uptime

`GET /v1/metrics/prometheus` returns the same counters in Prometheus text format.

Provider-backed routes use `POST /v1/provider/attribute`. Configure
`providers[]` in the service config with a provider ID, `openai_compatible_chat`
family, base URL, model, and API-key environment variable. The service refuses
provider-backed attribution when the route is not allowlisted or the configured
API-key environment variable is missing.
Protected service endpoints are also subject to the configured
`rate_limit_requests_per_window` and `rate_limit_window_seconds` values.

The service also writes hash-chained audit log entries for attribution requests.
Each entry binds request ID, event ID, event hash, source-footer hash, display
hash, source count, audit-error count, prior entry hash, and entry hash.
Readiness rejects an existing audit log whose chain cannot be verified, and
attribution routes fail closed if the new entry cannot be committed. The
verifier rejects broken chains, missing footer/display bindings, and
status/error-count contradictions, including `ready` rows with audit errors and
`blocked` rows without audit errors. Verify the chain before relying on the log
for incident response, audit handoff, or settlement review. Audit rows validate
against `docs/schemas/service_audit_entry.schema.json`; verifier reports
validate against `docs/schemas/service_audit_verification.schema.json`:

```bash
rdllm-service-audit-verify \
  --audit-log /var/lib/rdllm/audit/service.jsonl
```

## Upgrade Gate

Before rollout:

```bash
PYTHONPATH=src python3 tools/service_smoke.py
PYTHONPATH=src python3 tools/service_load_smoke.py
PYTHONPATH=src python3 tools/provider_live_smoke.py
PYTHONPATH=src python3 tools/security_abuse_smoke.py
PYTHONPATH=src python3 tools/deployment_audit.py
PYTHONPATH=src python3 tools/production_readiness.py
PYTHONPATH=src python3 tools/ship_check.py --skip-tests --skip-regenerate
PYTHONPATH=src python3 -m unittest discover -s tests
```

For full release candidates, run:

```bash
PYTHONPATH=src python3 tools/ship_check.py
```

## Failure Policy

The deployment must fail closed when:

- auth token hash is absent
- required proof artifact is missing or not ready
- provider attribution card does not bind passed RDLLM-L186 certification
- request exceeds configured size limits
- protected route exceeds configured rate limiting
- audit verification fails for the generated event
- audit-log path is absent, not writable, corrupt, or cannot commit the generated
  event before response release
- provider API key is missing, the provider route is unknown, the provider route
  still uses a packaged placeholder, or provider output is filtered, malformed,
  or larger than the configured output limit
- unknown route or unauthenticated protected route is called

Blocked requests must not be treated as grounded answers and must not release
direct creator settlement.
