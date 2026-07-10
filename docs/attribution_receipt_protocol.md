# RDLLM Attribution Receipt Protocol

Version: `rdllm-attribution-receipt/v1`

> **Security boundary:** production receipts use Ed25519 public-key signatures.
> The repeated `--signing-secret secret` commands later in this document create
> deterministic conformance fixtures only. HMAC fixtures are not independently
> verifiable, must never authorize a deployment or payment, and must not be used
> with a real secret copied into shell history.

Generate an operator key pair without printing the private key:

```bash
rdllm-keygen \
  --private-key /secure/rdllm/receipt-private.pem \
  --public-key /etc/rdllm/receipt-public.pem
```

The private key is created with mode `0600`. Keep it in an operator-controlled
secrets manager or signing service. Publish the public key and its key ID so users
and auditors can verify receipts without trusting the issuer's server.

## Purpose

The Royalty Driven LLM mechanism should not stop at internal payout accounting.
Every monetized AI usage event should be able to emit a verifiable attribution
receipt that proves:

1. which model route produced the response
2. which sources grounded the response
3. which exact evidence spans supported each claim
4. which claims were supported by which sources
5. whether citation labels, evidence spans, and factual support pass a reproducible
   grounding-quality check
6. whether every accessed source was cited, paid, or explicitly escrowed
7. whether each source was licensed for the attempted use
8. whether matched works have open ownership registry conflicts
9. which owners were credited and paid, or which escrow account held the value
10. which private prompt/output commitments were used
11. whether the receipt was included in an append-only transparency log
12. whether a public selective-disclosure package faithfully represents the private
    receipt without revealing private prompts, source quotes, access traces, or
    payout internals
13. whether provider telemetry exposes the same source accesses, citations, and
    claim-support evidence committed by the receipt
14. whether externally generated or paraphrased text has a replayable semantic
    attribution report with source footer rows or escrow
15. whether diffuse licensed training-corpus value is settled through a residual
    corpus royalty report that is separate from visible source footers and direct
    answer-attribution payout
16. whether the residual valuation method was benchmarked through known
    contributors, hard anti-documents, duplicate guards, confidence calibration,
    score stability, and privacy-preserving method commitments

This makes attribution useful for four parties at once:

- users get grounded answers with source footers
- creators get visible attribution and royalty accounting
- model providers get a machine-checkable compliance artifact
- auditors get cryptographic commitments and inclusion proofs

For text that was not generated inside the current provider route, the companion
`rdllm-semantic-text-attribution/v1` report supplies the same user-facing discipline:
it publishes footer rows for accepted source owners and escrow rows for ambiguous
or unmatched text while keeping the private prompt, output, matched passage, and
source text out of the public artifact.

For model value that cannot honestly be tied to a visible answer source, the
companion `rdllm-residual-corpus-royalty-report/v1` report handles a different
surface: diffuse licensed training-corpus royalties. It binds revenue rows,
training-content cohorts, creator-license terms, valuation evidence hashes,
direct-attribution exclusions, creator caps, payable rows, escrow rows, and
creator residual receipts without changing the user-facing source footer.

The companion `rdllm-valuation-method-audit/v1` report verifies the method behind
those residual rows. It binds the residual report to audited method cards,
benchmark-suite hashes, anti-document and duplicate-guard cases, confidence and
stability checks, and privacy or zero-knowledge commitments without publishing
raw benchmark, training, prompt, output, customer, or payment text.

## Design Lineage

The protocol intentionally borrows from existing supply-chain and dataset-governance
patterns:

- W3C PROV: entities, activities, and agents
- C2PA: content provenance manifests
- SCITT: signed statements, transparency services, and receipts
- Sigstore/Rekor: append-only transparency logs and inclusion proofs
- in-toto/SLSA: attestations about how an artifact was produced
- SPDX 3.0 AI: bill-of-materials vocabulary for AI systems and model artifacts
- MLCommons Croissant: machine-readable dataset metadata, provenance, and permissions
- W3C ODRL: permission, prohibition, duty, and constraint expressions for content use
- W3C Verifiable Credentials 2.0: portable issuer/subject/proof patterns for
  ownership attestations
- IETF SD-JWT/RFC 9901 and W3C Data Integrity BBS: selective disclosure patterns
  for signed claims, salted disclosures, and unlinkable derived proofs
- OpenTelemetry GenAI semantic conventions: provider-neutral spans for GenAI
  operations, data-source IDs, retrieval documents, model identifiers, and
  externally stored content references

The new idea is to apply these patterns at AI response time, not only at software
build time, identity presentation time, or dataset publication time.

## API Shape

A model provider can return the grounded answer and attach the receipt hash:

```http
X-RDLLM-Receipt-Hash: sha256:...
X-RDLLM-Transparency-Root: sha256:...
X-RDLLM-Protocol: rdllm-attribution-receipt/v1
```

The full receipt can be returned inline, stored privately, or made available through
an audit endpoint:

```http
GET /v1/attribution-receipts/{receipt_hash}
GET /v1/attribution-receipts/{receipt_hash}/public
GET /v1/attribution-receipts/{receipt_hash}/disclosure
GET /v1/attribution-receipts/{receipt_hash}/trace
GET /v1/attribution-receipts/{receipt_hash}/inclusion-proof
```

## Receipt Fields

Each receipt has:

- `receipt_hash`: canonical hash of the payload
- `payload.protocol_version`
- `payload.issuer`
- `payload.issued_at`
- `payload.model`: model ID, version, and route ID
- `payload.event`: event ID, event hash, prompt hash, answer hash, rendered output hash
- `payload.grounding.report`: claim coverage and grounding status
- `payload.grounding.quality`: source accessibility, citation integrity, evidence
  relevance, fact support, policy alignment, payout alignment, issues, and verdict
- `payload.grounding.attribution_gap`: verdict, scores, classifications, accessed
  source summaries, and report hash proving accessed, cited, paid, and escrowed
  sources reconcile
- `payload.grounding.source_accesses`: retrieval and text-match access records with
  work/chunk IDs, source URIs, content hashes, scores, ranks, use, policy decisions,
  registry decisions, and matched-text hashes
- `payload.grounding.sources`: source labels, owners, works, chunks, source URIs,
  evidence quotes, source hashes, evidence span hashes, support scores, contribution
  weights, and payouts
- `payload.grounding.claims`: claim-level support checks, supporting chunk IDs,
  evidence text, span hashes, and source character offsets
- `payload.rights`: policy status, denial count, and deterministic allow/deny
  decisions for retrieval, generation, external attribution, or other attempted uses
- `payload.registry`: registry status, open conflict count, registry report hash,
  and deterministic dispute decisions for matched works
- `payload.telemetry`: trace-exchange version, OpenTelemetry semantic-convention
  URL, source-access trace hash, source-reference trace hash, and claim-support
  trace hash
- `payload.economics`: gross revenue, creator pool, and payout shares
- `payload.privacy`: selective-disclosure version, disclosure root, private
  per-path salts, and public disclosure policy
- `signature`: signing metadata

## Public vs Private Receipt

The private receipt may include sensitive economics and evidence quotes. The public
receipt keeps only:

- receipt hash
- model route metadata
- prompt/output hashes
- grounding report
- grounding quality verdict and score
- attribution-gap verdict and report hash
- rights-policy status and denial count
- ownership-registry status and conflict count
- source IDs and content hashes
- contribution weights
- claim-support metadata and evidence span hashes
- telemetry commitment hashes
- selective-disclosure root
- signature metadata

This gives users and creators a verifiable public trail without forcing every
private prompt, customer document, or revenue number into the open.

## Selective-Disclosure Package

A public receipt alone is useful for UX, but it needs a cryptographic bridge back to
the private receipt. RDLLM therefore emits an `rdllm-selective-disclosure/v1`
package:

- `payload_disclosure_root`: Merkle root over every private receipt payload leaf
  except the root and private salt map
- `disclosed`: public path/value/salt/leaf-hash tuples for model route, event
  hashes, source IDs, source URIs, content hashes, claim-support metadata,
  grounding quality, attribution-gap summary, and policy/registry status
- `redacted`: private paths and salted leaf hashes for source quotes, claim evidence
  text, source-access traces, payout shares, gross revenue, detailed rights
  decisions, and detailed registry decisions
- `public_receipt`: the exact user-visible receipt reconstructed from disclosed
  leaves
- `package_hash`: deterministic hash over the package

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli disclose \
  --receipt artifacts/receipt.json \
  --output artifacts/selective_disclosure_package.json

PYTHONPATH=src python3 -m rdllm.cli verify-disclosure \
  --package artifacts/selective_disclosure_package.json \
  --receipt artifacts/receipt.json \
  --signing-secret secret
```

The verifier detects public receipt drift, disclosed leaf tampering, and mismatch
between the public package and the private signed receipt. The package follows the
security lesson of selective-disclosure credential systems: hash disclosures must
be salted, and undisclosed salts must remain private, so low-entropy hidden fields
are not trivially brute-forced from public digests.

## Trace Exchange

Provider observability logs are useful only if they can be compared with the public
answer and the signed receipt. RDLLM therefore defines `rdllm-trace-exchange/v1`:
an OpenTelemetry-aligned trace export with royalty-grade commitments.

The trace contains:

- a generation span with `gen_ai.provider.name`, model identifiers, event hash,
  prompt hash, answer hash, rendered-output hash, and receipt hash
- a source-access span for every retrieval or text-match access, carrying
  `gen_ai.data_source.id`, structured `gen_ai.retrieval.documents`, chunk ID, work
  ID, creator ID, source URI, content hash, score, rank, policy status, registry
  status, and matched-text hash
- a citation span for every footer-visible source
- a claim-support span for every claim and evidence span hash
- summary hashes that must match `payload.telemetry`

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli trace \
  --receipt artifacts/receipt.json \
  --output artifacts/trace_exchange.json

PYTHONPATH=src python3 -m rdllm.cli verify-trace \
  --trace artifacts/trace_exchange.json \
  --receipt artifacts/receipt.json
```

The verifier rejects missing source-access spans, relabeled citation content hashes,
claim-support drift, trace hashes that are not reproducible, or telemetry summary
hashes that no longer match the receipt. This gives model providers a way to expose
source telemetry without standardizing on a particular vendor's internal logging
format.

## Royalty Statement Rollup

Receipts prove individual events. Creators and enterprise buyers also need periodic
statements. RDLLM defines `rdllm-royalty-statement/v1` for aggregate accounting:

- event, share, source-access, source-reference, claim-support, receipt, and trace
  roots
- creator, escrow, work, and source-usage totals
- gross revenue, creator pool, payout, direct creator, and escrow totals
- privacy flags that keep prompts, outputs, source quotes, evidence text, and
  matched text out of the public statement
- statement hash and optional signature

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli statement \
  --ledger artifacts/conformance_ledger.json \
  --receipt artifacts/conformance_receipt.json \
  --trace artifacts/conformance_trace_exchange.json \
  --signing-secret secret \
  --output artifacts/royalty_statement.json

