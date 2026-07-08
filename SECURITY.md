# Security Policy

## Supported Versions

The main branch is the only supported development line until the first stable
release. Security fixes should target main.

## Reporting a Vulnerability

Do not open a public issue for vulnerabilities involving private payload leaks,
signature bypasses, settlement release bypasses, verifier replay weaknesses,
provider adapter bypasses, or proof artifact tampering.

Report privately by opening a GitHub security advisory on the repository, or by
contacting the current maintainers through the project owner channel listed on
GitHub.

Please include:

- affected artifact, command, schema, or verifier
- minimal reproduction steps
- expected fail-closed behavior
- observed unsafe behavior
- whether private text, secrets, customer data, or payout data can be exposed

## Security Invariants

- Public artifacts must be privacy-safe and hash-bound.
- Unknown provider states fail closed.
- A blocked, filtered, refused, truncated, tool-only, errored, or unverified
  response must not be presented as a grounded answer.
- Creator settlement must not release unless attribution, rights, provider,
  meter, and response-state gates are ready.
- Verifiers must reject stale hashes, missing signatures when required, and
  private field leakage.

## Secrets

Production operators must keep API keys, signing keys, payout credentials,
database credentials, salts, and webhook secrets outside the repository and
outside public proof artifacts. Public artifacts may contain key identifiers,
hash commitments, and signature metadata, but not raw secrets.

## Supply Chain

The release process requires CI, dependency update policy, package build checks,
schema validation, hosted-surface privacy checks, and the full ship gate before a
release is tagged. Operators that redistribute RDLLM should preserve build logs,
package hashes, dependency lock evidence when used, and release provenance.

## Abuse

Treat prompt-injection attempts, source-footer fabrication, attribution
suppression, rights-registry poisoning, duplicate ownership claims, provider
route bypasses, and settlement-meter manipulation as abuse cases. Affected
routes should fail closed, direct settlement should be held, and negative
fixtures should be replayed before reopening the route.

## Incident Response

Open an incident when a verifier accepts invalid proof, public artifacts leak
private data, source footers are missing or fabricated, revocation does not
propagate within SLA, payment execution does not reconcile, or a provider route
bypasses admission controls.

Minimum response:

- preserve relevant logs, profile, and proof artifacts
- disable verified source-footer claims for affected routes
- hold direct settlement for affected works, tenants, or providers
- rotate exposed secrets or signing material
- publish correction or reliance-revocation artifacts when users may have relied
  on an affected public proof
- replay the production-readiness, privacy, provider, and ship gates before
  restoring production claims