PYTHONPATH=src python3 -m rdllm.cli verify-statement \
  --ledger artifacts/conformance_ledger.json \
  --statement artifacts/royalty_statement.json \
  --receipt artifacts/conformance_receipt.json \
  --trace artifacts/conformance_trace_exchange.json \
  --signing-secret secret
```

The verifier recomputes the statement from the private ledger and bound artifacts.
It rejects payout drift, creator-statement tampering, missing receipt or trace
rollups, and accidental disclosure of private text fields.

## Attribution Challenge Report

Providers also need a correction path when a creator contests missing or weak
attribution. RDLLM defines `rdllm-attribution-challenge/v1`:

- original event ID, event hash, and optional royalty statement hash
- claimant ID, creator ID, work ID, chunk ID, source URI, and challenged content hash
- overlap evidence as scores, longest matched token sequence length, and matched
  text hash
- already-visible, already-paid, already-accessed, and already-credited flags
- verdict: `accepted`, `accepted_escrow`, `already_credited`, or `rejected`
- remedy: pay claimant, escrow unlicensed value, or no action
- source-access, source-reference, royalty-share, and claim-support commitments
- report hash and optional signature

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli challenge \
  --ledger artifacts/conformance_ledger.json \
  --event-id evt_1ed43e106d466249 \
  --work-id arjun-provenance-ledger \
  --statement artifacts/royalty_statement.json \
  --signing-secret secret \
  --output artifacts/attribution_challenge_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-challenge \
  --ledger artifacts/conformance_ledger.json \
  --event-id evt_1ed43e106d466249 \
  --work-id arjun-provenance-ledger \
  --statement artifacts/royalty_statement.json \
  --challenge artifacts/attribution_challenge_report.json \
  --signing-secret secret
```

The challenge verifier recomputes overlap evidence and the remedy from the original
event and challenged source. It rejects remedy drift, source hash drift, statement
hash drift, and any report that claims to rewrite the original event.

## Derivative Lineage Report

When a response credits a derivative work, RDLLM can emit
`rdllm-lineage-report/v1` so upstream owners remain visible in settlement. The
report binds the event hash, source royalty shares, derivative-work edges, upstream
content hashes, recursive pass-through obligations, and payout-conservation
commitments without exposing prompt, answer, source, or work text.

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli --corpus examples/lineage_corpus.json lineage-report \
  --ledger artifacts/lineage_ledger.json \
  --signing-secret secret \
  --output artifacts/lineage_report.json

PYTHONPATH=src python3 -m rdllm.cli --corpus examples/lineage_corpus.json verify-lineage-report \
  --ledger artifacts/lineage_ledger.json \
  --report artifacts/lineage_report.json \
  --signing-secret secret
```

The verifier rejects missing upstream works, lineage cycles, declared upstream hash
drift, source-payout non-conservation, private-text disclosure, report tampering,
and signature drift.

## Provenance Evaluation Report

Providers can also publish `rdllm-provenance-evaluation/v1` to prove that source
finding works before users trust a receipt. The report replays clean-source,
paraphrase, hard-decoy, unattributed-escrow, and derivative-lineage benchmark cases
with hashed benchmark prompts and outputs.

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli --corpus examples/provenance_benchmark_corpus.json --top-k 4 provenance-evaluation \
  --benchmark examples/provenance_benchmark.json \
  --signing-secret secret \
  --output artifacts/provenance_evaluation_report.json

PYTHONPATH=src python3 -m rdllm.cli --corpus examples/provenance_benchmark_corpus.json --top-k 4 verify-provenance-evaluation \
  --benchmark examples/provenance_benchmark.json \
  --report artifacts/provenance_evaluation_report.json \
  --signing-secret secret
```

The verifier rejects case omission, source-ranking drift, hash drift, signature
drift, and disclosure of raw benchmark prompts, answers, source text, or claim
evidence.

## Counterfactual Influence Report

Providers can publish `rdllm-counterfactual-influence/v1` to prove that credited
sources were not merely plausible citations. The report removes each credited work,
replays the same prompt and answer against the reduced corpus, and records whether
the source disappears, payout reallocates or escrows, and the credited source had a
decisive marginal influence score.

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli --corpus examples/counterfactual_corpus.json --top-k 1 run \
  "How can a provider prove a credited source actually mattered?" \
  --output "Counterfactual attribution reports remove each credited work, replay the same prompt and answer, verify that source credit disappears after removal, and confirm that payout either reallocates to another eligible source or routes to escrow." \
  --ledger artifacts/counterfactual_ledger.json

PYTHONPATH=src python3 -m rdllm.cli --corpus examples/counterfactual_corpus.json --top-k 1 counterfactual-report \
  --ledger artifacts/counterfactual_ledger.json \
  --signing-secret secret \
  --output artifacts/counterfactual_report.json

PYTHONPATH=src python3 -m rdllm.cli --corpus examples/counterfactual_corpus.json --top-k 1 verify-counterfactual-report \
  --ledger artifacts/counterfactual_ledger.json \
  --report artifacts/counterfactual_report.json \
  --signing-secret secret
```

The verifier rejects ablation replay drift, source-removal drift, payout
reallocation failures, hash drift, signature drift, and disclosure of raw prompt,
answer, source, quote, or claim evidence text.

## Media Attribution Report

Providers can publish `rdllm-media-attribution/v1` for multimodal generation and
retrieval. The report matches submitted image, audio, video, 3D, or text-shaped
media signatures against registered assets, publishes ranked scores and hash
commitments, pays matched owners, and routes weak or unknown matches to
unattributed-media escrow.

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli media-attribution \
  --media-corpus examples/media_corpus.json \
  --submitted-media examples/media_inputs.json \
  --media-gross-revenue 3.00 \
  --media-creator-pool-rate 0.55 \
  --accept-threshold 0.65 \
  --signing-secret secret \
  --output artifacts/media_attribution_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-media-attribution \
  --media-corpus examples/media_corpus.json \
  --submitted-media examples/media_inputs.json \
  --report artifacts/media_attribution_report.json \
  --signing-secret secret
```

The verifier rejects media replay drift, weak-score promotion, payout drift, hash
drift, signature drift, and disclosure of raw media, perceptual hashes, or private
descriptor text.

## Model Signal Attribution Report

Providers can publish `rdllm-model-signal-attribution/v1` when they have
model-internal evidence that a registered work influenced an answer. The report
does not expose raw activations. It publishes an explicit
`rdllm-attribution-contract/v1`, event hashes, registered work IDs, scalar signal
scores, accepted or escrow decisions, payout shares, and commitments to the private
telemetry input.

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli model-signal-report \
  --signal-input examples/model_signal_inputs.json \
  --signal-gross-revenue 2.00 \
  --signal-creator-pool-rate 0.55 \
  --accept-threshold 0.50 \
  --signing-secret secret \
  --output artifacts/model_signal_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-model-signal-report \
  --signal-input examples/model_signal_inputs.json \
  --report artifacts/model_signal_report.json \
  --signing-secret secret
```

The verifier rejects telemetry replay drift, unsupported attribution contracts,
weak-score promotion, payout drift, hash drift, signature drift, and disclosure of
private prompt text, output text, hidden states, token logits, private traces, or
chain-of-thought.

## Rights Remediation Report

Providers can publish `rdllm-rights-remediation/v1` whenever a registered work
changes consent, opts out, revokes rights, or changes allowed/prohibited uses after
historical usage. The report compares previous and updated policy roots, preserves
historical event hashes, runs future-use probes, and verifies that denied text use
routes value to `rights_conflict_escrow` without exposing work text or private
ledger payloads.

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli rights-remediation \
  --previous-corpus examples/revocation_previous_corpus.json \
  --updated-corpus examples/revocation_updated_corpus.json \
  --ledger artifacts/revocation_ledger.json \
  --remediation-gross-revenue 1.00 \
  --remediation-creator-pool-rate 0.55 \
  --signing-secret secret \
  --output artifacts/rights_remediation_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-rights-remediation \
  --previous-corpus examples/revocation_previous_corpus.json \
  --updated-corpus examples/revocation_updated_corpus.json \
  --ledger artifacts/revocation_ledger.json \
  --report artifacts/rights_remediation_report.json \
  --signing-secret secret
```

The verifier rejects policy-root drift, historical-event rewrites, future-use
enforcement drift, escrow drift, hash drift, signature drift, and disclosure of
work text, prompts, outputs, matched text, or private ledger payloads.

## Transparency Log

Each receipt can be appended to a Merkle transparency log. The log returns an
inclusion proof:

```json
{
  "leaf_hash": "...",
  "leaf_index": 0,
  "tree_size": 1,
  "root": "...",
  "path": []
}
```

Auditors can verify that:

1. the receipt hash matches the payload
2. the signature matches the issuer
3. the receipt hash is included in the transparency log root
4. the response footer sources match the receipt sources
5. the receipt rights decisions match the ledger event
6. the receipt registry decisions match the ledger event
7. the receipt attribution-gap report and source-access trace match the ledger event
8. the receipt disclosure root matches the private payload leaves
9. the receipt telemetry commitments match the exported trace exchange
10. the receipt economics match settlement records

## Conformance Bundle

A deployer can publish or privately export a conformance bundle:

- rendered response
- ledger event
- private or public receipt
- transparency log checkpoint
- receipt inclusion proof
- trace-exchange artifact
- verifier output

The reference verifier checks:

- receipt shape
- receipt hash reproducibility
- optional signature validity
- prompt, answer, rendered-output, and event hash commitments
- footer source labels against receipt source labels
- receipt source references against ledger source references
- receipt claim support against ledger claim support
- receipt grounding quality against ledger grounding quality
- receipt attribution-gap report against ledger attribution-gap report
- receipt source-access trace against ledger source-access trace
- receipt selective-disclosure root against receipt payload commitments
- trace-exchange spans and summary hashes against receipt telemetry commitments
- footer-visible evidence span hashes against receipt claim span hashes
- receipt rights decisions against ledger rights decisions
- receipt registry decisions against ledger registry decisions
- payout shares and creator-pool conservation
- transparency proof validity
- receipt membership in the transparency log

## Escrow Settlement Report

Attribution receipts record what happened at response time. They should not be
rewritten after a dispute is resolved. Instead, RDLLM emits a separate
`rdllm-escrow-resolution/v1` settlement report that links:

- the original ledger event and event hash
- the open registry conflict ID
- the registry report hash
- the signed or attested resolution
- the release amount and recipient split
- balances before and after release
- a report hash and optional settlement signature

This separates historical truth from financial finality. The original receipt can
truthfully say "registry-disputed"; the settlement report can later prove which
owner received the escrowed value.

## Interoperability Bundle

The `rdllm-interop/v1` bundle gives downstream systems a standards-aligned export
without forcing them to adopt the internal ledger schema. A bundle contains:

- `receipt_credential`: a VC-shaped attribution credential whose subject commits to
  the receipt hash, event hash, prompt/output hashes, model route, grounding verdict,
  rights status, registry status, attribution-gap verdict, source/claim/source-access
  commitments, trace summary hashes, attribution-gap commitment, disclosure root,
  and payout-share commitment
- `receipt_prov_graph`: a PROV-shaped graph whose entities, activities, agents, and
  relations explain which prompt commitment and source chunks were used, which
  rendered output was generated, which creators are attributed, which claims are
  supported, which attribution-gap decision was made, and which payout shares were
  assigned
- `settlement_credential`: an optional VC-shaped credential for escrow-release
  reports
- `trace_exchange`: an OpenTelemetry-aligned trace artifact bound to the receipt
- `bundle_hash`: a deterministic commitment to the exported bundle

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli interop \
  --receipt artifacts/receipt.json \
  --signing-secret secret \
  --output artifacts/interop_bundle.json

PYTHONPATH=src python3 -m rdllm.cli verify-interop \
  --bundle artifacts/interop_bundle.json \
  --receipt artifacts/receipt.json \
  --signing-secret secret
```

Command:

```bash
PYTHONPATH=src python3 -m rdllm.cli conformance \
  --ledger artifacts/conformance_ledger.json \
  --receipt artifacts/conformance_receipt.json \
  --signing-secret secret \
  --log artifacts/conformance_transparency_log.json \
  --proof artifacts/conformance_proof.json \
  --trace artifacts/conformance_trace_exchange.json \
  --statement artifacts/royalty_statement.json
```

## Certification Report

For procurement, regulator review, or model-provider self-testing, the reference
implementation also emits a certification report:

```bash
PYTHONPATH=src python3 -m rdllm.cli certify \
  --restricted-corpus examples/restricted_corpus.json \
  --conflict-corpus examples/conflict_corpus.json \
  --signing-secret secret \
  --output artifacts/certification_report.json
```

The report records passed and failed cases, `RDLLM-L0` through `RDLLM-L186`
conformance levels, representative event IDs, receipt hashes, a transparency root,
tamper-detection evidence, grounding-quality scores, selective-disclosure evidence,
trace-exchange evidence, royalty-statement evidence, challenge-correction evidence,
derivative-lineage evidence, provenance-benchmark evidence, provider-card evidence,
training-summary evidence, assurance-bundle evidence, universal accountability
witness-quorum evidence, universal grounded-reliance-contract evidence,
universal reliance-correction-ledger evidence,
universal provider-drift-sentinel evidence,
universal production-invocation-admission evidence,
universal source-grounded-response-receipt evidence,
universal distribution-reliance-passport evidence,
universal adversarial-provenance-quorum evidence,
universal procurement-regulatory-reliance-contract evidence,
universal attribution-negotiation-handshake evidence,
universal negotiated-invocation-enforcement evidence,
universal certification-trust-federation evidence,
universal foundation-provider-adoption-pack evidence,
universal industry-adoption-root evidence,
universal reference-implementation-distribution evidence,
universal live-attribution-proof evidence,
universal foundation-model-release-passport evidence,
universal composite-RDLLM-contract evidence,
universal foundation-provider-binding-matrix evidence,
universal provider-conformance-runner-receipt evidence,
universal model-capability-coverage-contract evidence,
answer-provenance-card evidence, source-materialization evidence,
source-access-lease evidence,
content-protocol-ingestion evidence,
universal-content-credential evidence,
universal-composite-RDLLM-profile evidence,
citation-reliance-receipt evidence,
universal-citation-verification evidence, universal-grounded-reuse evidence,
universal-RDLLM-root evidence,
license-transaction-receipt evidence,
foundation-runtime-adapter evidence,
foundation-runtime-router evidence,
foundation-model-deployment-attestation evidence,
universal-composition-receipt evidence,
universal-composition-settlement evidence,
universal-foundation-model-contract evidence,
universal-invocation-guard evidence,
universal-invocation-coverage evidence,
universal-invocation-witness evidence,
grounded-source-footer evidence, source-footer-delivery evidence,
foundation-api-attribution-profile evidence,
client-attribution-enforcement evidence,
persistent-memory-provenance evidence,
private-reasoning-attribution evidence,
post-training-signal-provenance evidence,
attribution-bom evidence,
creator-attribution-audit-index evidence,
creator-attribution-audit-federation evidence,
creator-audit-federation-transparency evidence,
creator-audit-transparency-monitor evidence,
creator-audit-private-watch evidence,
source-freshness-audit evidence,
royalty-abuse-audit evidence,
response-envelope evidence, integration-profile evidence, discovery-manifest
evidence, counterfactual-influence evidence, media-attribution evidence,
evidence-region binding evidence,
model-signal-attribution evidence, rights-remediation evidence,
semantic-text-attribution evidence, attribution-exchange evidence,
conformance-vector evidence, federation-handshake evidence,
portable-attribution-capsule evidence, response-release-gate evidence,
proof-carrying-response evidence, serving-gateway evidence, creator-license-contract
evidence, source-confidence evidence, citation-footer-contract evidence,
payment-rail evidence, creator-payout-receipt evidence,
rendered-attribution-audit evidence, training-memory-provenance evidence,
evidence-locked-generation evidence, emission-evidence-enforcement evidence,
live-emission-witness evidence,
private-audit-challenge evidence, transitive-attribution-flow evidence,
cross-provider-clearinghouse-settlement evidence, verifiable-remittance evidence,
third-party-audit-attestation evidence, usage-revenue-allocation evidence,
finance-ledger-attestation evidence, proof-dependency-graph evidence,
publication-monitor evidence, publication-witness evidence, trust-registry
evidence, certification-attestation evidence, generated-code-attribution evidence,
pre-settlement claim-verification evidence, source-availability evidence,
evidence-sufficiency evidence, counterevidence-adjudication evidence,
release-grounding-closure evidence, answer-claim-coverage evidence,
generation-context-closure evidence, source-boundary-integrity evidence,
decision-provenance evidence, calibrated-attribution-confidence evidence,
source-authenticity evidence, streaming-attribution evidence,
conversation-attribution-continuity evidence, agent-tool-attribution-trajectory,
pinpoint-provenance-antidocument-guard evidence,
citation-identity-metadata-swap-guard evidence,
attribution-consensus-quorum evidence, independent-verifier-quorum evidence,
bonded-verifier-accountability evidence, receipt-transparency-consistency evidence,
watchtower-challenge-settlement evidence, output-provenance-binding evidence,
post-release-discovery evidence, payment-execution-attestation evidence,
payment-rail-authenticity evidence, rendered-attribution-audit evidence,
training-memory-provenance evidence, evidence-locked-generation evidence,
emission-evidence-enforcement evidence, live-emission-witness evidence,
live-emission-transparency evidence, attested-attribution-runtime evidence,
residual-corpus-royalty evidence, valuation-method-audit evidence,
source-farm and sybil settlement-review evidence,
consent-revocation-propagation evidence, evidence-force-calibration evidence,
citation URL-health evidence, composite-foundation-adapter evidence,
foundation-provider-conformance evidence, universal-provider-wire evidence,
universal-accountability-audit-trail evidence, and
a report hash. This follows the same
assurance pattern used by provenance and supply-chain
ecosystems: a product should not merely claim conformance; it should produce
artifacts that an independent verifier can check.

## Provider Attribution Card

Per-response receipts answer "what happened here?" Provider cards answer "what does
this deployment prove across its ledger?" RDLLM defines
`rdllm-provider-attribution-card/v1`:

- provider ID, model ID, model version, issuer, and signature
- bound certification report hash, status, highest level, case counts, and score
- supported evidence channels and public disclosure surfaces
- rights, settlement, escrow, and creator-challenge policies
- aggregate coverage over the ledger, including source-access count, paid source
  count, escrow share count, attributed-access ratio, and average grounding quality
- hash roots for ledger events, source accesses, source references, claim support,
  royalty shares, grounding-quality reports, and attribution-gap reports
- explicit limitations for raw hidden-state disclosure while model-signal telemetry
  is verified through commitments

```bash
PYTHONPATH=src python3 -m rdllm.cli provider-card \
  --ledger artifacts/conformance_ledger.json \
  --certification-report artifacts/certification_report.json \
  --provider provider:reference \
  --model-id rdllm-reference-python \
  --model-version 2026-05 \
  --signing-secret secret \
  --output artifacts/provider_attribution_card.json

PYTHONPATH=src python3 -m rdllm.cli verify-provider-card \
  --ledger artifacts/conformance_ledger.json \
  --certification-report artifacts/certification_report.json \
  --card artifacts/provider_attribution_card.json \
  --signing-secret secret
```

The verifier recomputes the card from the ledger and optional certification report.
It rejects stale certification evidence below `RDLLM-L15`, coverage drift, hash
drift, invalid signatures, and public cards that disclose private prompts, outputs,
source quotes, claim evidence text, or matched text.

## Training Content Summary

Foundation-model providers also need to answer "what did this model train on?"
without dumping private or copyrighted source text. RDLLM defines
`rdllm-training-content-summary/v1`:

- provider ID, model ID, model version, training stage, issuer, and signature
- bindings to the certification report and provider attribution card
- alignment flags for EU GPAI training summaries, Croissant 1.1 usage policy, SPDX
  3 AI/Dataset BOMs, and ODRL rights policy
- aggregate work, creator, chunk, license, source-category, allowed-use,
  prohibited-use, revocation, royalty-duty, and attribution-duty counts
- per-work cohort commitments with content hashes, chunk hash roots, policy
  decisions, and training-value roots, but no work text
- hash roots for work IDs, content hashes, policy decisions, training values,
  certification, and provider card

```bash
PYTHONPATH=src python3 -m rdllm.cli training-summary \
  --certification-report artifacts/certification_report.json \
  --provider-card artifacts/provider_attribution_card.json \
  --provider provider:reference \
  --model-id rdllm-reference-python \
  --model-version 2026-05 \
  --training-stage reference_corpus \
  --signing-secret secret \
  --output artifacts/training_content_summary.json

PYTHONPATH=src python3 -m rdllm.cli verify-training-summary \
  --certification-report artifacts/certification_report.json \
  --provider-card artifacts/provider_attribution_card.json \
  --summary artifacts/training_content_summary.json \
  --signing-secret secret
```

The verifier recomputes the summary from the registered corpus, rejects coverage
drift, requires `RDLLM-L16` certification/provider-card evidence, and fails if the
public summary discloses private work text.

## Answer Provenance Card

A source footer is useful only if the user can verify that it matches the signed
attribution trail. RDLLM defines `rdllm-answer-provenance-card/v1` as a public,
hash-bound card for a single answer:

```bash
PYTHONPATH=src python3 -m rdllm.cli answer-card \
  --ledger artifacts/demo_ledger.json \
  --receipt artifacts/receipt.json \
  --trace artifacts/conformance_trace_exchange.json \
  --signing-secret secret \
  --card artifacts/answer_provenance_card.json

PYTHONPATH=src python3 -m rdllm.cli verify-answer-card \
  --ledger artifacts/demo_ledger.json \
  --receipt artifacts/receipt.json \
  --trace artifacts/conformance_trace_exchange.json \
  --card artifacts/answer_provenance_card.json \
  --signing-secret secret
```

The card binds event hash, rendered-output hash, receipt hash, trace hash, source
labels, claim span hashes, grounding quality, and attribution-gap verdict. It
redacts prompt text, answer text, source quotes, claim text, evidence text, and the
full receipt payload.

## Grounded Source Footer Receipt

The answer footer itself is a verification surface. RDLLM defines
`rdllm-grounded-source-footer/v1` so a client can render sources only when the
visible footer rows replay against source confidence, source availability, exact
evidence-region bindings, citation reliance, license transactions, and public
proof handles:

```bash
PYTHONPATH=src python3 -m rdllm.cli grounded-source-footer \
  --grounded-source-footer-input artifacts/grounded_source_footer_input.json \
  --signing-secret secret \
  --output artifacts/grounded_source_footer.json

PYTHONPATH=src python3 -m rdllm.cli verify-grounded-source-footer \
  --grounded-source-footer-input artifacts/grounded_source_footer_input.json \
  --receipt artifacts/grounded_source_footer.json \
  --signing-secret secret
```

## Source Footer Delivery Receipt

The grounded footer must also survive delivery. RDLLM defines
`rdllm-source-footer-delivery/v1` so clients can verify that the response
envelope, proof-carrying response, copied output hash, serving-gateway egress
hash, source labels, claim span handles, and verifier metadata still match the
grounded footer before display.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-source-footer-delivery \
  --source-footer-delivery-input artifacts/source_footer_delivery_input.json \
  --receipt artifacts/source_footer_delivery.json \
  --signing-secret secret
```

## Foundation API Attribution Profile

Foundation-model clients need a compact API contract, not a bespoke verifier for
every provider. RDLLM defines `rdllm-foundation-attribution-profile/v1` so a
provider can publish the required attribution headers, embedded proof objects,
well-known discovery paths, verifier commands, and fail-closed client policy that
must be present before a response can be rendered as attributed.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-foundation-api-profile \
  --foundation-api-profile-input artifacts/foundation_api_profile_input.json \
  --profile artifacts/foundation_api_profile.json \
  --signing-secret secret
```

## Client Attribution Enforcement Receipt

Provider-declared attribution is not enough if a downstream product can silently
strip the footer or ignore verifier metadata. RDLLM defines
`rdllm-client-attribution-enforcement/v1` so a relying client can prove that it
observed the required response headers, replayed the embedded response envelope
and source-footer-delivery receipt, matched source labels, and failed closed
before rendering an attributed answer.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-client-attribution-enforcement \
  --client-attribution-input artifacts/client_attribution_input.json \
  --receipt artifacts/client_attribution_enforcement.json \
  --signing-secret secret
```

## Persistent Memory Provenance Receipt

Stored assistant, agent, or model memory can become an invisible source for later
answers. RDLLM defines `rdllm-persistent-memory-provenance/v1` so a memory runtime
can prove that memory writes preserve source labels, upstream proof hashes,
license and retention policy, royalty obligations, and delete tombstones, and
that memory reads carry those labels into the verified footer of the later answer.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-persistent-memory-provenance \
  --persistent-memory-input artifacts/persistent_memory_input.json \
  --receipt artifacts/persistent_memory_provenance.json \
  --signing-secret secret
```

## Private Reasoning Attribution Receipt

Private chain-of-thought should not be disclosed, but hidden source influence
cannot be allowed to bypass attribution. RDLLM defines
`rdllm-private-reasoning-attribution/v1` so a provider, router, or agent runtime
can publish commitments for hidden scratchpads, delegated reviewers, and
memory-influenced synthesis. Each private step binds source labels, upstream proof
hashes, output commitments, memory or delegation references, royalty rows, and the
client-rendered output hash. Verification fails if a hidden source label is absent
from the delivered footer, a memory step lacks L106 provenance, a delegation step
lacks model identity, or raw private reasoning text appears in the public receipt.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-private-reasoning-attribution \
  --private-reasoning-input artifacts/private_reasoning_input.json \
  --receipt artifacts/private_reasoning_attribution.json \
  --signing-secret secret
```

## Post-Training Signal Provenance Receipt

Alignment and verifier data can carry source influence into future model behavior
without appearing in a user-facing footer. RDLLM defines
`rdllm-post-training-signal-provenance/v1` so RLHF, RLAIF, RLVR, preference,
reward, verifier, and critique signals prove source-label carry-forward, upstream
L107 and L91 proof hashes, synthetic disclosure, license terms, attestations, and
royalty obligations while keeping raw feedback and reward rationale private.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-post-training-signal-provenance \
  --post-training-signal-input artifacts/post_training_signal_input.json \
  --receipt artifacts/post_training_signal_provenance.json \
  --signing-secret secret
```

## Attribution Bill of Materials

Model, dataset, API, and application releases need one portable artifact that
carries attribution through the supply chain. RDLLM defines
`rdllm-attribution-bom/v1`, a CycloneDX-aligned bill of materials that binds model
identity, source components, notice hashes, license-term hashes, proof artifact
hashes, the proof-dependency graph, provider-card evidence, and L108 post-training
signal provenance without publishing raw private text.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-attribution-bom \
  --attribution-bom-input artifacts/attribution_bom_input.json \
  --bom artifacts/attribution_bom.json \
  --signing-secret secret
```

## Creator Attribution Audit Index

Creators need an audit surface that answers "where was my work used?" across
model-release and answer-level proof artifacts. RDLLM defines
`rdllm-creator-attribution-audit-index/v1`, a query-commitment artifact that
binds model-release ABOM rows, grounded footer rows, source-footer delivery,
post-training signal provenance, source-access leases, license transactions,
model lineage, training summaries, and payout receipts with source-label
namespaces and private-text redaction.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-creator-attribution-audit-index \
  --audit-input artifacts/creator_attribution_audit_index_input.json \
  --index artifacts/creator_attribution_audit_index.json \
  --signing-secret secret
```

## Creator Attribution Audit Federation

Creator-side audit must also work when the creator's work appears across multiple
model providers, search products, assistants, or downstream AI clients. RDLLM
defines `rdllm-creator-attribution-audit-federation/v1`, a cross-provider report
that merges provider-local L110 indexes under one query commitment, scopes source
labels by provider, binds attribution exchange or federation handshake artifacts,
and emits conflict rows when the same work resolves to inconsistent creator
identities.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-creator-attribution-audit-federation \
  --federation-input artifacts/creator_attribution_audit_federation_input.json \
  --report artifacts/creator_attribution_audit_federation.json \
  --signing-secret secret
```

## Creator Audit Federation Transparency

Federated creator queries must be anti-equivocation evidence, not private API
answers that can diverge by customer or regulator. RDLLM defines
`rdllm-creator-attribution-audit-federation-transparency/v1`, a report that proves
the L111 federation hash and every participant L110 index hash are included in
append-only transparency logs with valid inclusion proofs, prefix consistency,
split-view detection, and same-query/provider-set equivocation detection.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-creator-audit-federation-transparency \
  --federation-report artifacts/creator_attribution_audit_federation.json \
  --report artifacts/creator_audit_federation_transparency.json \
  --transparency-log prefix=artifacts/creator_audit_federation_transparency_prefix_log.json \
  --transparency-log latest=artifacts/creator_audit_federation_transparency_log.json \
  --signing-secret secret
```

## Creator Audit Transparency Monitor

The L112 log makes federation answers public, but creators still need an
independent way to watch for appearances and contradictions. RDLLM defines
`rdllm-creator-audit-transparency-monitor/v1`, a hash-only report that scans L112
logs for a creator query commitment, proves matching entry inclusion, reports
newly observed federation and participant-index entries, preserves continuity
with the previous monitor run, and rejects same-query equivocation.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-creator-audit-transparency-monitor \
  --monitor-query artifacts/creator_audit_transparency_monitor_query.json \
  --report artifacts/creator_audit_transparency_monitor.json \
  --transparency-report artifacts/creator_audit_federation_transparency.json \
  --transparency-log prefix=artifacts/creator_audit_federation_transparency_prefix_log.json \
  --transparency-log latest=artifacts/creator_audit_federation_transparency_log.json \
  --signing-secret secret
```

## Creator Audit Private Watch

Public monitor query hashes can become lookup keys. RDLLM therefore defines
`rdllm-creator-audit-private-watch/v1`, a redacted watch receipt that binds an
L113 monitor hash and replaces query, provider-set, federation, participant-index,
provider, and observation identifiers with keyed watch tokens. Creators or
authorized auditors verify it with the private watch input; public viewers see
only monitor bindings, token roots, counts, and privacy commitments.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-creator-audit-private-watch \
  --watch-input artifacts/creator_audit_private_watch_input.json \
  --monitor-report artifacts/creator_audit_transparency_monitor.json \
  --report artifacts/creator_audit_private_watch.json \
  --signing-secret secret
```

Long-form citation strings need a separate rendered-text audit. RDLLM therefore
defines `rdllm-deep-research-citation-audit/v1`, which parses citation markers,
resolves them to materialized source rows, binds cited claims to source and quote
hashes, and rejects reachable links that do not support the attached claim.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-deep-research-citation-audit \
  --audit-input artifacts/deep_research_citation_audit_input.json \
  --report artifacts/deep_research_citation_audit.json \
  --signing-secret secret
```

Current, latest, recent, rapidly changing, and as-of claims also need temporal
source proof. RDLLM therefore defines `rdllm-source-freshness-audit/v1`, which
binds each dynamic claim to selected source-version timestamps, retrieval lag,
validity windows, and fresher-supported-candidate checks.

```bash
PYTHONPATH=src python3 -m rdllm.cli verify-source-freshness-audit \
  --audit-input artifacts/source_freshness_audit_input.json \
  --report artifacts/source_freshness_audit.json \
  --signing-secret secret
```

## Source Verification Report

Footer confidence also requires proof that the cited sources are real registered
materials, not citation-shaped strings. RDLLM defines
`rdllm-source-verification-report/v1` as a public, hash-bound report for cited
source materialization:

```bash
PYTHONPATH=src python3 -m rdllm.cli source-verification \
  --ledger artifacts/demo_ledger.json \
  --answer-card artifacts/answer_provenance_card.json \
  --signing-secret secret \
  --output artifacts/source_verification_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-source-verification \
  --ledger artifacts/demo_ledger.json \
  --answer-card artifacts/answer_provenance_card.json \
  --report artifacts/source_verification_report.json \
  --signing-secret secret
```

The report recomputes source content hashes, quote hashes, claim evidence span
hashes, evidence offsets, visible footer labels, and answer-card bindings against
the registered corpus. It redacts prompt text, answer text, source text, source
quotes, claim text, and evidence text.

## Citation Footer Contract

The footer that users see should itself be reproducible. RDLLM defines
`rdllm-citation-footer-contract/v1` as the client-rendering contract for exact
source rows, claim anchors, confidence labels, license status, royalty status, and
footer hashes:

```bash
PYTHONPATH=src python3 -m rdllm.cli response-envelope \
  --ledger artifacts/demo_ledger.json \
  --answer-card artifacts/answer_provenance_card.json \
  --source-report artifacts/source_verification_report.json \
  --source-confidence-report artifacts/source_confidence_report.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --public-receipt artifacts/public_receipt.json \
  --provider-card artifacts/provider_attribution_card.json \
  --signing-secret secret \
  --output artifacts/response_envelope_base.json

PYTHONPATH=src python3 -m rdllm.cli citation-footer-contract \
  --response-envelope artifacts/response_envelope_base.json \
  --signing-secret secret \
  --output artifacts/citation_footer_contract.json

PYTHONPATH=src python3 -m rdllm.cli verify-citation-footer-contract \
  --contract artifacts/citation_footer_contract.json \
  --response-envelope artifacts/response_envelope_base.json \
  --signing-secret secret
```

The contract can then be embedded in the final response envelope and verified
again against that envelope.

## Response Envelope

For API delivery, RDLLM defines `rdllm-response-envelope/v1` as a signed public
package containing the rendered response and embedded proof artifacts:

```bash
PYTHONPATH=src python3 -m rdllm.cli response-envelope \
  --ledger artifacts/demo_ledger.json \
  --answer-card artifacts/answer_provenance_card.json \
  --source-report artifacts/source_verification_report.json \
  --source-confidence-report artifacts/source_confidence_report.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --source-availability-report artifacts/source_availability_report.json \
  --evidence-sufficiency-report artifacts/evidence_sufficiency_report.json \
  --counterevidence-report artifacts/counterevidence_report.json \
  --answer-claim-coverage-report artifacts/answer_claim_coverage_report.json \
  --public-receipt artifacts/public_receipt.json \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --signing-secret secret \
  --output artifacts/response_envelope.json

PYTHONPATH=src python3 -m rdllm.cli verify-response-envelope \
  --envelope artifacts/response_envelope.json \
  --signing-secret secret
```

The envelope lets a customer verify the visible answer, source labels, span
prefixes, answer card, source verification report, provider disclosure surface, and
certification posture without receiving the private ledger or source corpus.

## Integration Profile

For provider adoption, RDLLM defines `rdllm-integration-profile/v1` as the signed
contract for an RDLLM-compatible model API:

```bash
PYTHONPATH=src python3 -m rdllm.cli integration-profile \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --response-envelope artifacts/response_envelope.json \
  --signing-secret secret \
  --output artifacts/integration_profile.json

PYTHONPATH=src python3 -m rdllm.cli verify-integration-profile \
  --profile artifacts/integration_profile.json \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --response-envelope artifacts/response_envelope.json \
  --signing-secret secret
```

The profile publishes generation and verification endpoints, required headers,
embedded response-envelope artifacts, verifier commands, schema locations, public
surfaces, readiness checks, and proof hashes for the provider card, certification
report, response envelope, and optional assurance bundle. The verifier rejects API
contract drift, provider-surface drift, certification regression, response-envelope
drift, and profile tampering.

## Discovery Manifest

For automatic customer discovery, RDLLM defines `rdllm-discovery-manifest/v1` as a
signed well-known entry point for provider artifacts:

```bash
PYTHONPATH=src python3 -m rdllm.cli discovery-manifest \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --certification-attestation artifacts/certification_attestation.json \
  --integration-profile artifacts/integration_profile.json \
  --response-envelope artifacts/response_envelope.json \
  --assurance-bundle artifacts/assurance_bundle.json \
  --training-summary artifacts/training_content_summary.json \
  --provenance-evaluation-report artifacts/provenance_evaluation_report.json \
  --counterfactual-report artifacts/counterfactual_report.json \
  --media-attribution-report artifacts/media_attribution_report.json \
  --model-signal-report artifacts/model_signal_report.json \
  --rights-remediation-report artifacts/rights_remediation_report.json \
  --semantic-text-attribution-report artifacts/semantic_text_attribution_report.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --source-confidence-report artifacts/source_confidence_report.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --rendered-attribution-audit artifacts/rendered_attribution_audit.json \
  --training-memory-provenance artifacts/training_memory_provenance.json \
  --evidence-locked-generation artifacts/evidence_locked_generation.json \
  --attested-runtime artifacts/attested_runtime.json \
  --claim-source-attribution-report artifacts/claim_source_attribution_report.json \
  --evidence-utility-attribution-report artifacts/evidence_utility_attribution_report.json \
  --parametric-memory-attribution-report artifacts/parametric_memory_attribution_report.json \
  --style-influence-attribution-report artifacts/style_influence_attribution_report.json \
  --model-lineage-attribution-report artifacts/model_lineage_attribution_report.json \
  --black-box-model-provenance-report artifacts/black_box_model_provenance_report.json \
  --attribution-dispute-adjudication-report artifacts/attribution_dispute_adjudication_report.json \
  --post-adjudication-settlement-adjustment-report artifacts/post_adjudication_settlement_adjustment_report.json \
  --private-audit-challenge artifacts/private_audit_challenge.json \
  --revenue-allocation-report artifacts/revenue_allocation_report.json \
  --finance-ledger-attestation artifacts/finance_ledger_attestation.json \
  --proof-dependency-graph artifacts/proof_dependency_graph.json \
  --publication-monitor artifacts/publication_monitor.json \
  --publication-witness artifacts/publication_witness.json \
  --trust-registry artifacts/trust_registry.json \
  --signing-secret secret \
  --output artifacts/discovery_manifest.json

PYTHONPATH=src python3 -m rdllm.cli verify-discovery-manifest \
  --manifest artifacts/discovery_manifest.json \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --certification-attestation artifacts/certification_attestation.json \
  --integration-profile artifacts/integration_profile.json \
  --response-envelope artifacts/response_envelope.json \
  --assurance-bundle artifacts/assurance_bundle.json \
  --training-summary artifacts/training_content_summary.json \
  --provenance-evaluation-report artifacts/provenance_evaluation_report.json \
  --counterfactual-report artifacts/counterfactual_report.json \
  --media-attribution-report artifacts/media_attribution_report.json \
  --model-signal-report artifacts/model_signal_report.json \
  --rights-remediation-report artifacts/rights_remediation_report.json \
  --semantic-text-attribution-report artifacts/semantic_text_attribution_report.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --source-confidence-report artifacts/source_confidence_report.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --rendered-attribution-audit artifacts/rendered_attribution_audit.json \
  --training-memory-provenance artifacts/training_memory_provenance.json \
  --evidence-locked-generation artifacts/evidence_locked_generation.json \
  --attested-runtime artifacts/attested_runtime.json \
  --claim-source-attribution-report artifacts/claim_source_attribution_report.json \
  --evidence-utility-attribution-report artifacts/evidence_utility_attribution_report.json \
  --parametric-memory-attribution-report artifacts/parametric_memory_attribution_report.json \
  --style-influence-attribution-report artifacts/style_influence_attribution_report.json \
  --model-lineage-attribution-report artifacts/model_lineage_attribution_report.json \
  --black-box-model-provenance-report artifacts/black_box_model_provenance_report.json \
  --attribution-dispute-adjudication-report artifacts/attribution_dispute_adjudication_report.json \
  --post-adjudication-settlement-adjustment-report artifacts/post_adjudication_settlement_adjustment_report.json \
  --private-audit-challenge artifacts/private_audit_challenge.json \
  --revenue-allocation-report artifacts/revenue_allocation_report.json \
  --finance-ledger-attestation artifacts/finance_ledger_attestation.json \
  --proof-dependency-graph artifacts/proof_dependency_graph.json \
  --publication-monitor artifacts/publication_monitor.json \
  --publication-witness artifacts/publication_witness.json \
  --trust-registry artifacts/trust_registry.json \
  --signing-secret secret
```

The manifest is designed for `/.well-known/rdllm.json`. It publishes artifact
paths, API contract hashes, schema locations, verifier commands, readiness checks,
and proof hashes without embedding private artifact payloads. The verifier rejects
path tampering, API-contract drift, artifact-hash drift, certification regression,
missing discovery surfaces, and assurance bundles that omit required public proof
artifacts.

## Runtime Federation Handshake

For provider-to-provider use, RDLLM defines `rdllm-federation-handshake/v1` as a
signed runtime negotiation artifact. A downstream model can require a minimum
RDLLM level before it consumes an upstream answer, proof pack, or generated work:

```bash
PYTHONPATH=src python3 -m rdllm.cli federation-handshake \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --integration-profile artifacts/integration_profile.json \
  --discovery-manifest artifacts/discovery_manifest.json \
  --response-envelope artifacts/response_envelope.json \
  --assurance-bundle artifacts/assurance_bundle.json \
  --semantic-text-attribution-report artifacts/semantic_text_attribution_report.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --attribution-exchange artifacts/attribution_exchange.json \
  --conformance-vector-pack artifacts/conformance_vector_pack.json \
  --source-confidence-report artifacts/source_confidence_report.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --private-audit-challenge artifacts/private_audit_challenge.json \
  --training-summary artifacts/training_content_summary.json \
  --provenance-evaluation-report artifacts/provenance_evaluation_report.json \
  --counterfactual-report artifacts/counterfactual_report.json \
  --media-attribution-report artifacts/media_attribution_report.json \
  --model-signal-report artifacts/model_signal_report.json \
  --rights-remediation-report artifacts/rights_remediation_report.json \
  --requester provider:downstream-demo \
  --requester-model-id model:downstream-demo \
  --requester-model-version 2026-05 \
  --minimum-level RDLLM-L43 \
  --signing-secret secret \
  --output artifacts/federation_handshake.json

PYTHONPATH=src python3 -m rdllm.cli verify-federation-handshake \
  --handshake artifacts/federation_handshake.json \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --integration-profile artifacts/integration_profile.json \
  --discovery-manifest artifacts/discovery_manifest.json \
  --response-envelope artifacts/response_envelope.json \
  --assurance-bundle artifacts/assurance_bundle.json \
  --semantic-text-attribution-report artifacts/semantic_text_attribution_report.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --attribution-exchange artifacts/attribution_exchange.json \
  --conformance-vector-pack artifacts/conformance_vector_pack.json \
  --source-confidence-report artifacts/source_confidence_report.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --private-audit-challenge artifacts/private_audit_challenge.json \
  --training-summary artifacts/training_content_summary.json \
  --provenance-evaluation-report artifacts/provenance_evaluation_report.json \
  --counterfactual-report artifacts/counterfactual_report.json \
  --media-attribution-report artifacts/media_attribution_report.json \
  --model-signal-report artifacts/model_signal_report.json \
  --rights-remediation-report artifacts/rights_remediation_report.json \
  --signing-secret secret
```

The handshake binds requester identity, provider identity, requested level,
negotiated level, required public artifacts, required runtime headers, source-footer
relay, escrow relay, and downgrade policy. The verifier rejects stale hashes,
missing attribution-exchange manifests, missing conformance vectors, unsigned
material changes, disabled relay obligations, and private prompt, output, matched,
source, or hidden-state leakage.

## Portable Attribution Capsule

For copied, reposted, exported, or metadata-wrapped AI outputs, RDLLM defines
`rdllm-attribution-capsule/v1` as a signed proof object that travels with the
content without embedding private text:

```bash
PYTHONPATH=src python3 -m rdllm.cli attribution-capsule \
  --response-envelope artifacts/response_envelope.json \
  --federation-handshake artifacts/federation_handshake.json \
  --attribution-exchange artifacts/attribution_exchange.json \
  --conformance-vector-pack artifacts/conformance_vector_pack.json \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --integration-profile artifacts/integration_profile.json \
  --discovery-manifest artifacts/discovery_manifest.json \
  --assurance-bundle artifacts/assurance_bundle.json \
  --semantic-text-attribution-report artifacts/semantic_text_attribution_report.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --source-confidence-report artifacts/source_confidence_report.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --private-audit-challenge artifacts/private_audit_challenge.json \
  --training-summary artifacts/training_content_summary.json \
  --provenance-evaluation-report artifacts/provenance_evaluation_report.json \
  --counterfactual-report artifacts/counterfactual_report.json \
  --media-attribution-report artifacts/media_attribution_report.json \
  --model-signal-report artifacts/model_signal_report.json \
  --rights-remediation-report artifacts/rights_remediation_report.json \
  --signing-secret secret \
  --output artifacts/attribution_capsule.json

PYTHONPATH=src python3 -m rdllm.cli verify-attribution-capsule \
  --capsule artifacts/attribution_capsule.json \
  --response-envelope artifacts/response_envelope.json \
  --federation-handshake artifacts/federation_handshake.json \
  --attribution-exchange artifacts/attribution_exchange.json \
  --conformance-vector-pack artifacts/conformance_vector_pack.json \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --integration-profile artifacts/integration_profile.json \
  --discovery-manifest artifacts/discovery_manifest.json \
  --assurance-bundle artifacts/assurance_bundle.json \
  --semantic-text-attribution-report artifacts/semantic_text_attribution_report.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --source-confidence-report artifacts/source_confidence_report.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --private-audit-challenge artifacts/private_audit_challenge.json \
  --training-summary artifacts/training_content_summary.json \
  --provenance-evaluation-report artifacts/provenance_evaluation_report.json \
  --counterfactual-report artifacts/counterfactual_report.json \
  --media-attribution-report artifacts/media_attribution_report.json \
  --model-signal-report artifacts/model_signal_report.json \
  --rights-remediation-report artifacts/rights_remediation_report.json \
  --signing-secret secret
```

The capsule binds the rendered-output hash, response envelope, federation
handshake, exchange manifest, conformance vector pack, provider card,
certification report, discovery manifest, runtime capsule headers, copyable footer
marker, delivered-body hash, C2PA-compatible assertion pointer, and SCITT-like
statement subject. The verifier rejects stale hashes, marker loss, copied-body
tampering, missing capsule surfaces, signature drift, or prompt, answer, matched,
source, hidden-state, or private ledger leakage.

## Transitive Attribution Report

When a capsule-bearing copied answer becomes downstream source material, RDLLM
defines `rdllm-transitive-attribution-report/v1` as the second-hop settlement
artifact:

```bash
PYTHONPATH=src python3 -m rdllm.cli transitive-attribution-report \
  --upstream-capsule artifacts/attribution_capsule.json \
  --upstream-response-envelope artifacts/response_envelope.json \
  --downstream-ledger artifacts/downstream_ledger.json \
  --copied-output-file artifacts/copied_output.txt \
  --pass-through-rate 0.70 \
  --signing-secret secret \
  --output artifacts/transitive_attribution_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-transitive-attribution-report \
  --report artifacts/transitive_attribution_report.json \
  --upstream-capsule artifacts/attribution_capsule.json \
  --upstream-response-envelope artifacts/response_envelope.json \
  --downstream-ledger artifacts/downstream_ledger.json \
  --copied-output-file artifacts/copied_output.txt \
  --signing-secret secret
```

The report verifies the copied marker and body hash, carries upstream answer-card
source rows forward, and splits the configured pass-through pool across original
owners. It rejects marker loss, body drift, source-row deletion, payout
non-conservation, and private copied-output leakage.

## Clearinghouse Report

For settlement periods that include multiple providers or second-hop copied-output
reuse, RDLLM defines `rdllm-clearinghouse-report/v1`:

```bash
PYTHONPATH=src python3 -m rdllm.cli clearinghouse-report \
  --statement artifacts/royalty_statement.json \
  --transitive-report artifacts/transitive_attribution_report.json \
  --signing-secret secret \
  --output artifacts/clearinghouse_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-clearinghouse-report \
  --report artifacts/clearinghouse_report.json \
  --statement artifacts/royalty_statement.json \
  --transitive-report artifacts/transitive_attribution_report.json \
  --signing-secret secret
```

The report verifies submitted artifact hashes, normalizes obligations into
payable, escrow, and held rows, conserves settlement totals, and holds duplicate or
overlapping submissions instead of paying them twice.

## Remittance Report

After clearing, RDLLM defines `rdllm-remittance-report/v1` to produce
instruction-only payment rows without exposing raw creator payment accounts:

```bash
PYTHONPATH=src python3 -m rdllm.cli remittance-report \
  --clearinghouse-report artifacts/clearinghouse_report.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --payment-rail iso20022-pain001-compatible \
  --signing-secret secret \
  --output artifacts/remittance_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-remittance-report \
  --report artifacts/remittance_report.json \
  --clearinghouse-report artifacts/clearinghouse_report.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --signing-secret secret
```

The report binds each payment instruction to the clearinghouse settlement row,
creator license contract, payout-account hash, origin hashes, chunk IDs, end-to-end
ID, and remittance reference. It preserves clearinghouse holds and explicitly does
not claim that regulated bank settlement already happened.

## Payment Execution Report

After remittance, RDLLM defines `rdllm-payment-execution-report/v1` to prove that
instruction-only payment rows were reconciled against external processor or escrow
settlement records before settlement is described as executed:

```bash
PYTHONPATH=src python3 -m rdllm.cli payment-execution-report \
  --remittance-report artifacts/remittance_report.json \
  --processor-records artifacts/payment_processor_records.json \
  --signing-secret secret \
  --output artifacts/payment_execution_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-payment-execution-report \
  --report artifacts/payment_execution_report.json \
  --remittance-report artifacts/remittance_report.json \
  --processor-records artifacts/payment_processor_records.json \
  --signing-secret secret
```

The report verifies amount, currency, end-to-end ID, payout or escrow account hash,
settlement status, processor-record hash, and settlement-batch hash for every
payment and escrow instruction. It rejects duplicate or unmatched processor rows,
preserves clearinghouse holds as unpaid carryforward rows, and blocks raw bank,
tax, customer, or private payment fields from entering the public artifact.

## Payment Rail Attestation

After payment execution, RDLLM defines `rdllm-payment-rail-attestation/v1` to prove
that the settlement batches were signed by registered external payment or escrow
processors:

```bash
PYTHONPATH=src python3 -m rdllm.cli processor-batch-attestations \
  --payment-execution-report artifacts/payment_execution_report.json \
  --processor-secret processor:rdllm-reference-ach=processor-reference-ach-secret \
  --processor-secret escrow:rdllm-reference-registry=escrow-reference-registry-secret \
  --output artifacts/processor_batch_attestations.json

PYTHONPATH=src python3 -m rdllm.cli payment-rail-attestation \
  --payment-execution-report artifacts/payment_execution_report.json \
  --trust-registry artifacts/trust_registry.json \
  --processor-attestations artifacts/processor_batch_attestations.json \
  --processor-secret processor:rdllm-reference-ach=processor-reference-ach-secret \
  --processor-secret escrow:rdllm-reference-registry=escrow-reference-registry-secret \
  --signing-secret secret \
  --output artifacts/payment_rail_attestation.json

PYTHONPATH=src python3 -m rdllm.cli verify-payment-rail-attestation \
  --report artifacts/payment_rail_attestation.json \
  --payment-execution-report artifacts/payment_execution_report.json \
  --trust-registry artifacts/trust_registry.json \
  --processor-attestations artifacts/processor_batch_attestations.json \
  --processor-secret processor:rdllm-reference-ach=processor-reference-ach-secret \
  --processor-secret escrow:rdllm-reference-registry=escrow-reference-registry-secret \
  --signing-secret secret
```

The attestation rejects unregistered processors, unauthorized processor roles,
missing or invalid processor signatures, uncovered execution batches, amount or
status drift, and raw private payment fields. Public verifiers see registry rows,
hashes, signatures, counts, totals, and batch coverage, not bank or customer data.

Creator-facing payout receipts bind those signed rail batches back to the work and
settlement row a creator can inspect:

```bash
PYTHONPATH=src python3 -m rdllm.cli creator-payout-receipts \
  --clearinghouse-report artifacts/clearinghouse_report.json \
  --remittance-report artifacts/remittance_report.json \
  --payment-execution-report artifacts/payment_execution_report.json \
  --payment-rail-attestation artifacts/payment_rail_attestation.json \
  --signing-secret secret \
  --output artifacts/creator_payout_receipt_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-creator-payout-receipts \
  --report artifacts/creator_payout_receipt_report.json \
  --clearinghouse-report artifacts/clearinghouse_report.json \
  --remittance-report artifacts/remittance_report.json \
  --payment-execution-report artifacts/payment_execution_report.json \
  --payment-rail-attestation artifacts/payment_rail_attestation.json \
  --signing-secret secret
```

The receipt report exposes paid, escrowed, or held status, settlement hashes,
execution hashes, signed batch coverage, counts, and totals, not prompts, generated
text, source text, customer records, tax records, or raw payout accounts.

The exact displayed Markdown can also be audited so user-visible citations are
not merely decorative footer text:

```bash
PYTHONPATH=src python3 -m rdllm.cli rendered-attribution-audit \
  --response-envelope artifacts/response_envelope.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --source-availability-report artifacts/source_availability_report.json \
  --evidence-sufficiency-report artifacts/evidence_sufficiency_report.json \
  --counterevidence-report artifacts/counterevidence_report.json \
  --answer-claim-coverage-report artifacts/answer_claim_coverage_report.json \
  --signing-secret secret \
  --output artifacts/rendered_attribution_audit.json

PYTHONPATH=src python3 -m rdllm.cli verify-rendered-attribution-audit \
  --report artifacts/rendered_attribution_audit.json \
  --response-envelope artifacts/response_envelope.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --source-availability-report artifacts/source_availability_report.json \
  --evidence-sufficiency-report artifacts/evidence_sufficiency_report.json \
  --counterevidence-report artifacts/counterevidence_report.json \
  --answer-claim-coverage-report artifacts/answer_claim_coverage_report.json \
  --signing-secret secret
```

The rendered attribution audit exposes line hashes, source labels, source URIs,
content-hash prefixes, claim span prefixes, and verification booleans. It rejects
answers whose inline source markers, footer rows, or claim-evidence spans drift
from the signed response envelope and grounding proof chain.

Registered training-memory reuse can also be audited against the exact rendered
answer:

```bash
PYTHONPATH=src python3 -m rdllm.cli training-memory-provenance \
  --response-envelope artifacts/response_envelope.json \
  --rendered-attribution-audit artifacts/rendered_attribution_audit.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --training-content-summary artifacts/training_content_summary.json \
  --source-snapshots artifacts/training_memory_snapshots.json \
  --signing-secret secret \
  --output artifacts/training_memory_provenance.json

PYTHONPATH=src python3 -m rdllm.cli verify-training-memory-provenance \
  --report artifacts/training_memory_provenance.json \
  --response-envelope artifacts/response_envelope.json \
  --rendered-attribution-audit artifacts/rendered_attribution_audit.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --training-content-summary artifacts/training_content_summary.json \
  --source-snapshots artifacts/training_memory_snapshots.json \
  --signing-secret secret
```

The training-memory provenance report exposes only snapshot commitments, matched
sequence hashes, token counts, coverage ratios, visible source labels, and
remediation rows. It rejects hidden memorized registered spans before display.

Evidence-locked generation proves that citations and claim evidence were bound
before the answer was emitted:

```bash
PYTHONPATH=src python3 -m rdllm.cli evidence-locked-generation \
  --response-envelope artifacts/response_envelope.json \
  --answer-claim-coverage-report artifacts/answer_claim_coverage_report.json \
  --generation-context-closure-report artifacts/generation_context_closure_report.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --rendered-attribution-audit artifacts/rendered_attribution_audit.json \
  --training-memory-provenance artifacts/training_memory_provenance.json \
  --lock-created-at 2026-05-30T23:59:59Z \
  --generation-started-at 2026-05-31T00:00:00Z \
  --signing-secret secret \
  --output artifacts/evidence_locked_generation.json

PYTHONPATH=src python3 -m rdllm.cli verify-evidence-locked-generation \
  --report artifacts/evidence_locked_generation.json \
  --response-envelope artifacts/response_envelope.json \
  --answer-claim-coverage-report artifacts/answer_claim_coverage_report.json \
  --generation-context-closure-report artifacts/generation_context_closure_report.json \
  --citation-footer-contract artifacts/citation_footer_contract.json \
  --rendered-attribution-audit artifacts/rendered_attribution_audit.json \
  --training-memory-provenance artifacts/training_memory_provenance.json \
  --signing-secret secret
```

The served and streamed response path can then be bound to those locks:

```bash
PYTHONPATH=src python3 -m rdllm.cli emission-evidence-enforcement \
  --response-envelope artifacts/response_envelope.json \
  --answer-claim-coverage-report artifacts/answer_claim_coverage_report.json \
  --evidence-locked-generation artifacts/evidence_locked_generation.json \
  --proof-carrying-response artifacts/proof_carrying_response.json \
  --serving-gateway-report artifacts/serving_gateway_report.json \
  --streaming-attribution-manifest artifacts/streaming_attribution_manifest.json \
  --signing-secret secret \
  --output artifacts/emission_evidence_enforcement.json

PYTHONPATH=src python3 -m rdllm.cli verify-emission-evidence-enforcement \
  --report artifacts/emission_evidence_enforcement.json \
  --response-envelope artifacts/response_envelope.json \
  --answer-claim-coverage-report artifacts/answer_claim_coverage_report.json \
  --evidence-locked-generation artifacts/evidence_locked_generation.json \
  --proof-carrying-response artifacts/proof_carrying_response.json \
  --serving-gateway-report artifacts/serving_gateway_report.json \
  --streaming-attribution-manifest artifacts/streaming_attribution_manifest.json \
  --signing-secret secret
```

The stream boundary can also be witnessed independently before and after emission:

```bash
PYTHONPATH=src python3 -m rdllm.cli live-emission-witness \
  --emission-evidence-enforcement artifacts/emission_evidence_enforcement.json \
  --streaming-attribution-manifest artifacts/streaming_attribution_manifest.json \
  --witness witness-a:secret-a \
  --witness witness-b:secret-b \
  --witness witness-c:secret-c \
  --signing-secret secret \
  --output artifacts/live_emission_witness.json

PYTHONPATH=src python3 -m rdllm.cli verify-live-emission-witness \
  --report artifacts/live_emission_witness.json \
  --emission-evidence-enforcement artifacts/emission_evidence_enforcement.json \
  --streaming-attribution-manifest artifacts/streaming_attribution_manifest.json \
  --witness witness-a:secret-a \
  --witness witness-b:secret-b \
  --witness witness-c:secret-c \
  --signing-secret secret
```

Before a grounded response is emitted, RDLLM can also publish a response release
gate. This is the serving-boundary artifact: it blocks display unless the response
envelope, visible footer labels, claim spans, source materialization, attribution
capsule, provider public surface, and minimum upstream certification all verify.

```bash
PYTHONPATH=src python3 -m rdllm.cli release-gate \
  --response-envelope artifacts/response_envelope.json \
  --attribution-capsule artifacts/attribution_capsule.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --signing-secret secret \
  --output artifacts/release_gate.json

PYTHONPATH=src python3 -m rdllm.cli verify-release-gate \
  --gate artifacts/release_gate.json \
  --response-envelope artifacts/response_envelope.json \
  --attribution-capsule artifacts/attribution_capsule.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --signing-secret secret
```

After the gate emits, RDLLM can publish a decision provenance graph. This is a
post-release artifact: it binds claim grounding, visible source-footers, royalty
participation, and the release decision to authorized proof channels without
becoming an input to the attribution capsule.

```bash
PYTHONPATH=src python3 -m rdllm.cli decision-provenance-report \
  --response-envelope artifacts/response_envelope.json \
  --release-gate artifacts/release_gate.json \
  --trace-exchange artifacts/conformance_trace_exchange.json \
  --attribution-capsule artifacts/attribution_capsule.json \
  --signing-secret secret \
  --output artifacts/decision_provenance_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-decision-provenance-report \
  --report artifacts/decision_provenance_report.json \
  --response-envelope artifacts/response_envelope.json \
  --release-gate artifacts/release_gate.json \
  --trace-exchange artifacts/conformance_trace_exchange.json \
  --attribution-capsule artifacts/attribution_capsule.json \
  --signing-secret secret
```

RDLLM can then publish calibrated attribution confidence as a second
post-release artifact. It binds visible claim, footer, and payout decisions to
benchmark-backed lower confidence bounds so users can distinguish verified
attribution from uncertain or escrowed attribution.

```bash
PYTHONPATH=src python3 -m rdllm.cli calibrated-attribution-report \
  --response-envelope artifacts/response_envelope.json \
  --source-confidence-report artifacts/source_confidence_report.json \
  --evidence-sufficiency-report artifacts/evidence_sufficiency_report.json \
  --provenance-evaluation-report artifacts/provenance_evaluation_report.json \
  --decision-provenance-report artifacts/decision_provenance_report.json \
  --release-gate artifacts/release_gate.json \
  --trace-exchange artifacts/conformance_trace_exchange.json \
  --attribution-capsule artifacts/attribution_capsule.json \
  --signing-secret secret \
  --output artifacts/calibrated_attribution_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-calibrated-attribution-report \
  --report artifacts/calibrated_attribution_report.json \
  --response-envelope artifacts/response_envelope.json \
  --source-confidence-report artifacts/source_confidence_report.json \
  --evidence-sufficiency-report artifacts/evidence_sufficiency_report.json \
  --provenance-evaluation-report artifacts/provenance_evaluation_report.json \
  --decision-provenance-report artifacts/decision_provenance_report.json \
  --release-gate artifacts/release_gate.json \
  --trace-exchange artifacts/conformance_trace_exchange.json \
  --attribution-capsule artifacts/attribution_capsule.json \
  --signing-secret secret
```

The final serving-boundary object is a proof-carrying response. It releases the
answer only when the embedded gate verifies; otherwise it returns a held-response
notice and suppresses the original answer.

```bash
PYTHONPATH=src python3 -m rdllm.cli proof-carrying-response \
  --response-envelope artifacts/response_envelope.json \
  --attribution-capsule artifacts/attribution_capsule.json \
  --release-gate artifacts/release_gate.json \
  --creator-license-contract artifacts/creator_license_contract.json \
  --provider-card artifacts/provider_attribution_card.json \
  --certification-report artifacts/certification_report.json \
  --signing-secret secret \
  --output artifacts/proof_carrying_response.json

PYTHONPATH=src python3 -m rdllm.cli verify-proof-carrying-response \
  --response artifacts/proof_carrying_response.json \
  --signing-secret secret
```

The production egress proof is a serving gateway report. It hash-commits the
private prompt and raw model output while proving the delivered output equals the
proof-carrying response copied output.

```bash
PYTHONPATH=src python3 -m rdllm.cli serving-gateway-report \
  --proof-response artifacts/proof_carrying_response.json \
  --request-id req_demo_gateway \
  --provider provider:rdllm-reference \
  --model-id model:rdllm-reference \
  --model-version 2026-05 \
  --route-id route:default \
  --signing-secret secret \
  --output artifacts/serving_gateway_report.json

PYTHONPATH=src python3 -m rdllm.cli verify-serving-gateway-report \
  --report artifacts/serving_gateway_report.json \
  --signing-secret secret
```

The pre-use rights proof is a creator license contract. It binds registered works
to allowed AI uses, attribution duties, royalty duties, revocation state, and
hashed payout-account commitments without publishing work text or raw payout
accounts.

```bash
PYTHONPATH=src python3 -m rdllm.cli creator-license-contract \
  --provider provider:rdllm-reference \
  --signing-secret secret \
  --output artifacts/creator_license_contract.json

PYTHONPATH=src python3 -m rdllm.cli verify-creator-license-contract \
  --contract artifacts/creator_license_contract.json \
  --signing-secret secret
```

## Assurance Bundle

For public confidence, the proof pack itself should be verifiable without exposing
private event or corpus text. RDLLM defines `rdllm-assurance-bundle/v1` as a signed,
hash-only publication artifact covering receipts, traces, statements, challenges,
answer cards, source verification reports, source confidence reports, citation
footer contracts, evidence-force calibration reports, rendered attribution audits,
private audit challenges, response envelopes, integration profiles, provider cards,
training summaries, derivative-lineage reports,
provenance-evaluation reports, counterfactual-influence reports, media-attribution
reports, model-signal reports, rights-remediation reports, creator-license
contracts, revenue-allocation reports, finance-ledger attestations, certification
reports, and certification attestations. Downstream settlement artifacts such as
transitive-attribution, clearinghouse, and remittance reports are generated after
discovery and bound by their own verifiers plus the third-party audit attestation:

```bash
PYTHONPATH=src python3 -m rdllm.cli assurance-bundle \
  --artifact certification:certification_report:artifacts/certification_report.json \
  --artifact certification_attestation:certification_attestation:artifacts/certification_attestation.json \
  --artifact lineage_report:lineage_report:artifacts/lineage_report.json \
  --artifact provenance_evaluation:provenance_evaluation_report:artifacts/provenance_evaluation_report.json \
  --artifact counterfactual:counterfactual_influence_report:artifacts/counterfactual_report.json \
  --artifact media_attribution:media_attribution_report:artifacts/media_attribution_report.json \
  --artifact model_signal:model_signal_attribution_report:artifacts/model_signal_report.json \
  --artifact rights_remediation:rights_remediation_report:artifacts/rights_remediation_report.json \
  --artifact semantic_text:semantic_text_attribution_report:artifacts/semantic_text_attribution_report.json \
  --artifact integration_profile:integration_profile:artifacts/integration_profile.json \
  --artifact response_envelope:response_envelope:artifacts/response_envelope.json \
  --artifact answer_card:answer_provenance_card:artifacts/answer_provenance_card.json \
  --artifact source_verification:source_verification_report:artifacts/source_verification_report.json \
  --artifact source_confidence:source_confidence_report:artifacts/source_confidence_report.json \
  --artifact citation_footer:citation_footer_contract:artifacts/citation_footer_contract.json \
  --artifact rendered_attribution_audit:rendered_attribution_audit:artifacts/rendered_attribution_audit.json \
  --artifact training_memory_provenance:training_memory_provenance:artifacts/training_memory_provenance.json \
  --artifact creator_license:creator_license_contract:artifacts/creator_license_contract.json \
  --artifact provider_card:provider_attribution_card:artifacts/provider_attribution_card.json \
  --artifact training_summary:training_content_summary:artifacts/training_content_summary.json \
  --artifact receipt:attribution_receipt:artifacts/conformance_receipt.json \
  --artifact trace:trace_exchange:artifacts/conformance_trace_exchange.json \
  --artifact statement:royalty_statement:artifacts/royalty_statement.json \
  --artifact challenge:attribution_challenge:artifacts/attribution_challenge_report.json \
  --artifact private_audit:private_audit_challenge:artifacts/private_audit_challenge.json \
  --artifact revenue_allocation:revenue_allocation_report:artifacts/revenue_allocation_report.json \
  --artifact finance_ledger:finance_ledger_attestation:artifacts/finance_ledger_attestation.json \
  --signing-secret secret \
  --output artifacts/assurance_bundle.json

PYTHONPATH=src python3 -m rdllm.cli verify-assurance-bundle \
  --bundle artifacts/assurance_bundle.json \
  --artifact certification:certification_report:artifacts/certification_report.json \
  --artifact certification_attestation:certification_attestation:artifacts/certification_attestation.json \
  --artifact lineage_report:lineage_report:artifacts/lineage_report.json \
  --artifact provenance_evaluation:provenance_evaluation_report:artifacts/provenance_evaluation_report.json \
  --artifact counterfactual:counterfactual_influence_report:artifacts/counterfactual_report.json \
  --artifact media_attribution:media_attribution_report:artifacts/media_attribution_report.json \
  --artifact model_signal:model_signal_attribution_report:artifacts/model_signal_report.json \
  --artifact rights_remediation:rights_remediation_report:artifacts/rights_remediation_report.json \
  --artifact semantic_text:semantic_text_attribution_report:artifacts/semantic_text_attribution_report.json \
  --artifact integration_profile:integration_profile:artifacts/integration_profile.json \
  --artifact response_envelope:response_envelope:artifacts/response_envelope.json \
  --artifact answer_card:answer_provenance_card:artifacts/answer_provenance_card.json \
  --artifact source_verification:source_verification_report:artifacts/source_verification_report.json \
  --artifact source_confidence:source_confidence_report:artifacts/source_confidence_report.json \
  --artifact citation_footer:citation_footer_contract:artifacts/citation_footer_contract.json \
  --artifact rendered_attribution_audit:rendered_attribution_audit:artifacts/rendered_attribution_audit.json \
  --artifact training_memory_provenance:training_memory_provenance:artifacts/training_memory_provenance.json \
  --artifact creator_license:creator_license_contract:artifacts/creator_license_contract.json \
  --artifact provider_card:provider_attribution_card:artifacts/provider_attribution_card.json \
  --artifact training_summary:training_content_summary:artifacts/training_content_summary.json \
  --artifact receipt:attribution_receipt:artifacts/conformance_receipt.json \
  --artifact trace:trace_exchange:artifacts/conformance_trace_exchange.json \
  --artifact statement:royalty_statement:artifacts/royalty_statement.json \
  --artifact challenge:attribution_challenge:artifacts/attribution_challenge_report.json \
  --artifact private_audit:private_audit_challenge:artifacts/private_audit_challenge.json \
  --artifact revenue_allocation:revenue_allocation_report:artifacts/revenue_allocation_report.json \
  --artifact finance_ledger:finance_ledger_attestation:artifacts/finance_ledger_attestation.json \
  --signing-secret secret
```

The verifier recomputes artifact hashes, Merkle roots, inclusion proofs, and
signatures, and rejects missing proofs or changed payload hashes.

## Provider Requirements

A provider adopting this protocol should:

- register source content with content hashes and license terms
- express source rights as machine-readable allowed uses, prohibited uses,
  jurisdictions, minimum royalty rates, and revocation state
- attach stable source IDs to retrieved chunks
- emit source-access records for retrieval and text-match paths
- export OpenTelemetry-aligned trace exchanges for source access, citations, and
  claim support
- render citations as constrained source labels
- render citation footer contracts exactly, including confidence, license, royalty,
  and claim-anchor rows
- run claim-level support checks before final response delivery
- emit grounding-quality scores for source accessibility, citation integrity,
  evidence relevance, fact support, policy alignment, and payout alignment
- emit attribution-gap reports that reconcile accessed, cited, paid, and escrowed
  sources
- emit counterfactual influence reports that ablate credited works and prove source
  removal, payout reallocation, and influence margins
- emit media attribution reports that match registered image, audio, video, 3D, and
  text-shaped signatures to owners or escrow without exposing raw media
- emit model signal attribution reports that bind provider-private log-probability,
  activation, gradient, attention, and memorization telemetry to an explicit
  attribution contract, owner payouts, and model-signal escrow without exposing raw
  hidden states or logits
- emit rights remediation reports that preserve historical event hashes, enforce
  updated consent and revocation state for future use, and verify rights-conflict
  escrow without exposing work text or private ledger payloads
- emit ownership registry reports for duplicate and near-duplicate claim detection
- emit an attribution receipt for every monetized usage event
- route traced-but-unlicensed use to rights-conflict escrow
- route disputed ownership claims to registry-dispute escrow
- release disputed escrow only through a verifiable settlement report
- export VC-shaped credentials and PROV-shaped answer graphs for interoperability
- export selective-disclosure packages for public trust without private-data leakage
- publish periodic royalty statements that bind ledger, receipt, trace, source-usage,
  creator, escrow, and payout commitments without private text disclosure
- accept and verify attribution challenge reports for contested omissions or weak
  attribution, with non-rewrite correction remedies
- publish derivative lineage reports so summaries, synthetic datasets, tool outputs,
  and transformed corpora preserve upstream creator obligations
- publish answer provenance cards that bind visible source footers to receipt and
  trace evidence without exposing private text
- publish source verification reports that prove cited source hashes, quotes, and
  evidence span hashes materialize from registered content without exposing private
  source or evidence text
- publish response envelopes that package rendered answers with public verification
  artifacts for API customers
- publish integration profiles that declare the API contract, verifier commands,
  schemas, public surfaces, readiness checks, and bound proof hashes
- publish discovery manifests at a well-known path so customers can find and verify
  provider proof surfaces automatically
- publish live capability discovery contracts so provider model/capability claims
  are tied to current official or attested provider evidence before source footers
  and settlements rely on them
- publish native source annotation contracts so provider-specific citation and
  grounding metadata is normalized into the exact footer rows users see
- publish attribution exchange manifests so downstream AI providers can import
  upstream proof hashes, preserve source footer rows, and relay escrow obligations
  without seeing private prompt, output, matched, or source text
- publish conformance vector packs so independent providers can reproduce expected
  RDLLM outcomes and negative drift failures before claiming compatibility
- publish federation handshakes so downstream AI systems can negotiate a minimum
  RDLLM level, verify required public artifacts, preserve source footers, relay
  escrow, and reject downgrades before provider-to-provider use
- publish attribution capsules so copied answers, reposted responses, exported
  reports, and generated content metadata keep a verifiable output-hash and
  proof-chain pointer outside the original AI product
- publish transitive attribution reports so downstream reuse of copied RDLLM output
  preserves the upstream capsule, source rows, copied-body hash, and pass-through
  settlement obligations
- publish clearinghouse reports so provider statements and transitive reports can
  be reconciled into duplicate-safe payable, escrow, and held settlement rows
- publish remittance reports so cleared obligations become instruction-only
  payment rows with payout-account hashes, reconciliation references, and preserved
  holds before funds move through external payment processors
- publish third-party audit attestations so independent reviewers can replay the
  public proof pack and cite a hash-only readiness artifact without seeing private
  prompts, answers, source text, evidence text, or payout accounts
- publish revenue allocation reports so event-level gross revenue can be traced to
  conserved billing, advertising, subscription, API, enterprise, or marketplace
  source pools before payout, clearing, and remittance
- publish finance ledger attestations so those revenue pools can be reconciled to
  hash-only external finance exports without disclosing customer records, invoice
  text, payment details, prompts, outputs, or source text
- publish proof dependency graphs so auditors and downstream providers can replay
  the proof pack in a deterministic topological order and reject dependency cycles
- publish publication monitors so public proof surfaces are checkpointed over time,
  required-artifact removal is detected, and certification regressions are blocked
- publish publication witnesses so monitor checkpoints are independently cosigned,
  quorum-checked, and rejected when split-view histories appear
- publish trust registries so signer and witness keys are active, rotated,
  revocation-checked, and independently replayable
- publish a provider attribution card that binds certification, coverage, evidence
  channels, disclosure surfaces, limitations, and privacy-safe evidence roots
- publish training-content summaries that bind corpus categories, rights coverage,
  license/use counts, policy roots, content-hash roots, and training-value
  commitments
- publish assurance bundles that bind public proof-pack hashes, Merkle roots, and
  inclusion proofs without disclosing private prompt, answer, source, evidence, or
  work text
- publish public receipts or transparency log roots at regular intervals
- support private audit exports for creators and regulators
- require copied-output or capsule-header submissions when downstream systems use
  AI-generated content as source material
- escrow creator pool value when no owner can be traced

## Why This Is Foundation-Model Grade

Foundation models need a common attribution layer that works across base training,
fine-tuning, retrieval, tools, agents, and generated outputs. This protocol turns
attribution from an internal analytics problem into an interoperable runtime receipt.
That is the missing layer between source-grounded generation, creator compensation,
and institutional trust.
