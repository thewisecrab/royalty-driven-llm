# Royalty Driven LLM Mechanism

## Summary

A Royalty Driven LLM is a platform-agnostic attribution and settlement layer where
each monetized AI usage event creates an auditable royalty record. It is not limited
to YouTube-like platforms. It can be attached to any AI product that uses content:
LLM APIs, chatbots, search engines, RAG systems, agents, enterprise assistants,
creative tools, model marketplaces, and licensed training pipelines.

The mechanism separates attribution into working layers, ordered by proof strength:

1. Ownership claim registry for creator attestations, duplicate registration
   detection, and dispute status.
2. Rights-policy gating for consent, license scope, jurisdiction, revocation, and
   minimum royalty terms.
3. Direct usage attribution for retrieved or tool-supplied source material.
4. Text/output attribution for generated text that overlaps registered works.
5. Citation attribution when the output explicitly cites a registered chunk or work.
6. Training-data value attribution for licensed training and fine-tuning corpora.
7. Residual corpus royalty settlement for diffuse licensed training value that is
   not safely attributable to a specific visible answer source.
8. Escrow for monetized outputs where no owner can be traced, where a source is
   traced but blocked by policy, or where ownership is under registry dispute.
9. Grounding-quality evaluation for detecting citations that are visible but weak,
   sources that are paid but hidden, or claims whose evidence spans disappeared.
10. Attribution-gap accountability for proving that every accessed source was cited,
   paid, or explicitly withheld with a policy or registry escrow reason.
11. Interoperability export for mapping receipts and settlements into portable
   credential and provenance graph artifacts.
12. Selective-disclosure receipts for showing public source and claim-support
    evidence while cryptographically committing to private prompts, evidence text,
    access traces, rights decisions, registry decisions, and payout fields.
13. Trace exchange for mapping provider retrieval, text-match, citation, and
    claim-support telemetry into OpenTelemetry-aligned spans that can be checked
    against the receipt and ledger.
14. Royalty statement rollups for aggregating many events into creator, escrow,
    work, and source-usage totals while preserving private prompt, answer, source
    quote, evidence-text, and matched-text confidentiality.
15. Attribution challenge and correction reports for creator appeals when a source
    was omitted, weakly attributed, or already credited.
16. Derivative lineage reports for proving that summaries, synthetic datasets, tool
    outputs, transformed corpora, and other derivative works pass royalty
    obligations back to upstream registered owners.
16. Provenance evaluation reports for replaying portable attribution-quality
    benchmarks across clean, paraphrased, hard-decoy, unattributed-escrow, and
    derivative-lineage cases.
17. Counterfactual influence reports for removing each credited work, replaying the
    same prompt and answer, and proving whether source credit and payout survive
    source-removal interventions.
18. Media attribution reports for matching image, audio, video, 3D, and
    text-shaped media signatures to registered assets with content-hash,
    perceptual-hash, descriptor-hash, payout, and escrow commitments.
19. Model signal attribution reports for verifying provider-private log-probability,
    activation, gradient, attention, and memorization telemetry through explicit
    attribution contracts, scalar scores, commitments, payout shares, and escrow
    without disclosing hidden states, logits, prompt text, output text, or
    chain-of-thought.
20. Semantic text attribution reports for matching paraphrased, summarized, or
    externally generated text to registered source owners, publishing source footer
    rows, paying accepted owners, and escrowing ambiguous text without disclosing
    prompt, output, matched, or source text.
21. Provider attribution cards for publishing certification level, coverage metrics,
    evidence channels, public disclosure surfaces, challenge policy, limitations,
    and privacy-safe hash roots at the model/provider level.
22. Training-content summaries for publishing GPAI/Croissant/SPDX/ODRL-aligned
    training corpus categories, rights coverage, license counts, policy roots,
    content-hash roots, and training-value commitments without disclosing work text.
23. Answer provenance cards for binding the visible response footer to source
    labels, claim span hashes, receipt hash, trace hash, grounding quality, and
    attribution-gap verdict without disclosing private prompt or source text.
24. Source verification reports for proving cited sources, quote hashes, source
    URIs, and claim evidence spans materialize from registered content without
    disclosing source or evidence text.
25. Response envelopes for packaging the rendered answer with embedded answer-card,
    source-verification, source-confidence, creator-license, and other public proof
    artifacts that customers can verify at the API boundary.
26. Integration profiles for publishing the provider API contract, verifier
    commands, schema map, required public surfaces, readiness checks, and bound
    proof hashes needed by RDLLM-compatible model APIs.
27. Assurance bundles for publishing hash-only proof-pack entries, Merkle roots,
    and inclusion proofs across receipts, traces, statements, challenges, provider
    cards, answer cards, source verification reports, source confidence reports,
    citation footer contracts, response envelopes, training summaries, integration
    profiles, derivative-lineage reports, provenance
    evaluation reports, counterfactual-influence reports, media-attribution
    reports, model-signal reports, rights-remediation reports,
    semantic-text-attribution reports, and certification reports.
28. Discovery manifests for publishing a well-known provider entry point with
    artifact paths, API contract hashes, schema maps, verifier commands, readiness
    checks, and bound proof hashes.
29. Attribution exchange manifests for importing upstream provider proof hashes,
    preserving public source-footer rows, and relaying escrow obligations across
    downstream AI providers without exposing private text.
30. Conformance vector packs for publishing implementation fixtures, expected
    public outcomes, verifier commands, and negative mutations that independent
    providers can reproduce before claiming RDLLM compatibility.
31. Federation handshakes for negotiating provider-to-provider runtime attribution,
    minimum certification level, required artifact hashes, source-footer relay,
    escrow relay, runtime headers, signatures, and downgrade rejection before an
    upstream proof is consumed by a downstream AI system.
32. Portable attribution capsules for binding copied or reposted AI outputs to the
    response envelope, federation handshake, source-footer commitments, proof-chain
    hashes, copy markers, delivered-body hashes, C2PA-compatible assertions, and
    SCITT-like statement subjects after content leaves the original API boundary.
33. Response release gates for blocking answer emission unless the response
    envelope, source verification report, attribution capsule, provider surface,
    and minimum certification all verify.
34. Proof-carrying responses for delivering the answer only with its release-gate
    proof and suppressing unsupported output when the gate fails.
35. Serving gateway reports for proving the production egress route delivered the
    proof-carrying response output, not an unverified raw model answer.
36. Creator license contracts for binding registered works to source-use scopes,
    attribution duties, royalty duties, revocation state, and payout commitments
    before source use.
37. Source confidence reports for converting public answer-card,
    source-verification, and creator-license evidence into verified/warning/failed
    source footer rows, claim confidence rows, and hallucination taxonomy.
38. Citation footer contracts for binding the exact client-renderable source rows,
    claim anchors, confidence labels, license status, royalty status, display order,
    and footer hash to the response proofs before a client renders the answer.
39. Private audit challenges for opening selected redacted source-access,
    claim-evidence, rights, registry, and payout paths to authorized auditors
    without publishing prompts, evidence text, salts, or payout accounts.
40. Transitive attribution reports for binding downstream reuse of copied RDLLM
    outputs to the upstream capsule, response envelope, original source rows, and
    pass-through royalty obligations so attribution cannot be laundered away by
    reposting, summarizing, or using an AI answer as downstream source material.
41. Clearinghouse reports for normalizing provider royalty statements and
    transitive attribution reports into payable, escrow, and held settlement rows
    across providers so duplicate or overlapping submissions cannot pay twice.
42. Remittance reports for converting clearinghouse payable and escrow rows into
    instruction-only payment rows, creator payout-account hash bindings,
    reconciliation references, and preserved hold rows without exposing bank
    details or asserting that payment settlement already happened.
43. Third-party audit attestations for independently replaying the public proof
    pack, binding provider surfaces through integration and discovery artifacts,
    and publishing a hash-only attestation that proves readiness without exposing
    prompt, answer, source, evidence, or payout-account text.
44. Revenue allocation reports for proving that event-level `gross_revenue` was
    derived from conserved billing, advertising, subscription, API, enterprise, or
    marketplace revenue pools before creator-pool payout calculation.
45. Finance ledger attestations for proving those revenue pools reconcile to
    hash-only external billing, invoice, ad-server, API-meter,
    enterprise-contract, marketplace-order, or other finance-system records without
    exposing customer records, payment details, prompts, outputs, or source text.
46. Proof dependency graphs for publishing a hash-only, cycle-checked replay DAG
    that tells auditors which RDLLM artifacts verify before which downstream
    artifacts, while separating hard replay dependencies from publication
    commitments.
47. Publication monitors for publishing append-only checkpoints over public proof
    surfaces so customers, creators, downstream providers, and auditors can detect
    source-proof, footer-proof, assurance-bundle, or certification drift over time.
48. Publication witnesses for binding those monitor checkpoints to independent
    witness signatures, quorum policy, and split-view detection.
49. Trust registries for binding active provider, auditor, and witness keys to
    signed proof artifacts, key rotations, revocations, and witness attestations.
50. Watchtower challenge settlement reports for requiring independent registered
    watchtower attestations over receipt-transparent settlement and for routing
    value to escrow when public challenges remain open or are accepted.
51. Source boundary reports for proving that retrieved source packets were
    evidence-only data, not instruction/control channels, and could not mutate
    attribution or payout policy before the model answered.
52. Decision provenance reports for proving which authorized proof, policy,
    accounting, and boundary-guard channels influenced claim, footer, payout, and
    release decisions.
53. Calibrated attribution confidence reports for binding those visible claims,
    source-footers, and payout-participation rows to benchmark-backed lower
    confidence bounds, with uncertainty disclosed rather than hidden.
54. Source authenticity reports for proving that visible and paid source rows have
    trusted origin evidence, active license terms, archive consensus, synthetic
    disclosure, and low source-farm/poisoning risk before direct payment.
54. Independent verifier quorum reports for requiring multiple external signed
    replay attestations before attribution consensus can release direct settlement.
55. Bonded verifier accountability reports for binding accepted verifier signatures
    to active trust-registry identities, non-revoked key hashes, slashable bond
    coverage, conflict disclosures, challenge status, and escrow/slashing evidence.
56. Receipt transparency consistency reports for comparing creator-, customer-,
    provider-, and witness-visible usage receipt logs, proving append-only prefix
    consistency, required receipt inclusion, and absence of split-view roots before
    verifier-approved settlement can leave escrow.
57. Attested attribution runtime reports for binding the live-transparent output
    path to measured enforcement code, model/policy/verifier bundle hashes,
    trusted attestor quotes, fresh nonces, and required attribution capabilities.

The current certification suite also treats certification attestations and
generated-code attribution as explicit public proof surfaces: certification
attestations bind the suite result to trust-registry-verifiable certifier keys, and
code attribution reports bind generated snippets to source owners, license checks,
payouts, and escrow without exposing code text. Claim verification reports then
require trusted signed ownership evidence before direct settlement and route weak,
unverified, or duplicate claims to escrow.

The highest public deployment object is now the
`rdllm-universal-rdllm-passport/v1` passport. It does not replace user-facing
source attribution; it proves that the answer footer, evidence previews, locator
rows, citation URL-health rows, payout rows, universal content credential,
invocation guard, invocation coverage, invocation witness, foundation-model
adapter/conformance/runtime artifacts, certification, attestation, provider card,
training summary, assurance bundle, proof dependency graph, integration profile,
discovery manifest, public verifier commands, and research-control rows all
hash-bind and verify together across supported foundation-model provider
families. A deployment that cannot publish this passport cannot claim complete
cross-provider RDLLM compatibility, even if an individual answer has a local
source footer.

The prototype in this repository implements these layers as runnable code. The
response itself is now part of the attribution mechanism: every rendered answer ends
with a `Sources` footer that lists source labels, owner metadata, work IDs, source
URIs, evidence quotes, content hashes, evidence span hashes, support scores, and
grounding coverage. Each event also carries a `rdllm-grounding-quality/v1` report
that scores source availability, citation integrity, evidence relevance, fact
support, policy alignment, and payout alignment, plus a
`rdllm-attribution-gap/v1` report that closes the loop between source access,
user-visible attribution, payout, and escrow.
Every receipt also carries a `rdllm-selective-disclosure/v1` root so public users
can verify footer-grounding facts without seeing private economics or confidential
source-access details.
Every receipt now also carries `rdllm-trace-exchange/v1` commitments so provider
telemetry can be exported and verified without depending on a vendor-specific log
format.
Periodic `rdllm-royalty-statement/v1` reports aggregate receipts and traces into
creator-facing statements with public commitments over the underlying private
ledger.
Creator `rdllm-attribution-challenge/v1` reports provide a non-rewrite correction
path when attribution is contested after an event or statement is published.
Derivative `rdllm-lineage-report/v1` reports prove that royalties attached to a
summary, synthetic dataset, tool output, or transformed corpus can be recursively
split between the immediate derivative owner and upstream registered owners without
rewriting the original usage event.
Provider `rdllm-provenance-evaluation/v1` reports replay clean-source, paraphrase,
hard-decoy, unattributed-escrow, and derivative-lineage benchmark cases so source
finding is tested as a public quality claim, not merely inferred from receipts.
Provider `rdllm-counterfactual-influence/v1` reports remove each credited source,
replay the same prompt and answer against the reduced corpus, and publish hashes,
scores, source-removal status, payout reallocation status, and influence margins so
users and auditors can distinguish sources that mattered from sources that merely
looked relevant.
Provider `rdllm-media-attribution/v1` reports match image, audio, video, 3D, and
text-shaped media signatures against registered assets, publish only hashes and
scores, pay matched owners, and escrow weak or unknown media influence.
Provider `rdllm-model-signal-attribution/v1` reports verify provider-private
influence telemetry through an explicit attribution contract, scalar model-signal
scores, private telemetry commitments, payout shares, and escrow without exposing
raw hidden states, token logits, private prompts, private outputs, or
chain-of-thought.
Provider `rdllm-rights-remediation/v1` reports compare previous and updated rights
states, preserve historical event hashes, and prove future denied use after
revocation or consent changes without exposing work text or private ledger
payloads.
Provider `rdllm-semantic-text-attribution/v1` reports attribute paraphrased or
externally generated text to registered sources, publish source footer rows, pay
accepted owners, and escrow ambiguous or unmatched text without exposing prompt,
output, matched, or source text.
Response `rdllm-answer-provenance-card/v1` reports let a user or downstream system
verify that visible source labels and claim span hashes match the signed receipt and
trace without seeing private prompt, answer, source quote, claim, or evidence text.
Provider `rdllm-source-confidence-report/v1` reports combine that answer card with
source materialization evidence and creator license terms, then expose public
footer rows labeled `verified`, `warning`, or `failed`. The report also publishes a
hallucination taxonomy for fabricated sources, metadata drift, hash mismatches,
footer omissions, attribution suppression, license gaps, unsupported claims, and
evidence-span gaps, so a user can see whether the footer is actually grounded
rather than merely decorative.
Provider `rdllm-citation-footer-contract/v1` reports then turn those confidence rows
into a client-rendering contract. The contract specifies the exact source lines,
claim anchors, display order, confidence labels, license status, royalty status,
row hashes, and footer hash a response client must preserve, and verification fails
if a client tampers with the visible footer, omits a source, weakens a claim anchor,
or renders a footer that no longer matches the response envelope.
Provider `rdllm-rendered-attribution-audit/v1` reports verify the exact Markdown
the user sees. The audit parses inline `[S#]` markers, the rendered `Sources`
footer, and `Claim Evidence` rows, then checks them against the response envelope,
citation footer contract, source availability, evidence sufficiency,
counterevidence, and answer-coverage reports without storing raw answer or source
text.
Provider `rdllm-source-boundary-report/v1` reports prove that source packets in the
generation context were treated as evidence-only data. Each context block is bound
to the source-access trace, source verification report, and generation context
closure report; verification fails if a source block is relabeled as control or
instruction content, if it can modify attribution or payout decisions, or if the
source packet/content hash drifts. This converts prompt-injection guidance into a
public proof artifact rather than relying on prompt text alone.
Provider `rdllm-source-authenticity-report/v1` reports then prove that cited
sources are not merely reachable and boundary-isolated, but also origin-bound and
poisoning-resistant. Each visible source row is replayed against availability,
boundary, license, confidence, and trusted origin-signal artifacts. Verification
fails if the origin signature or issuer trust is missing, if source-farm or
poisoning risk exceeds policy thresholds, if synthetic provenance is hidden, if
archive consensus is absent, or if unauthenticated rows are treated as direct
payout-eligible.
Provider `rdllm-decision-provenance-report/v1` reports prove why a response was
allowed to say what it said, cite what it cited, and pay who it paid. The report is
generated after the release gate and publishes a hash-only influence graph over
claim grounding, footer display, payout participation, and release decisions.
Verification fails if a decision is missing required proof edges, if a payout row
is influenced directly by retrieved source text, if private prompt/source text is
present, or if the graph is not bound to the response envelope, release gate, trace
exchange, attribution capsule, and source-boundary report.
Provider `rdllm-calibrated-attribution-confidence/v1` reports prove how much
confidence a user, creator, downstream provider, or auditor should assign to the
visible attribution. The report binds claim rows, footer rows, and payout
participation rows to observed benchmark rates and Wilson lower confidence
bounds, using source confidence, evidence sufficiency, provenance evaluation,
decision provenance, release-gate, trace, and capsule artifacts. Verification
fails if benchmark inputs drift, decision provenance is missing, low-confidence
rows are not disclosed or escrowed, or private prompt/source text leaks.
Provider `rdllm-assurance-bundle/v1` reports publish the proof pack as hashes and
inclusion proofs so public verifiers can confirm artifact integrity without seeing
private prompt, answer, source, evidence, or work text.
Provider `rdllm-integration-profile/v1` reports publish the stable API contract,
schemas, verifier commands, surfaces, readiness checks, and bound hashes that make
RDLLM adoption testable by platforms, model buyers, and auditors.
Provider `rdllm-discovery-manifest/v1` reports publish the well-known artifact map
that lets customers automatically discover, verify, and monitor the public RDLLM
proof surfaces.
Provider `rdllm-federation-handshake/v1` reports turn those public surfaces into a
runtime contract: a downstream model asks for a minimum RDLLM level, the upstream
provider signs the accepted level, bound artifact hashes, required headers,
source-footer relay, escrow relay, and downgrade-failure rules, and the verifier
rejects missing vectors, missing exchange manifests, stale hashes, or private-text
leakage.
Provider `rdllm-remittance-report/v1` reports take the clearinghouse output and
produce payment-file-ready rows. Each payment instruction binds the clearinghouse
settlement row hash, origin hashes, chunk IDs, creator license contract hash,
payout-account hash, ISO 20022-compatible end-to-end ID, and remittance reference.
The report is explicitly instruction-only: it proves who should be paid and how the
payment can be reconciled, while leaving actual fund movement to regulated payment
processors.
Provider `rdllm-payment-execution-report/v1` reports then prove whether those
instructions were actually matched by hash-only processor or escrow settlement
records. The report checks amount, currency, end-to-end ID, account hash,
settlement status, processor-record hash, settlement-batch hash, duplicate rows,
unmatched rows, and private-field absence before value can be described as paid or
escrowed.
Provider `rdllm-payment-rail-attestation/v1` reports bind that execution report to
registered payment or escrow processor signatures over each settlement batch. The
attestation checks trust-registry membership, processor role authorization,
attestation hashes, processor signatures, batch coverage, amounts, currencies,
settlement statuses, and private-field absence, so a provider cannot fabricate a
consistent payment-execution report without matching rail-authentic evidence.
Provider `rdllm-third-party-audit-attestation/v1` reports let an independent
auditor replay the public RDLLM proof pack and publish only hashes, statuses, and
readiness checks. The attestation binds the provider card, certification report,
integration profile, discovery manifest, assurance bundle, response envelope,
source confidence report, citation footer contract, clearinghouse report, and
remittance report, plus an optional payment execution report when processor records
are available, then rejects drift in any of those artifacts without embedding private
prompts, answer text, source text, evidence text, or payout-account data.
Provider `rdllm-revenue-allocation-report/v1` reports close the revenue-input
trust gap. They bind hashed billing, advertising, subscription, API, enterprise, or
marketplace revenue sources to event allocation rows, prove that source revenue
conserves into ledger `gross_revenue`, prove that creator-pool totals follow from
allocated revenue and creator-pool rates, and reject private customer account or
invoice text leakage.

## Actors

- Creator: a person or entity that owns or controls a work.
- Work: a registered content item with metadata, license, and payout account.
- Claim registry: a tamper-evident registry report that binds works, creators,
  ownership attestations, duplicate-content conflicts, and report hashes.
- Rights policy: machine-readable permission, prohibition, duty, jurisdiction, and
  revocation metadata associated with a work.
- AI operator: the AI service, model provider, app, API, marketplace, or enterprise
  system that earns revenue from AI usage.
- Auditor: a creator, regulator, platform reviewer, or third party that can replay
  attribution from the ledger.
- Collective manager: an optional rights organization or data trust for pooled
  licensing at scale.

## Revenue Flow

For each generation event `r`:

- `G_r` is gross monetizable revenue attributable to the event. It can come from
  ads, subscription allocation, API usage, enterprise license usage, or marketplace
  fees.
- `s` is the creator pool rate. The prototype defaults to `0.55`, mirroring the
  long-form YouTube Partner Program split as an inspiration, not a legal rule.
- `P_r = G_r * s` is the royalty pool for the event.

The AI operator can keep `G_r - P_r` for infrastructure, model costs, moderation,
product margin, and reserves.

## Attribution Formula

For every eligible source chunk `i` used in event `r`, first evaluate policy:

```text
allowed_i = use in allowed_uses
            and use not in prohibited_uses
            and jurisdiction is allowed
            and not revoked
            and creator_pool_rate >= minimum_creator_pool_rate
```

Before settlement, the registry checks whether a matched source is under an open
ownership conflict. If two different creators register duplicate or near-duplicate
content, the event is marked `registry_disputed` and the pool is moved to
registry-dispute escrow until the claim is resolved.

If a matched source is denied for the attempted use, the event is marked
`rights_blocked` and the pool is moved to rights-conflict escrow. For every
policy-eligible source chunk `i`, compute:

```text
raw_i = (
  0.15 * retrieval_i
  + 0.15 * output_support_i
  + 0.05 * prompt_overlap_i
  + 0.55 * text_match_i
  + 0.10 * citation_i
) * training_value_i
weight_i = raw_i / sum(raw_j for all eligible j)
payout_i = P_r * weight_i
```

Prototype scoring channels:

- retrieval relevance to the prompt
- output support between source and final output
- direct prompt overlap
- content-ID-style text match score
- explicit citation score
- training-value prior from Shapley-style data valuation
- rights decision for the attempted use

Production systems can replace lexical support with model-native signals such as
attention over cited context, constrained decoding citations, source-aware beam
scores, retrieval logs, or post-generation entailment checks.

The current implementation uses this transparent formula:

```text
raw_i = (
  0.15 * retrieval_i
  + 0.15 * output_support_i
  + 0.05 * prompt_overlap_i
  + 0.55 * text_match_i
  + 0.10 * citation_i
) * training_value_i
```

## Ledger Event

Each event records:

- prompt
- raw answer text
- rendered answer with source footer
- gross revenue
- creator pool rate
- creator pool amount
- retrieved chunk IDs
- text matches against registered works
- source hashes
- source references shown to the user
- claim-level support checks
- claim-to-evidence span hashes
- grounding quality verdict and component scores
- rights policy decisions
- registry conflict decisions
- attribution basis scores
- attribution weights
- payout amounts
- event hash

The event hash is built from the prompt, output, source hashes, payouts, and pool.
Auditors can verify that:

1. Payouts sum exactly to the creator pool.
2. Attribution weights sum to one for paid events.
3. Source hashes match registered chunks.
4. Source references shown to the user match registered chunk hashes.
5. Supported claims point to evidence text inside registered chunks.
6. Evidence span hashes appear in the rendered footer and receipt.
7. Rights decisions in the event match the source licenses and attempted use.
8. Registry decisions in the event match the ownership-conflict report.
9. The event hash is reproducible.
10. The grounding quality verdict is reproducible from the event.

## Ownership Claim Registry

The claim registry adds a settlement safety layer that hashes ownership claims
separately from generated answers. Each registry report has:

- `registry_report_version`
- registered works and content hashes
- optional ownership attestations with issuer, evidence URI, evidence hash, claim
  type, and signature placeholder
- duplicate and near-duplicate conflicts across different creator IDs
- open-conflict counts
- report hash

The reference implementation detects exact duplicate text and near-duplicate text
above a configurable similarity threshold. If registry enforcement is enabled and a
generation event touches a conflicted work, no claimant is paid directly. The
rendered answer withholds source quotes, the receipt records a `registry` section
with the conflict ID and registry report hash, and the creator pool goes to
`registry_dispute_escrow`.

This is intentionally separate from copyright proof. Hashes and attestations do not
settle legal ownership by themselves. They make the runtime settlement behavior
auditable: a provider can prove that a disputed claim did not receive automatic
royalty settlement while the dispute was open.

## Escrow Resolution

Registry-dispute escrow is not the final state. After a dispute window, review board,
court order, collective-management decision, or verified credential update resolves
ownership, a settlement report can release escrow without rewriting the original
usage event.

The settlement report has:

- `settlement_version`
- `resolution_id`, conflict ID, resolver, evidence URI, evidence hash, and resolved
  timestamp
- the registry report hash that was active when the event was blocked
- payout splits for the resolved owner or owners
- source ledger hash
- release entries linked to original event IDs and event hashes
- balances before release, released balances, and balances after release
- report hash and optional signature

This creates a full lifecycle: attribute, detect conflict, escrow, resolve, release,
and verify. Historical receipts continue to show that the original event was
registry-disputed; the settlement report proves where the held value went after
resolution.

## Attribution Receipts

Every event can produce an attribution receipt:

- `receipt_hash`: canonical hash of the receipt payload
- `issuer`: model provider, AI app, or settlement authority
- `model`: model ID, version, and route ID
- `event`: event hash plus prompt, answer, and rendered-output commitments
- `grounding`: source references, source-access trace, claim checks, evidence span
  hashes, grounding report, grounding quality verdict, and attribution-gap verdict
- `rights`: allow/deny policy decisions, denial count, and policy status
- `registry`: registry status, conflict count, registry report hash, and deterministic
  dispute decisions
- `telemetry`: OpenTelemetry-aligned trace-exchange version plus hashes for
  source-access spans, visible source/citation spans, and claim-support spans
- `economics`: creator pool and payout shares
- `privacy`: selective-disclosure policy
- `signature`: optional provider signature

The receipt is the portable artifact a foundation-model API could return in a
header, webhook, or audit endpoint. It lets downstream tools verify that the answer
and the payout trail came from the same source-grounding evidence.

## Interoperability Bundle

Receipts and settlement reports can also be exported as an
`rdllm-interop/v1` bundle. The bundle contains:

- a VC-shaped attribution credential whose subject commits to the receipt hash,
  event hash, prompt/output hashes, source count, source-access count, claim count,
  rights commitment, registry commitment, attribution-gap commitment, and
  payout-share commitment
- a PROV-shaped answer graph with entities for prompt commitments, rendered-output
  commitments, source chunks, and supported claims
- relations for `prov:used`, `prov:wasGeneratedBy`, `prov:wasAttributedTo`,
  `rdllm:supportedClaim`, `rdllm:paidShare`, `rdllm:rightsDecision`, and
  `rdllm:registryDecision`, and `rdllm:attributionGapDecision`
- an OpenTelemetry-aligned `rdllm-trace-exchange/v1` artifact with generation,
  source-access, citation, and claim-support spans
- an optional VC-shaped escrow-settlement credential bound to the settlement report
  hash, source ledger hash, conflict ID, release balances, and payout splits
- a bundle hash and deterministic proof envelope

This layer is not meant to replace W3C Verifiable Credentials or W3C PROV. It gives
RDLLM artifacts a standards-aligned shape so wallets, registries, provider APIs,
enterprise GRC tools, and transparency services can ingest the same attribution
facts without understanding the internal Python ledger.

## Transparency Log

Receipts can be appended to a Merkle transparency log. The log returns an inclusion
proof binding the receipt hash to a tree root. This gives creators, enterprise
customers, and regulators a tamper-evident audit path without forcing every private
prompt or full economic record into the open.

## Selective Disclosure

Public trust does not require exposing every private field. RDLLM therefore emits a
selective-disclosure package alongside the private receipt. The private receipt
contains per-path salts and a `payload.privacy.disclosure_root`. The public package
reveals only source identity, source URI, content hash, contribution weight,
claim-support metadata, grounding quality, attribution-gap summary, model route,
event commitments, and policy/registry status. It redacts source quotes, claim
evidence text, source-access traces, payout shares, gross revenue, rights-decision
internals, and registry-decision internals.

Verification recomputes disclosed leaf hashes from `(path, salt, value)`, checks
the Merkle root over disclosed and redacted leaf hashes, and checks that the public
receipt is exactly reconstructible from disclosed values. A private auditor can add
the full receipt and provider signing secret to prove that the redacted commitments
match the hidden receipt payload. This follows the same design direction as
SD-JWT-style claim disclosures: show only what the verifier needs, but make hidden
claim tampering detectable.

## Trace Exchange

The trace exchange solves a different problem from the public source footer. A
footer says what the user saw; a provider trace says what the system actually
retrieved, text-matched, cited, and used to support claims. RDLLM maps that trace
into OpenTelemetry-style spans so the artifact can ride existing observability
stacks while carrying royalty-specific fields.

An `rdllm-trace-exchange/v1` artifact contains:

- one generation span with `gen_ai.provider.name`, model attributes, event hash,
  prompt hash, answer hash, rendered-output hash, and optional receipt hash
- one source-access span for every retrieval or text-match access, including
  `gen_ai.data_source.id`, structured `gen_ai.retrieval.documents`, chunk ID, work
  ID, creator ID, source URI, content hash, score, rank, policy status, registry
  status, and matched-text hash
- one citation span for every footer-visible source, including label, owner, chunk,
  URI, content hash, contribution weight, and evidence span hashes
- one claim-support span for every claim, including claim hash, support score,
  source label, chunk ID, evidence span hash, and evidence character offsets
- summary hashes for source accesses, visible sources, and claim support

Verification rejects traces where a provider omits accessed sources, relabels a
citation to a different content hash, changes claim evidence, or publishes summary
hashes that no longer match the signed receipt. This is the provider-facing bridge
between source attribution and production observability: ordinary telemetry can show
latency and cost, while RDLLM trace exchange proves source accountability.

## Royalty Statement Rollups

Single-event receipts prove one answer. Platform-scale creator economics also need
periodic statements that creators and auditors can reconcile against many usage
events. RDLLM emits `rdllm-royalty-statement/v1` reports for that layer.

A statement contains:

- period metadata and issuer metadata
- event count, receipt count, trace count, creator count, source-access count,
  visible-source count, supported-claim count, gross revenue total, creator-pool
  total, payout total, direct creator total, and escrow total
- per-creator, per-escrow, per-work, and per-source usage rows
- event rollups with event hashes, receipt hashes, trace hashes, creator pools,
  source counts, claim counts, grounding status, and attribution-gap verdict
- root commitments over events, shares, creator statements, escrow statements,
  work statements, source usage, source access, source references, claim support,
  receipt rollups, and trace rollups
- a statement hash and optional signature

The public statement deliberately omits prompts, rendered outputs, answer text,
source quotes, evidence text, and matched text. A private auditor can recompute it
from the ledger plus optional receipt and trace artifacts. Verification fails if a
provider changes a creator payout, removes an event, drops a trace, changes a
source-usage count, or publishes totals that no longer equal the creator pool.

## Attribution Challenge Reports

Even a strong provider receipt is still a provider assertion. Creators need a way
to contest an omission after an answer, receipt, or royalty statement is published.
RDLLM emits `rdllm-attribution-challenge/v1` reports for that correction path.

A challenge report contains:

- the original event ID, event hash, and optional royalty statement hash
- claimant, creator, work, chunk, source URI, and challenged content hash
- the challenge reason and acceptance threshold
- text-match evidence as scores, longest matched token sequence length, and matched
  text hash, without disclosing the matched text itself
- flags for whether the challenged source was already visible, already paid,
  already accessed, already credited, and licensed for generation
- a verdict: `accepted`, `accepted_escrow`, `already_credited`, or `rejected`
- a remedy: pay claimant, escrow unlicensed value, or no action
- commitments over the original event's source access, source references, payout
  shares, and claim support
- a report hash and optional signature

The remedy explicitly does not rewrite the historical event. If the original event
omitted a source, the challenge report creates a corrective adjustment. If the
source was already credited, the report proves no double payment is due. If the
evidence is weak, the challenge is rejected. If the source appears influential but
is not licensed for generation, the correction routes to rights-conflict escrow.

## Derivative Lineage Reports

Modern AI pipelines often consume derivative artifacts: summaries, curated
datasets, synthetic examples, tool outputs, and transformed corpora. If settlement
stops at the immediate derivative work, upstream creators disappear from the money
flow. RDLLM emits `rdllm-lineage-report/v1` reports so derivative works can carry
machine-readable upstream obligations.

A lineage report contains:

- the bound event ID, event hash, creator pool, and settleable source-share count
- a pass-through policy for how much of a derivative source payout flows upstream
- source royalty shares with work IDs, chunk IDs, content hashes, payout amounts,
  and whether upstream lineage exists
- a lineage graph of work nodes and derivative edges, including declared and actual
  upstream content hashes
- settlement obligations that split each source payout between immediate residual
  owners and upstream owners while conserving the original source payout
- commitments over source shares, lineage edges, obligations, and work-lineage
  metadata
- privacy flags, report hash, and optional signature

The verifier recomputes the report from the event and registered works. It rejects
missing upstream works, lineage cycles, declared upstream hash drift, payout
non-conservation, private-text disclosure, report tampering, and signature drift.

## Provenance Evaluation Reports

A provider can publish perfect-looking receipts while still using a weak source
finder. RDLLM therefore defines `rdllm-provenance-evaluation/v1`: a signed replay
report over a portable source-attribution benchmark. The benchmark covers clean
source reuse, paraphrased reuse, hard decoys with overlapping vocabulary,
unattributed escrow, and derivative-lineage cases.

A provenance evaluation report contains:

- hashed benchmark prompts and outputs, expected work IDs, forbidden decoy work IDs,
  expected upstream work IDs, and escrow expectations
- per-case event hashes, creator-pool totals, source counts, claim counts, and
  escrow totals
- ranked source decisions with work IDs, chunk IDs, content hashes, retrieval,
  text-match, claim-support, output-support, contribution, and payout signals
- checks for expected recall, top-1 source accuracy, decoy resistance, escrow
  accuracy, grounding verification, and attribution-gap accounting
- aggregate metrics, evidence roots, privacy flags, report hash, and optional
  signature

The verifier replays the benchmark against the registered corpus and rejects report
tampering, omitted cases, signature drift, source-ranking drift, and disclosure of
raw benchmark prompts, answers, source text, or claim evidence.

## Counterfactual Influence Reports

Receipts and benchmark reports prove that a source was found, cited, and paid. They
do not by themselves prove whether the source had marginal influence or merely
appeared in a plausible retrieval set. RDLLM therefore defines
`rdllm-counterfactual-influence/v1`: a signed intervention report that removes each
credited work from the attribution engine, replays the same prompt and answer, and
records what happens to source credit and payout.

A counterfactual influence report contains:

- the bound event ID, event hash, creator pool, and number of credited works tested
- a policy profile for the `remove_credited_work` intervention and minimum impact
  margin
- baseline ranked source rows with work IDs, chunk IDs, content hashes, decision
  scores, and signal summaries
- one intervention per credited source, including ablation event hash, source-
  absence status, payout reallocation or escrow status, best substitute source, and
  intervention hash
- impact margins that classify a source as decisive, replaceable or redundant, or
  weak/uncredited
- commitments over baseline sources, interventions, ablation event hashes, privacy
  flags, report hash, and optional signature

The verifier recomputes every ablation from the original event and registered
corpus. It rejects report tampering, source-removal drift, failed payout
reallocation, signature drift, and disclosure of raw prompt, answer, source text,
quote text, or claim evidence. This makes source footers more than decoration:
users can see that cited works were not only relevant, but tested for influence.

## Media Attribution Reports

Text attribution alone is not enough for model providers that generate images,
audio, video, design assets, game objects, or multimodal answers. RDLLM therefore
defines `rdllm-media-attribution/v1`: a signed report over registered media assets
and submitted media signatures.

A media attribution report contains:

- registered asset IDs, creator IDs, media types, source URIs, content hashes, and
  ranked match scores
- submitted input IDs, media types, input hashes, perceptual-hash commitments, and
  descriptor-hash commitments
- exact-hash, perceptual-similarity, and descriptor-similarity signal scores
- a decision per input: matched owner payout or unattributed-media escrow
- royalty shares with the matched creator, asset, input IDs, payout, and
  contribution weight
- commitments over the media corpus, submitted media, match rows, share rows,
  report hash, and optional signature

The verifier replays the match from the private media signatures and rejects hash
drift, payout drift, weak-score promotion, signature drift, and disclosure of raw
media, private descriptors, or perceptual hashes. This gives multimodal systems a
Content-ID-like owner trail without assuming every media object is public or that a
single platform hosts the content.

## Model Signal Attribution Reports

Footer citations and source verification prove that an answer is grounded in
registered material, but recent attribution research also shows that a model can
post-rationalize citations or rely on internal memory. RDLLM therefore defines
`rdllm-model-signal-attribution/v1`: a signed report over provider-private
model-internal telemetry.

A model signal attribution report contains:

- an explicit `rdllm-attribution-contract/v1` stating the output being explained,
  eligible credited features, feature granularity, assumed generation process,
  attributed score, held-fixed values, and excluded private internals
- event hashes for the prompt, output, model ID, and model version
- per-work scalar evidence channels for log-probability delta, activation
  similarity, gradient influence, attention mass, and memorization score
- source IDs, creator IDs, work IDs, source URIs, content hashes, decision scores,
  ranked accepted/escrow decisions, and private telemetry commitments
- royalty shares for accepted owners and `model_signal_escrow` for weak, denied, or
  zero-confidence signal mass
- commitments over private signal inputs, public signal rows, payout shares, report
  hash, and optional signature

The verifier replays the scalar report from the private telemetry input and rejects
hash drift, payout drift, threshold drift, signature drift, unsupported attribution
contracts, weak-score promotion, and disclosure of private prompts, outputs, hidden
states, logits, traces, or chain-of-thought. This gives providers a way to expose
internal attribution evidence without publishing raw activations.

## Rights Remediation Reports

Creator consent is not static. A source may be allowed for training or generation
at one point, then later opt out, revoke a license, narrow allowed uses, add
jurisdiction limits, or raise minimum royalty terms. RDLLM therefore defines
`rdllm-rights-remediation/v1`: a signed report over previous and updated rights
states.

A rights remediation report contains:

- previous and updated policy roots for the registered corpus
- changed work rows with content hashes, policy hashes, revocation flags, and
  machine-readable change reasons
- historical event references that preserve event IDs, event hashes, creator-pool
  amounts, and changed-work payout totals without rewriting past events
- future-use probes across training, retrieval, generation, external attribution,
  display, and quote
- blocked-output probes proving newly denied text use routes the creator pool to
  `rights_conflict_escrow`
- commitments over changed works, historical event references, enforcement probes,
  report hash, and optional signature

The verifier recomputes the report from the previous corpus, updated corpus, and
private ledger. It rejects policy-root drift, changed-work drift, historical-event
rewrites, future-use enforcement drift, escrow drift, signature drift, and leakage
of work text, prompts, outputs, claim text, matched text, or private ledger
payloads.

## Semantic Text Attribution Reports

Direct text matching catches verbatim and near-verbatim outputs, but source owners
also need attribution when an AI answer paraphrases, summarizes, translates, or
rephrases a registered work. RDLLM therefore defines
`rdllm-semantic-text-attribution/v1`: a signed report over submitted text outputs
and registered source candidates.

A semantic text attribution report contains:

- submitted output rows with prompt hashes, output hashes, semantic fingerprint
  commitments, policy use, and gross revenue
- ranked source rows with work IDs, creator IDs, chunk IDs, source URIs, content
  hashes, lexical scores, concept-overlap scores, source-distinctiveness scores,
  sequence scores, n-gram scores, decoy margins, policy decisions, and feature
  commitments
- public source footer rows for accepted sources, or explicit escrow footer rows
  for ambiguous, unmatched, or policy-blocked text
- royalty shares for accepted owners, `semantic_text_escrow`, or
  `rights_conflict_escrow`
- commitments over submitted outputs, match rows, footer rows, payout shares,
  policy roots, report hash, and optional signature

The verifier replays the ranking from the private inputs and registered corpus. It
rejects ranking drift, hard-decoy promotion, payout drift, footer tampering,
signature drift, and disclosure of prompt text, output text, matched text, or source
text. This gives external AI outputs the same user-facing source-footing discipline
as answers generated inside the provider route.

## Pinpoint Provenance Reports

Model-signal and semantic-text reports are necessary but not enough: a cited source
can be topically related while failing to support the answer's actual claim. RDLLM
therefore defines `rdllm-pinpoint-provenance-report/v1`, a signed report over
private prompt, answer, claim, and candidate-document text that publishes only
hashes, source IDs, support scores, footer rows, and payout or escrow decisions.

A pinpoint provenance report contains:

- claim hashes and required evidence-phrase hashes for support-bearing answer
  claims
- ranked candidate rows with work IDs, creator IDs, source URIs, content hashes,
  decision scores, support margins, document roles, and feature commitments
- explicit `rejected_anti_document` decisions for topical or forbidden
  anti-documents
- public source-footer rows only for accepted supporting works
- royalty shares for accepted owners and `pinpoint_provenance_escrow` for claims
  that do not pass answer-critical fact support

The verifier replays the report from private inputs and rejects hash drift,
ranking drift, anti-document promotion, footer tampering, payout drift, signature
drift, and disclosure of prompt, response, claim, source, or critical-evidence
phrase text.

## Citation Identity Reports

Pinpoint provenance proves that a candidate source supports a claim, but a public
footer can still hallucinate the citation identity: a fake DOI, an arXiv ID attached
to the wrong title, or a real link with swapped authors. RDLLM therefore defines
`rdllm-citation-identity-report/v1`, a signed report that resolves declared
citations against authority records before a source can enter the canonical footer
or receive citation-linked payout.

A citation identity report contains:

- claim hashes and citation IDs for each source-bearing answer claim
- ranked citation rows with declared identifier hashes, resolved authority
  commitments, title similarity, author overlap, year match, identifier match,
  claim-support scores, and `accepted` or `citation_identity_escrow` decisions
- canonical footer rows only for citations whose identity and claim support pass
  the policy thresholds
- explicit rejection of fabricated, unresolved, metadata-swapped, and
  claim-unsupported citations
- royalty shares for accepted source owners and `citation_identity_escrow` for
  blocked citation rows

The verifier replays authority resolution from private inputs and rejects metadata
swap drift, fabricated-citation promotion, footer tampering, payout drift, signature
drift, and disclosure of private prompt, response, claim, source-excerpt, or
authority-content text.

## Attribution Consensus Reports

Individual proof artifacts can be valid while disagreeing about settlement
readiness. RDLLM therefore defines `rdllm-attribution-consensus-report/v1`, a
signed public report that binds source confidence, source authenticity, evidence
sufficiency, counterevidence, pinpoint provenance, and citation identity to the
same event hash before direct payout.

An attribution consensus report contains:

- event-hash bindings and declared hashes for all six required public artifacts
- per-source consensus rows with channel votes, channel scores, missing channels,
  blockers, consensus scores, and `accepted` or `attribution_consensus_escrow`
  decisions
- royalty shares for accepted owners and escrow rows for sources with missing or
  conflicting evidence
- commitments over artifact bindings, consensus rows, payout shares, policy, and
  report hash

The verifier replays the consensus from public artifacts and rejects event-hash
divergence, accepted rows that miss any required channel, blocked rows that receive
direct payout, payout drift, signature drift, and disclosure of private prompt,
response, source, claim, authority, or tool text.

## Independent Verifier Quorum Reports

L70 proves that the provider's public attribution artifacts agree with each
other. L71 adds a stronger settlement gate: `rdllm-verifier-quorum-report/v1`
requires multiple independent verifier signatures over the same public artifact
root before any consensus-accepted row can become directly payable.

A verifier quorum report contains:

- declared hashes for the attribution consensus report, provider card,
  certification report, and integration profile
- per-verifier signed replay rows with verifier id, organization id, artifact
  root, required checks, verdict, signature, and attestation hash
- a settlement gate that either preserves consensus payout rows or routes them to
  `verifier_quorum_escrow`
- commitments over artifact bindings, verifier attestations, disagreement rows,
  accepted organizations, and settlement rows

The verifier rejects signature drift, mismatched artifact roots, insufficient
quorum, insufficient independent organizations for direct settlement, private
field leakage, and creator-pool drift. Honest disagreement is not hidden: it
produces a valid escrow report rather than a direct-settlement report.

## Bonded Verifier Accountability Reports

L71 proves external replay agreement, but it does not by itself make verifier
misconduct economically costly. L72 adds `rdllm-verifier-accountability-report/v1`:
accepted verifier attestations must bind to active trust-registry identities,
non-revoked verifier key hashes, active slashable bond rows, conflict-disclosure
hashes, and challenge/slashing evidence before verifier-approved settlement can
leave escrow.

A verifier accountability report contains:

- declared hashes for the verifier quorum report, trust registry, provider card,
  and certification report
- accepted verifier rows copied as hash-only public evidence from the L71 report
- registry rows proving the accepted verifier key hashes are active and not revoked
- bond rows with bond id, amount, currency, escrow-account hash, validity window,
  conflict-disclosure hash, duties, active flag, and slashable flag
- challenge rows and slashing evidence rows for accepted or open accountability
  disputes
- a settlement gate that either preserves verifier-quorum payout rows or routes
  value to `bonded_verifier_accountability_escrow`

The verifier rejects unregistered verifiers, key-hash mismatch, revoked keys,
missing or insufficient bonds, unslashable bonds, blocking conflicts, open
accountability challenges, artifact drift, private-field leakage, and creator-pool
drift. A disputed verifier does not silently block attribution forever: the report
preserves the escrow amount and publishes the challenge/slashing evidence root
needed for a later adjudication.

## Receipt Transparency Consistency Reports

L72 proves that independent verifiers are accountable, but the economic usage log
itself can still be attacked by omission, forked publication, or split-view roots.
L73 adds `rdllm-receipt-transparency-consistency-report/v1`: providers publish
receipt-log snapshots from the perspectives of creators, customers, witnesses, and
the provider, and direct settlement requires all snapshots to be append-only and
consistent.

A receipt transparency consistency report contains:

- declared hashes for the verifier accountability report, provider card, and
  certification report
- hash-only transparency-log bindings for each observed receipt-log snapshot
- snapshot rows that recompute tree size, Merkle root, entry sequencing, and
  entry-hash completeness
- append-only consistency rows that prove smaller snapshots are prefixes of larger
  snapshots
- split-view conflict rows for same-size roots or receipt hashes that appear at
  multiple indexes
- required-receipt rows with inclusion proofs, payload-hash checks, and receipt
  envelope-hash checks
- a settlement gate that either preserves verifier-approved payout rows or routes
  value to `receipt_transparency_consistency_escrow`

The verifier rejects tree-size drift, root drift, non-sequential entries,
append-only violations, split-view conflicts, missing required receipts, invalid
inclusion proofs, receipt payload/envelope mismatch, artifact drift, private-field
leakage, and creator-pool drift. This closes the practical gap between
"the model says it paid this usage" and "creators, customers, and auditors can see
the same append-only economic history."

## Watchtower Challenge Settlement Reports

L74 adds `rdllm-watchtower-challenge-settlement-report/v1`: direct settlement
requires a quorum of registered independent watchtowers to sign the
receipt-transparency subject, and any open or accepted public challenge blocks
release. This turns L73 from a passive consistency proof into an enforceable
optimistic challenge mechanism.

A watchtower challenge settlement report contains:

- declared hashes for the receipt-transparency-consistency report, verifier
  accountability report, trust registry, provider card, and certification report
- a watchtower subject hash over L73 status, required receipt counts, split-view
  counts, settlement decision, and verifier-accountability state
- registry rows proving active watchtower key hashes and revocation status
- HMAC reference attestations from each watchtower in the quorum
- challenge rows with status, evidence hash, blocking flag, slash targets, and
  challenged amount
- slashing-evidence rows and bounty rows for accepted verifier-observation
  failures
- settlement rows that either preserve direct payout or route all value to
  `watchtower_challenge_escrow`

The verifier rejects missing quorum, unregistered or revoked watchtower keys,
invalid watchtower signatures, provider surface drift, private-field leakage,
open or accepted blocking challenges, unreproducible slashing rows, and
creator-pool drift. Accepted challenges can produce hash-only slashing and bounty
rows without exposing prompts, answers, source text, receipts, customers, or
payment details.

## Output Provenance Binding Reports

L75 adds `rdllm-output-provenance-binding-report/v1`: copied or exported output
must remain bound to the proof-carrying response after it leaves the API boundary.
The report binds the serving-gateway output hash, attribution capsule, L74
watchtower-cleared settlement report, content-credential assertion, watermark
commitment, fingerprint commitment, and public verification path without embedding
raw generated text.

An output provenance binding report contains:

- declared hashes for the proof-carrying response, serving-gateway report,
  attribution capsule, watchtower challenge settlement report, provider card, and
  certification report
- a subject hash over rendered-output hash, copied-output hash, footer hash,
  gateway-delivered output hash, proof status, watchtower status, and certification
  level
- content-credential rows compatible with C2PA-style attribution assertions
- durable signal rows for content credentials, watermark commitments, and copy
  fingerprint registries
- public verification rows for the well-known output binding report and embedded
  attribution capsule marker

## Post-Release Discovery Reports

L76 adds `rdllm-post-release-discovery-report/v1`: a two-phase discovery artifact
for outputs whose proof-carrying response, serving-gateway report, attribution
capsule, watchtower settlement, output binding, and proof graph are only known
after release. The report binds those late artifacts back to the base discovery
manifest, but it does not mutate that base manifest and it does not catalog its
own hash as an artifact, so the proof surface remains acyclic.

A post-release discovery report contains:

- a release-subject hash over the base discovery manifest, output binding report,
  proof graph, provider card, integration profile, certification report, and copied
  output hash
- a pre-release and post-release artifact catalog with well-known paths, declared
  hashes, payload hashes, reproducibility checks, and release-subject bindings
- verification rows for the post-release report, output-binding report, proof
  dependency graph, and base discovery manifest
- a publication plan proving that the base manifest does not need mutation after
  the answer has been released

The verifier rejects missing content credentials, missing watermark/fingerprint
commitments, gateway-output drift, watchtower settlement failure, provider-surface
drift, private-text leakage, and binding tampering.

## Conformance Verification

The reference verifier checks a complete bundle:

- ledger event
- rendered response with source footer
- attribution receipt
- receipt signature
- transparency log entry
- inclusion proof
- selective-disclosure package
- trace-exchange artifact
- royalty statement rollup
- media attribution report
- model signal attribution report
- rights remediation report
- semantic text attribution report

It fails if any artifact drifts from the others. For example, a source footer cannot
claim `[S1]` while the receipt names a different work; a receipt cannot point to a
different event hash than the ledger; and payout shares must sum to the creator pool.
Rights decisions are also bound into the receipt, so a deployer cannot silently
remove a denied-use decision from the audit trail.
Supported claim span hashes are footer-visible and receipt-bound, so a deployer
cannot replace a supporting passage while leaving the citation label unchanged.
Registry decisions are bound into the receipt too, so a deployer cannot pay a
duplicate claimant while hiding the open conflict from auditors.
The source-access trace and attribution-gap report are bound as well, so a deployer
cannot silently remove a consumed source from the footer or receipt while still
using it for a response.
The selective-disclosure verifier adds a public-facing invariant: a public receipt
cannot change its event hash, source list, claim-support metadata, or disclosure
root without detection, and a disclosed claim cannot be changed without breaking its
salted leaf hash.
The trace-exchange verifier adds a provider-telemetry invariant: every accessed
source span must match the ledger and receipt, every citation span must match the
footer-visible source list, and every claim-support span must match the receipt
claim evidence commitments.
The royalty-statement verifier adds an aggregate invariant: creator totals, escrow
totals, work totals, source usage, event roots, receipt roots, trace roots, and
payout totals must be reproducible from the ledger and bound artifacts without
revealing private text.
The challenge verifier adds a correction invariant: omitted-source remedies must
recompute from the original event and challenged content hash, must not disclose
private text, and must not rewrite the event being challenged.
The lineage verifier adds an upstream-obligation invariant: derivative source
payouts must recursively split across declared lineage edges and preserve the total
source payout without exposing private work text.
The semantic-text verifier adds a paraphrase invariant: a public footer must be
replayable from private submitted text and registered sources, and weak or ambiguous
semantic matches must escrow instead of paying a false owner.

## Provider Attribution Cards

Per-response receipts are too granular for procurement and standards adoption by
themselves. RDLLM therefore emits `rdllm-provider-attribution-card/v1` cards: signed
provider-level disclosures that summarize a deployment without revealing private
prompts, answers, source quotes, claim evidence text, or matched text.

A provider card contains:

- provider and model identity
- bound certification status, report hash, highest level, and case counts
- supported evidence channels, including retrieval, text matching, claim support,
  source-access traces, and training-value priors
- public disclosure surfaces, including footers, receipts, trace exchange, royalty
  statements, challenge reports, answer provenance cards, source verification
  reports, response envelopes, integration profiles, discovery manifests, assurance
  bundles, and interop bundles
- rights and settlement guarantees for policy, registry, unattributed, and
  rights-conflict escrow
- coverage metrics over the current ledger, including event count, source-access
  count, paid source count, escrow share count, attributed coverage, and average
  grounding quality
- evidence roots for ledger events, source accesses, source references, claim
  support, royalty shares, grounding quality, and attribution-gap reports
- explicit limitations, including that model-internal attribution is verified from
  provider-supplied telemetry commitments while raw hidden states and token logits
  remain private

The verifier recomputes the card from the ledger and optional certification report,
rejects coverage drift, rejects stale certification evidence below `RDLLM-L15`, and
checks that private event text is absent from the public card.

## Training Content Summaries

Foundation-model adoption requires a model-level training disclosure, not just
per-answer receipts. RDLLM emits `rdllm-training-content-summary/v1` reports aligned
with EU GPAI training-content summaries, Croissant 1.1 usage policies, SPDX 3 AI and
dataset bill-of-materials concepts, and ODRL rights policies.

A training summary contains:

- provider, model, model version, and training stage
- certification and provider-card bindings
- public template-alignment flags for GPAI, Croissant, SPDX, and ODRL
- aggregate training rights coverage, license counts, source category counts,
  allowed/prohibited use counts, revocation counts, and royalty/attribution duties
- per-work cohort metadata limited to IDs, modality, source category, license,
  source URI, policy ID, content hash, chunk hash root, training decision, and
  training-value commitment
- commitments for work IDs, content hashes, policy decisions, training values,
  certification report hash, and provider-card hash
- privacy guarantees that work text, chunk text, prompts, and answers are not
  disclosed in the public summary

The verifier recomputes the summary from the registered corpus, rejects training
coverage drift, requires at least `RDLLM-L16` certification and provider-card
evidence, and fails if private work text appears in the public report.

## Answer Provenance Cards

The response footer is the human trust surface. RDLLM therefore emits
`rdllm-answer-provenance-card/v1` reports: compact, public cards that bind what the
user sees to the same receipt and provider trace used by auditors.

An answer provenance card contains:

- event hash, answer hash, rendered-output hash, receipt hash, and trace hash
- grounding status, grounding-quality verdict, attribution-gap verdict, policy
  status, registry status, source count, and claim count
- source entries with labels, titles, owners, work IDs, chunk IDs, source URIs,
  content hashes, evidence span hashes, support scores, and contribution weights
- claim entries with claim hashes, source labels, support scores, evidence span
  hashes, and character ranges, without exposing claim or evidence text
- footer checks proving that visible source labels and claim span prefixes match
  the event
- privacy guarantees that prompt text, answer text, source quotes, claim text,
  evidence text, and the full receipt payload are not disclosed in the card

The verifier recomputes the card from the ledger event and optional receipt/trace,
rejects footer relabeling, rejects card tampering, and checks the receipt and trace
bindings when those artifacts are supplied.

## Source Verification Reports

Answer footers must not become decorative citations. RDLLM therefore emits
`rdllm-source-verification-report/v1` reports that materialize every visible source
and supported claim span against the registered corpus.

A source verification report contains:

- event hash, answer hash, rendered-output hash, and optional answer-card hash
- per-source checks for registered chunk existence, source URI, content hash
  reproducibility, work/creator/title/license agreement, quote hash, and quote
  presence in the registered chunk
- per-claim checks for source-label resolution, source chunk agreement, evidence
  hash reproducibility, evidence offsets, and visible footer span prefixes
- roots for the registered chunk corpus, source materialization entries, claim
  materialization entries, visible footer labels, and visible footer spans
- privacy guarantees that prompt text, answer text, source text, source quotes,
  claim text, and evidence text are not disclosed in the report

The verifier recomputes the report from the ledger event and registered corpus,
rejects fabricated source hashes, rejects stale answer-card bindings, and rejects
claim evidence that cannot be reproduced from registered content.

## Response Envelopes

The proof system needs an API-native delivery surface. RDLLM therefore emits
`rdllm-response-envelope/v1` packages: signed response objects that carry the
rendered answer alongside embedded public artifacts.

A response envelope contains:

- the rendered output, rendered-output hash, event hash, source labels, and visible
  claim span prefixes
- embedded answer provenance card, source verification report, source confidence
  report, creator license contract, and optional citation footer, source
  availability, evidence sufficiency, counterevidence, answer claim coverage,
  generation context closure, and source boundary reports
- optional public receipt, provider attribution card, and certification report
- an artifact index with declared hashes, payload hashes, and entry hashes
- commitments for footer labels, footer span prefixes, artifact root, answer-card
  hash, source-verification-report hash, source-confidence-report hash,
  citation-footer-contract hash, late-grounding report hashes, provider-card hash,
  certification hash, and public-receipt hash
- public verification booleans for output/card/report agreement, footer agreement,
  source materialization, late-grounding closure, provider disclosure surfaces, and
  certification posture
- privacy flags that distinguish the visible rendered response from private prompt
  payload, private ledger, and private source corpus disclosure

The verifier recomputes the output hash, footer labels, footer spans, artifact
index, artifact root, embedded artifact hashes, answer-card binding, source-report
status, source-confidence status, optional citation-footer contract binding,
late-grounding report binding, provider response-surface disclosure, and envelope signature without
requiring private ledger access.

## Integration Profiles

The proof objects are only adoption-grade if customers know where to get them and
how to verify them. RDLLM therefore emits `rdllm-integration-profile/v1` reports:
signed provider integration contracts for model APIs.

An integration profile contains:

- provider, model, and model-version identity
- API contract endpoints for generation, response-envelope verification, provider
  cards, certification reports, assurance bundles, and attribution challenges
- required response headers and embedded response-envelope artifacts
- reference verifier commands and required failure modes
- schema paths for every public artifact shape
- required public disclosure surfaces from the provider attribution card
- certification summary, response-envelope hash, provider-card hash, optional
  assurance-bundle hash, and readiness checks
- a small sample response declaration, privacy flags, profile hash, and optional
  issuer signature

The verifier recomputes the profile from the provider card, certification report,
response envelope, and optional assurance bundle. It rejects profile tampering,
provider-surface drift, certification regression, response-envelope drift, missing
schemas, missing verifier commands, and non-ready API contracts. This turns RDLLM
from a file format into a contract that any AI API, chatbot, search product, agent,
or foundation-model provider can publish at a well-known path.

## Assurance Bundles

Provider trust eventually depends on more than one receipt. RDLLM therefore emits
`rdllm-assurance-bundle/v1` reports: public, hash-only bundles that collect the
certification report, attribution receipt, trace exchange, royalty statement,
challenge report, answer provenance card, source verification report, response
envelope, integration profile, provider attribution card, training content
summary, derivative-lineage report, provenance evaluation report, and
counterfactual influence report, media attribution report, model signal report, and
rights remediation report, semantic text attribution report, creator license
contract, source confidence report, citation footer contract, private audit
challenge, revenue allocation report, finance ledger attestation, and
certification attestation into one tamper-sensitive publication artifact.
Downstream settlement artifacts such as transitive attribution, clearinghouse, and
remittance reports are intentionally verified after discovery and bound by the
third-party audit attestation, which prevents the assurance bundle from depending
on reports that depend on the discovery surface.

An assurance bundle contains:

- artifact names, types, declared hashes, payload hashes, and leaf hashes
- a Merkle root and per-artifact inclusion proofs
- publication-profile flags aligned with SCITT-style signed statements,
  Rekor-style transparency inclusion, in-toto-style attestation subjects, and
  C2PA-style conformance assurance
- privacy guarantees that the bundle does not disclose prompt text, answer text,
  source text, evidence text, work text, or full artifact payloads
- an optional issuer signature over the public bundle

The verifier recomputes every artifact hash and inclusion proof from the supplied
payloads, rejects missing proofs or changed artifact hashes, and verifies the
signature when a shared signing secret is supplied.

## Discovery Manifests

Provider adoption needs one stable place where customers, platforms, creators, and
auditors can discover the public proof surfaces. RDLLM therefore emits
`rdllm-discovery-manifest/v1` reports intended for `/.well-known/rdllm.json`.

A discovery manifest contains:

- provider, model, and model-version identity
- well-known paths for the provider card, certification report, integration profile,
  assurance bundle, training summary, provenance evaluation report, counterfactual
  influence report, media attribution report, model signal report, pinpoint
  provenance report, rights remediation report, and sample response envelope
- the API contract hash, endpoint list, required headers, and required embedded
  response-envelope artifacts
- an artifact catalog with paths, declared hashes, payload hashes, and entry hashes
- the schema map, including the discovery-manifest schema itself
- reference verifier commands, required failure modes, readiness checks, summary,
  privacy flags, manifest hash, and optional issuer signature

The verifier recomputes the manifest from the provider card, certification report,
integration profile, response envelope, assurance bundle, and optional training,
provenance-evaluation, counterfactual, media-attribution, model-signal,
pinpoint-provenance, citation-identity, and rights-remediation reports.
It rejects path tampering, artifact-hash drift, API-contract drift, profile
readiness regression, certification regression, missing discovery surfaces, and
assurance bundles that omit response-envelope or integration-profile evidence.

## Cross-Provider Attribution Exchange

Discovery tells a customer where a provider's proof surfaces live. The exchange
manifest tells a second provider how to import and relay those proofs. RDLLM
therefore emits `rdllm-attribution-exchange/v1` reports for downstream AI systems
that summarize, quote, remix, search, or otherwise reuse an upstream AI answer or
source-footer obligation.

An attribution exchange contains:

- the upstream provider identity and minimum upstream certification level
- a relay contract requiring downstream systems to preserve declared hashes,
  source-footer rows, escrow decisions, and upstream/downstream provider identity
- imported artifact rows for provider card, certification report, integration
  profile, discovery manifest, response envelope, assurance bundle, and semantic
  text attribution report
- declared hashes, payload hashes, schemas, and well-known paths for each imported
  artifact
- public source-footer rows copied from semantic text attribution reports
- verification-matrix rows for exchange surface declaration, schema declaration,
  discovery-path declaration, response-envelope verification, assurance coverage,
  semantic-footers, creator-pool conservation, and hash reproducibility
- commitments over imported artifacts, public footers, schemas, and verification
  rows

The exchange is deliberately hash-only except for public footer metadata. It does
not embed prompts, generated answers, private source text, matched text, model
internals, or ledger payloads. A downstream model can therefore cite or route
royalty obligations from an upstream provider without being handed private corpus
material.

The verifier recomputes the exchange from the imported artifacts, verifies the
integration profile, response envelope, discovery manifest, assurance bundle shape,
semantic attribution shape, imported hashes, readiness checks, and signature, and
rejects artifact-hash drift or source-footer replay drift.

## Conformance Vector Pack

A standard is only useful if independent implementations can fail the same tests in
the same way. RDLLM therefore emits `rdllm-conformance-vector-pack/v1`: a signed
test-vector pack for foundation-model providers, marketplaces, auditors, and
regulators.

A conformance vector pack contains:

- fixture hashes for the reference corpora and semantic text input sets
- artifact entries for the provider card, certification report, integration
  profile, discovery manifest, response envelope, assurance bundle, semantic text
  attribution report, and attribution exchange
- public expected outcomes for response-envelope verification, discovery
  publication, semantic paraphrase attribution, exchange relay, full-stack
  certification, and privacy/hash commitments
- negative mutations such as rendered-output hash drift, embedded artifact hash
  drift, footer hash drift, hard-decoy promotion, source-footer removal,
  certification regression, vector expected-status drift, and raw prompt insertion
- the verifier commands each implementer must run
- commitments over artifact rows, fixtures, schemas, and test vectors

The pack does not embed artifact payloads, prompts, outputs, source text, or matched
text. It gives implementers the behavioral contract and failure modes without
turning the standard artifact into a corpus leak.

The verifier recomputes the pack from the public artifacts, verifies the response
envelope and attribution exchange, checks vector hashes and negative-mutation
coverage, enforces the L31 upstream certification floor, and rejects any drift in
expected outcomes or private text disclosure.

## Runtime Federation Handshake

Static publication proves that a provider can produce RDLLM artifacts. Runtime
federation proves that the provider and a downstream AI system negotiated those
artifacts before use. RDLLM emits `rdllm-federation-handshake/v1`: a signed
contract for provider-to-provider attribution relay.

A federation handshake contains:

- requester identity, requester model ID, provider identity, provider model ID,
  requested minimum RDLLM level, and negotiated level
- artifact bindings for the provider card, certification report, integration
  profile, discovery manifest, response envelope, assurance bundle, semantic text
  attribution report, attribution exchange, and conformance vector pack
- required runtime headers: `RDLLM-Handshake-Hash`, `RDLLM-Certification-Level`,
  `RDLLM-Exchange-Hash`, `RDLLM-Vector-Pack-Hash`, and `RDLLM-Signature`
- relay obligations to preserve upstream hashes, preserve public source-footer
  rows, relay escrow obligations, append downstream provider identity, and emit
  new exchange/handshake hashes after material proof changes
- downgrade policy that rejects lower certification levels, missing vectors,
  missing exchange manifests, disabled source-footer relay, disabled escrow relay,
  or unsigned material handshake changes

The handshake remains privacy-safe: it binds hashes, headers, paths, schemas, and
contract metadata, but it does not embed prompts, answers, source text, matched
text, model internals, hidden states, or private ledger payloads.

The verifier recomputes the handshake from public artifacts, verifies the response
envelope, discovery manifest, integration profile, attribution exchange, and vector
pack, checks required headers and relay obligations, enforces the requested
minimum level, and rejects stale hashes, missing artifacts, disabled downgrade
protection, signature drift, or private text disclosure.

## Portable Attribution Capsule

Runtime federation proves that providers negotiated attribution before use. It does
not by itself guarantee that a copied paragraph, reposted answer, exported report,
or generated-media metadata will keep enough attribution context after leaving the
originating AI product. RDLLM therefore emits `rdllm-attribution-capsule/v1`: a
signed, hash-only proof object designed to travel with copied content.

An attribution capsule contains:

- a subject hash over the event ID, event hash, rendered-output hash, answer hash,
  source-label root, claim-span root, source count, and claim count
- artifact bindings for the response envelope, federation handshake, attribution
  exchange, conformance vector pack, provider card, certification report,
  integration profile, discovery manifest, assurance bundle, and semantic text
  attribution report
- a copyable text footer and Markdown marker carrying the capsule ID plus shortened
  output and handshake hashes
- a delivered-output contract that records the body hash, footer marker hash,
  Markdown marker hash, and canonicalization rule for verifying copied text
- runtime headers: `RDLLM-Capsule-ID`, `RDLLM-Capsule-Hash`,
  `RDLLM-Output-Hash`, `RDLLM-Handshake-Hash`, and `RDLLM-Signature`
- a C2PA-compatible assertion pointer and a SCITT-like statement subject binding
  the content digest to the RDLLM handshake hash

The capsule deliberately does not embed the prompt, answer text, matched text,
source text, hidden states, or private ledger payloads. Its verifier recomputes the
capsule from the public proof chain, verifies the response envelope and federation
handshake, checks the copy marker when copied output is supplied, removes the marker
according to the delivery contract, and hashes the copied body. Verification rejects
stale hashes, marker loss, copied-body tampering, missing capsule surfaces, signature
drift, or private text disclosure.

## Transitive Attribution Report

An attribution capsule preserves proof with the copied output. The transitive
attribution report converts that portable proof into downstream settlement.
RDLLM emits `rdllm-transitive-attribution-report/v1` when a copied RDLLM output is
used as input to another model, answer engine, agent, marketplace, or publication
workflow.

A transitive attribution report contains:

- upstream capsule ID, capsule hash, response-envelope hash, rendered-output hash,
  answer-card hash, and answer-card source root
- downstream event hash, prompt hash, answer hash, rendered-output hash,
  copied-input hash, and creator-pool amount
- a policy declaring the pass-through rate, copied-marker requirement,
  copied-body-hash requirement, and residual settlement rule
- upstream source rows copied from the answer provenance card, including creator
  IDs, work IDs, chunk IDs, source URIs, content hashes, contribution weights,
  evidence-span hashes, and source-row hashes, but not source text
- settlement obligations that split the transitive pool across those original
  source rows and bind each obligation to the upstream capsule hash and downstream
  event hash
- commitments over the copied input, downstream event replay, upstream source rows,
  obligations, and policy

The verifier recomputes the report from the upstream capsule, upstream response
envelope, downstream usage event, and copied output. Verification rejects marker
loss, copied-body drift, missing upstream source rows, non-conserved transitive
payouts, stale capsule/envelope hashes, and any disclosure of private prompt,
answer, copied-output, matched, or source text. This is the anti-laundering layer:
a downstream provider can add local sources and settle the residual pool locally,
but cannot turn a reused AI answer into a fresh uncredited source.

## Clearinghouse Report

Per-provider statements prove local payout accounting, and transitive reports prove
second-hop copied-output obligations. A market-scale royalty system also needs a
neutral settlement artifact that can ingest both forms across providers. RDLLM
therefore emits `rdllm-clearinghouse-report/v1`: a signed clearing report that
normalizes each submitted statement and transitive report into one obligation table.

A clearinghouse report contains:

- input artifact rows for each royalty statement and transitive report, including
  provider ID, declared hash, reproducibility status, event roots, downstream event
  hashes, and transitive-pool totals
- normalized obligations with origin artifact reference, recipient creator ID,
  work ID, chunk ID, basis, payout, settlement status, and obligation hash
- payable rows aggregated by creator/work/currency
- escrow rows for unresolved, disputed, or escrow recipients
- held rows for duplicate artifact submissions, duplicate transitive obligations,
  or overlapping statement event hashes
- duplicate rows that show exactly what was held and which earlier artifact or
  event caused the hold
- commitments over input artifacts, normalized obligations, payable rows, escrow
  rows, held rows, duplicate rows, and clearing policy

The verifier recomputes the clearing report from the submitted public statements
and transitive reports. Verification rejects artifact hash drift, non-ready
transitive reports, payable or escrow total drift, duplicate rows that are paid
instead of held, non-conserved status totals, and any private prompt, answer,
source, copied-output, matched, or evidence text disclosure. This turns attribution
from a provider-local proof into a multi-provider settlement rail.

## Response Release Gate

Portable capsules preserve attribution after an answer leaves the origin surface,
but the model still needs an emit-time stop sign. RDLLM therefore emits
`rdllm-response-release-gate/v1`: a signed decision object that says whether the
answer is safe to show before it is displayed, streamed, copied into a downstream
model, or exported into another product.

The release gate recomputes the response envelope, source verification report,
answer provenance card, attribution capsule, provider attribution card, and
certification summary. It emits `decision: emit` only when:

- the response envelope verifies and is bound to the rendered output hash
- cited sources and supported claim spans materialize to registered source hashes
- the footer source labels and claim span prefixes match the answer provenance card
- the attribution capsule binds the same rendered-output hash and delivery contract
- the provider card declares the release-gate public surface
- upstream certification is at least `RDLLM-L34`
- if upstream certification claims L55, L56, or L57, the response envelope embeds
  source availability, evidence sufficiency, and counterevidence reports at the
  corresponding levels and the gate verifies that each report is event-bound,
  hash-reproducible, status-verified, and chained to the footer artifacts
- unsupported claims equal zero for grounded answers
- the gate itself discloses no prompt, answer, matched text, source text, hidden
  state, or private ledger payload

If any check fails, the gate returns `hold_for_revision`. This converts recent
citation-verification findings into a serving boundary: citations are not just
rendered in the footer; they must verify before the user sees the answer.

## Proof-Carrying Response

The release gate is the decision. The proof-carrying response is the delivery
object that makes the decision hard to bypass. RDLLM emits
`rdllm-proof-carrying-response/v1` at the API boundary. It packages the displayed
answer, capsule footer, release gate, response envelope, attribution capsule,
provider attribution card, and certification report into one signed public object.

If the embedded release gate verifies and says `emit`, the proof-carrying response
returns the rendered answer plus the capsule footer. If the gate fails, the object
returns a held-response notice and suppresses the original answer. Its verifier
checks the release gate, envelope hash, capsule marker, copied-output hash,
provider public surface, and certification level. This turns attribution from
metadata attached after generation into proof-carrying generation: the answer and
its source-support proof cross the serving boundary together.

## Serving Gateway Report

The proof-carrying response proves what may be delivered. The serving gateway
report proves what actually left the API route. RDLLM emits
`rdllm-serving-gateway-report/v1` as an ingress/egress enforcement artifact. It
hash-commits the private prompt and raw model output, embeds the proof-carrying
response, binds the proof-response hash and release-gate hash, and records the
delivered-output hash.

The gateway verifier checks that egress equals the proof-carrying response copied
output, that the provider declares the gateway surface, that the embedded proof
response verifies, and that tampering with the delivered-output hash is rejected.
This closes the operational gap between a provider publishing proofs and a provider
actually routing every production answer through the proof-carrying response path.

## Creator License Contract

Attribution must start before retrieval, training, generation, display, or external
text matching. RDLLM therefore emits `rdllm-creator-license-contract/v1` as a
machine-readable contract over registered works. Each term binds a work ID,
creator ID, title hash, content hash, source URI, license URI, policy ID, allowed
uses, prohibited uses, jurisdictions, attribution duty, royalty duty, minimum
creator-pool rate, revocation state, ODRL/Croissant/SPDX-aligned policy metadata,
and a hashed payout-account commitment.

The contract verifier recomputes terms from the registered corpus, rejects
use-scope or royalty-term tampering, checks that attribution and compensation
duties are present, and proves that work text and raw payout accounts are not
published. This turns "we had permission" into an artifact that can be cited,
discovered, audited, and bound into procurement or billing systems.

## Source Confidence Report

Source footers are only useful if the user can tell whether the listed sources are
real, relevant, licensed, and claim-supporting. RDLLM therefore emits
`rdllm-source-confidence-report/v1` as the public footer confidence layer. It
recomputes source rows from the answer provenance card, source verification report,
and creator license contract. Each row exposes public metadata, content-hash
prefixes, support scores, retrieval scores, text-match scores, confidence score,
and confidence level without publishing source text, claim text, evidence text, or
payout accounts.

The report also emits claim rows and a hallucination taxonomy. The taxonomy counts
fabricated source labels, registry metadata drift, content-hash mismatch, footer
omission, license gaps, unsupported claims, evidence-span gaps, failed sources, and
failed claims. A response can be marked `verified` only when the answer-card hash,
source-verification hash, source-materialization status, creator license contract,
source rows, claim rows, and footer rows all agree and the hallucination issue
count is zero.

## Citation Footer Contract

The final user-visible step is rendering. Even a verified confidence report can be
lost if a client omits a row, changes the display order, strips the confidence
label, or hides license and royalty status. RDLLM therefore emits
`rdllm-citation-footer-contract/v1` as a signed display contract for response
clients.

A citation footer contract contains:

- the response event hash, rendered-output hash, answer-card hash, source
  verification hash, source-confidence hash, creator-license hash, and response
  boundary hash
- exact source display rows with source label, title, creator, work ID, chunk ID,
  source URI, content-hash prefix, confidence score, license status, royalty status,
  source-selection rationale, rationale hash, display text, and row hash
- exact claim anchor rows with claim index, source label, evidence-span prefix,
  support score, confidence score, and row hash
- rendered footer lines, source-label order, claim-span prefixes, and footer hash
- verification booleans proving the footer rows match the response envelope,
  source-confidence report, creator-license terms, displayed labels, and displayed
  claim span prefixes
- privacy flags proving the contract discloses footer metadata only, not prompt,
  answer, source, claim, evidence, or payout-account text

The verifier recomputes the contract from the response envelope and rejects footer
line drift, source omission, claim-anchor drift, inactive license or royalty duties,
failed source confidence rows, missing source-selection rationale, signature drift,
and private-text leakage. This
turns the footer into a grounded UI surface: the API customer can render the
contract's `rendered_footer.footer_text`, and a user can know that the visible
sources are the same sources that passed materialization, license, confidence, and
royalty checks.

## Rendered Attribution Audit

The final trust boundary is the literal response body delivered to the user. A
valid footer contract can still be undermined by a renderer that rewrites inline
source markers, drops a source row, appends unsupported text, or changes claim
span anchors after verification. RDLLM therefore emits
`rdllm-rendered-attribution-audit/v1` for the exact visible Markdown output.

The audit derives hash-only rows from the displayed answer body, source footer,
and claim-evidence section. Verification requires body `[S#]` markers to match
the response envelope source labels, footer sources to match both body markers
and the citation footer contract, footer rows to include resolvable URIs and
content-hash prefixes plus a `why=...` source-selection reason, claim-evidence
rows to cover every answer-coverage pair, and each claim span to bind back to the
rendered footer. It also replays source
availability, evidence sufficiency, counterevidence, and answer claim coverage
status. This is the user-facing anti-hallucination proof: the visible sources are
not decorative text, but the same source rows and spans that survived the proof
chain.

## Training-Memory Provenance

Retrieval logs are insufficient when a model reproduces or closely paraphrases
registered training text from parametric memory. RDLLM therefore emits
`rdllm-training-memory-provenance/v1` after the rendered attribution audit. The
report scans the exact displayed answer body against registered source snapshots,
binds detected memorized spans to training-content summaries and creator-license
contracts, and requires the matching source to appear in the visible footer before
display.

The public report is hash-only: it records source snapshot commitments, matched
sequence hashes, token counts, coverage ratios, license/training/display
permission checks, visible-source labels, and remediation rows. It fails if a
memorized registered span is hidden from the footer, if the source hash is absent
from the training summary or license contract, if the rendered output hash drifts,
or if raw answer, prompt, source, or matched text appears in the public artifact.
This closes the gap between "the model cited what it retrieved" and "the model
credited what it remembered."

## Evidence-Locked Generation

Post-hoc citations are still possible if a model generates an answer first and
then attaches plausible-looking sources afterward. RDLLM therefore emits
`rdllm-evidence-locked-generation/v1` after training-memory provenance and before
release. The report requires each support-bearing answer unit to have a
pre-generation lock that binds the answer-unit hash, claim hash, source label,
generation-context block, source-access ID, footer row, body marker, and rendered
claim-evidence span.

The public report is hash-only and fails if the lock timestamp is after
generation start, if any support-required unit lacks a satisfied lock, if a
footer source has no matching lock, if the rendered answer hash drifts from
coverage or audit artifacts, if training-memory provenance reports hidden
memorized spans, or if raw answer, prompt, source, claim, or context text appears
in the report. This closes the gap between "the visible citation can be checked"
and "the model was constrained by that evidence before emitting the answer."

## Emission Evidence Enforcement

Evidence locks are strongest when the serving boundary proves they were enforced
while output left the system. RDLLM therefore emits
`rdllm-emission-evidence-enforcement/v1` after the proof-carrying response,
serving-gateway report, and streaming attribution manifest exist. The report binds
the rendered output hash, copied output hash, gateway egress hash, stream output
hash, proof-response hash, gateway-report hash, and streaming-manifest hash to the
same L82 evidence-lock root.

For every support-required answer unit, the report records the unit hash, claim
index, source label, evidence prefix, evidence-lock row hash, proof-response hash,
gateway hash, streaming hash, and booleans proving the unit was covered, locked,
lock-satisfied, stream-bound, and authorized for emission. It fails if streaming
starts before the evidence lock and generation window, if gateway/proof/stream
hashes disagree, if any support-required unit lacks a satisfied lock, if stream
chunks cannot be replayed from the public output, or if raw answer, prompt,
source, claim, context, or chunk text appears in the public report.

## Live Emission Witness

Post-stream enforcement is still weaker than witnessed serving. RDLLM therefore
emits `rdllm-live-emission-witness/v1`: a signed report with two independent
quorum phases. The preflight phase cosigns the proof response, gateway report,
evidence-lock root, support-unit authorization root, and planned stream boundary
before the first chunk is admitted. The completion phase cosigns the final stream
chain, chunk-subject root, output hash, and L83 emission-enforcement hash after
the final chunk is committed.

The public report stores witness IDs, organization IDs, signature hashes,
preflight/completion subject hashes, chunk row hashes, timing booleans, and quorum
results. It fails if preflight witnesses observe after stream start, if completion
witnesses sign before the final chain exists, if the quorum or independent
organization threshold is not met, if the streaming manifest drifts from L83, if
chunk rows are missing, or if raw prompt, answer, source, claim, context, or chunk
text appears in the report.

## Live Emission Transparency

Witness quorum is not enough if the provider can hide an unfavorable witness view
or show different live-emission histories to different auditors. RDLLM therefore
emits `rdllm-live-emission-transparency/v1`: a signed hash-only report over the
L84 live witness report and append-only transparency-log snapshots. The report
requires the live witness report subject and every preflight/completion witness
attestation subject to appear in the latest log with valid inclusion proofs.

The transparency report also verifies append-only prefix consistency between older
and newer log snapshots, recomputes tree sizes and Merkle roots, rejects
same-size split-view roots, checks subject payload hashes and entry types, and
fails if private prompt, answer, source, claim, context, chunk, or credential
fields appear. This turns "independent witnesses saw the stream" into "the public
emission history cannot omit or fork those witnesses without detection."

## Attested Attribution Runtime

The transparency layer proves live witness subjects were logged, but not which
runtime enforced the attribution checks. RDLLM therefore emits
`rdllm-attested-attribution-runtime/v1`: a signed report that binds the live
transparency report, proof-carrying response, serving-gateway report, and
evidence-locked-generation report to a deterministic runtime measurement.

The measurement commits to source revision, container image, enforcement binary,
policy bundle, model binding, verifier bundle, and required capabilities. The
attestor quote signs that measurement plus the subject binding root and nonce. The
reference implementation uses HMAC conformance quotes so the mechanism is runnable
in this repository; production deployments can replace those quotes with hardware
TEE, ZKML, or hybrid attestation evidence while preserving the same public
verification contract.

Certification rejects untrusted attestors, stale quotes, measurement drift,
subject-binding drift, missing runtime capabilities, and public reports that expose
prompt, answer, source, claim, chunk, or secret fields.

## Private Audit Challenge

Public proof should not publish raw prompts, source text, evidence text, access
trace details, salts, or payout accounts. Yet auditors still need to test whether a
provider can open the private basis for a displayed source row or paid royalty
share. RDLLM therefore emits `rdllm-private-audit-challenge/v1` as a signed,
nonce-bound audit certificate over selected hidden receipt paths.

A private audit challenge contains:

- auditor ID, challenge nonce, requested JSON-pointer paths, requested-path root,
  and challenge binding hash
- receipt hash, payload hash, disclosure root, selective-disclosure package hash,
  and public-receipt hash
- per-path rows with category, disclosure status, private-path flag, leaf hash,
  value hash, salt hash, opening commitment, and row hash
- verification booleans proving the selective-disclosure package verifies, the
  private receipt opens the requested paths, package leaves match private leaves,
  commitments are nonce-bound, and no private values are disclosed
- privacy flags proving the report names paths but hides values and salts

The verifier recomputes the openings from the private receipt and rejects replayed
nonces, missing paths, mismatched source-access or claim-evidence leaves, rights or
payout drift, raw opening material, signature drift, and private-text leakage. This
lets regulators, collective-management organizations, publishers, creators, and
enterprise buyers audit hidden evidence without forcing the provider to publish
confidential prompts, evidence text, or economics.

## Reference Certification Suite

The `certify` command turns the verifier into a portable implementation test. It
emits a machine-readable report with eighty-two cases:

- grounded generation with source labels, claim support, span hashes, rights allow
  decisions, and balanced payouts
- external text attribution for outputs generated by another AI system
- unattributed escrow when no registered owner can be traced
- rights-blocked generation when a source is retrievable but not licensed for the
  attempted use
- signed receipt, public receipt, transparency log, and inclusion proof conformance
- tamper detection for missing footer span hashes and modified receipt payloads
- rights manifest export with ODRL, Croissant, SPDX, and PROV-aligned fields
- grounding quality scoring and tamper-sensitive citation-quality verdicts
- registry dispute escrow for duplicate ownership claims
- registry escrow resolution after a dispute is resolved
- interop export as signed credential-shaped artifacts and a provenance graph
- attribution-gap accountability for consumed, cited, paid, and escrowed sources
- selective-disclosure receipts that prove public source attribution while redacting
  private evidence, access, and payout fields
- trace-exchange accountability that proves provider telemetry covers source access,
  footer citations, claim support, and receipt telemetry commitments
- royalty-statement rollups that prove aggregate creator, escrow, work, source,
  receipt, and trace commitments without exposing private text
- attribution-challenge correction that accepts an omitted source, rejects remedy
  tampering, avoids double payment when the source was already credited, and keeps
  private prompt/source/matched text out of the public challenge
- derivative-lineage royalties that route source payouts through declared
  derivative-work edges while preserving upstream obligations and redacting private
  work text
- provenance-benchmark evaluation that proves clean-source, paraphrase,
  hard-decoy, unattributed-escrow, and derivative-lineage source attribution can be
  replayed without leaking benchmark text
- counterfactual-influence verification that removes credited works, replays the
  same prompt and answer, proves source removal and payout reallocation, and
  rejects impact-margin tampering without exposing private text
- provider-attribution-card verification that binds certification, coverage,
  supported surfaces, challenge policy, limitations, and privacy-safe evidence roots
- training-content-summary verification that binds GPAI/Croissant/SPDX/ODRL
  alignment, training rights coverage, license/use counts, policy roots,
  content-hash roots, and training-value commitments
- assurance-bundle publication that binds proof-pack artifact hashes, Merkle roots,
  inclusion proofs, and privacy guarantees
- answer-provenance-card verification that binds visible footers, claim span
  hashes, receipt hashes, trace hashes, and grounding verdicts without private text
- source-materialization verification that proves cited source hashes, quote hashes,
  source URIs, claim evidence spans, answer-card bindings, and visible footer
  prefixes resolve to registered content without private text
- response-envelope public verification that packages the rendered answer with
  public artifacts and rejects output or embedded-artifact tampering
- integration-profile contract verification that publishes the API contract,
  schemas, verifier commands, public surfaces, readiness checks, and bound proof
  hashes for provider adoption
- discovery-manifest publication that exposes well-known artifact paths, schemas,
  verifier commands, readiness checks, and bound proof hashes
- multimodal-media attribution verification that matches image, audio, video, 3D,
  and text-shaped signatures while preserving creator-pool conservation
- model-internal signal attribution verification that binds provider-private
  telemetry to an explicit attribution contract, accepts strong sources, escrows
  weak or zero-confidence influence, conserves payout, and rejects private telemetry
  leakage
- post-publication rights-remediation verification that preserves historical event
  hashes, proves future denied use after revocation, routes blocked value to
  rights-conflict escrow, and rejects private text leakage
- semantic-text-attribution verification that attributes paraphrased or external
  outputs to registered owners, publishes source footer commitments, escrows
  ambiguous matches, and rejects private text leakage
- cross-provider attribution-exchange verification that imports provider proofs by
  hash, relays public source footers and escrow obligations, and rejects proof drift
- portable-conformance-vector verification that publishes expected outcomes,
  verifier commands, and negative mutations for independent implementations
- runtime-federation-handshake verification that negotiates attribution level,
  runtime headers, required artifact hashes, source-footer relay, escrow relay, and
  downgrade rejection before cross-provider use
- portable-attribution-capsule verification that binds copied output markers,
  delivered-body hashes, proof-chain hashes, C2PA-compatible assertions, and
  SCITT-like statement subjects while rejecting marker loss, copied-body tampering,
  hash drift, and private text leakage
- response-release-gate verification that emits grounded answers only when source
  materialization, footer source labels, claim span coverage, capsule binding,
  provider public surfaces, and `RDLLM-L34` upstream certification all verify
- proof-carrying-response verification that releases the answer only when the gate
  verifies, attaches the capsule marker to copied output, suppresses the original
  answer on gate failure, and rejects display-payload tampering
- serving-gateway-report verification that proves API egress delivered the
  proof-carrying response output, hash-committed the private prompt and raw model
  output, bound the provider gateway surface, and rejected egress-hash tampering
- creator-license-contract verification that binds source-use scopes,
  attribution duties, royalty duties, revocation state, content hashes, and
  payout-account commitments before use while rejecting rights-term tampering and
  private text disclosure
- source-confidence-report verification that turns materialized sources and license
  terms into public footer confidence rows, rejects metadata drift and license
  gaps, and reports zero hallucination issues before an answer is marked verified
- citation-footer-contract verification that binds exact source lines, claim
  anchors, confidence labels, license status, royalty status, and footer hash to the
  response proofs before clients render the footer
- rendered-attribution-audit verification that parses the exact displayed Markdown
  answer and proves inline source markers, footer source rows, and claim-evidence
  span rows match the response envelope and grounding reports
- training-memory-provenance verification that detects registered memorized spans
  in the exact displayed answer and fails release unless they are visibly
  attributed, licensed, and bound to the training-content summary
- evidence-locked-generation verification that proves every support-required
  answer unit was bound to source evidence, context closure, footer display, and
  rendered claim-evidence rows before generation started
- emission-evidence-enforcement verification that proves served and streamed
  output used those satisfied evidence locks before chunks left the serving
  boundary
- private-audit-challenge verification that opens selected redacted source-access,
  claim-evidence, rights, and payout paths under auditor nonce without public
  private-text disclosure
- transitive-attribution-flow verification that binds downstream copied-output use
  to the upstream capsule and answer-card source rows, conserves pass-through
  settlement, and rejects marker loss or copied-body drift
- cross-provider-clearinghouse-settlement verification that normalizes royalty
  statements and transitive reports into payable, escrow, and held rows, conserves
  status totals, and rejects duplicate payment or clearing tampering
- verifiable-remittance-instructions verification that converts clearinghouse
  payable and escrow rows into instruction-only payment rows, binds payout-account
  hashes from creator license contracts, preserves held rows, and rejects account
  leakage or settlement overclaiming
- payment-execution-attestation verification that reconciles remittance rows
  against hash-only external payment and escrow processor records, verifies
  amounts, currencies, end-to-end IDs, account hashes, settlement statuses,
  duplicate and unmatched rows, and rejects raw payment-field leakage before payout
  value is treated as executed
- third-party-audit-attestation verification that proves an independent auditor can
  replay the public proof pack, bind provider surfaces through discovery, attest to
  response-footers, clearing, remittance, and optional payment execution, and reject
  proof-pack drift without publishing private text
- usage-revenue-allocation verification that proves source revenue pools conserve
  into event-level gross revenue, creator-pool totals match allocated revenue, and
  private billing identifiers remain hash-only
- finance-ledger-attestation verification that proves hash-only finance exports
  reconcile to revenue allocation source pools, match allocation totals, and reject
  duplicate rows, stale hashes, currency drift, amount drift, and private finance
  fields
- proof-dependency-graph verification that publishes a topological replay plan,
  separates replay dependencies from publication commitments, and rejects cycles,
  unknown dependencies, stale graph hashes, and private-field leakage
- publication-monitor verification that publishes append-only artifact
  checkpoints, proves snapshot inclusion, detects certification regression, and
  rejects checkpoint tampering or private-field leakage
- publication-witness verification that binds monitor checkpoints to independent
  witness signatures, enforces quorum, detects split views, and rejects private
  monitor-payload leakage
- trust-registry verification that binds active provider and witness keys to signed
  public artifacts, key rotations, revoked keys, and witness attestations without
  disclosing raw key material
- certification-attestation verification that binds the certification report hash,
  attested level, levels root, case-status root, certifier identity, and signature
  into a trust-registry-verifiable public object
- generated-code-attribution verification that binds copied or derived code snippets
  to registered source owners, license compatibility decisions, payout or escrow,
  and privacy-safe line/token commitments
- pre-settlement claim-verification that allows direct settlement only for trusted
  signed ownership claims and routes duplicate, weak, or unverified claims to escrow
- source-availability verification that binds user-facing footer rows to reachable
  or archived source snapshots, registered content hashes, cited claim spans, and
  the source-verification and citation-footer artifacts
- evidence-sufficiency verification that ranks candidate evidence spans for every
  claim, requires the cited span to be the top-ranked minimal sufficient support,
  requires a margin over decoy evidence, and binds the result to source
  availability, source verification, and citation-footer artifacts
- counterevidence adjudication that scans registered source spans for contradiction
  candidates and blocks release when a claim leaves counterevidence unaddressed
- release grounding closure that prevents high-certification providers from serving
  a response envelope unless the L55-L57 source availability, evidence sufficiency,
  and counterevidence reports are embedded, hash-bound, and release-gate verified
- answer claim coverage that prevents providers from appending unsupported public
  answer sentences before or after the citation footer unless those sentences
  replay to verified, sufficient, counterevidence-free claim rows
- generation context closure that prevents providers from attaching plausible
  sources after the fact unless each verified claim replays to source-access spans
  and redacted context commitments present before generation
- source boundary integrity that prevents retrieved, uploaded, web, tool, corpus,
  or downstream AI source packets from acting as control or instruction channels
  and proves those packets could not modify attribution or payout policy
- decision provenance that proves claim, footer, payout, and release decisions used
  only authorized proof, policy, accounting, and boundary-guard channels
- calibrated attribution confidence that attaches benchmark-backed lower bounds to
  public claim, footer, and payout attribution so uncertainty is visible and
  reproducible
- source authenticity and poisoning resilience that proves verified source rows
  carry trusted origin evidence, active license terms, archive consensus, and low
  poisoning/source-farm risk before direct payment
- streaming attribution commitments that hash-chain every emitted stream chunk to
  the proof-carrying response, serving gateway report, and final attribution
  footer so streamed APIs cannot leak unproven text before the source footer lands
- conversation attribution continuity that hash-chains stateful turns and requires
  follow-up answers to carry inherited source rows and royalty obligations from
  prior turns when they depend on earlier conversation context
- agent-tool attribution trajectories that bind each retrieval, web, file,
  function, code, MCP, or remote-tool observation to trace spans, visible source
  rows, supported claims, and continuing conversation-level obligations
- pinpoint provenance reports that reject topical anti-documents and require
  answer-critical fact support before a source can appear in a footer or receive
  direct payout
- citation identity reports that reject fabricated, unresolved, metadata-swapped,
  or claim-unsupported public citations before canonical footer display or
  citation-linked payout
- attribution consensus reports that require all settlement-critical attribution
  channels to agree before direct payout
- independent verifier quorum reports that require external signed replay
  agreement before direct settlement
- bonded verifier accountability reports that require registry identity, bond
  coverage, conflict disclosure, and no open verifier challenge before settlement
  can leave escrow
- receipt transparency consistency reports that require append-only usage receipt
  logs, required receipt inclusion proofs, and no split-view roots before
  settlement can leave escrow
- watchtower challenge settlement reports that require independent registered
  watchtower attestations and no open or accepted public challenge before
  receipt-transparent settlement can leave escrow
- output provenance binding reports that keep copied or exported output tied to
  proof-carrying responses, content credentials, watermark/fingerprint commitments,
  and public verification paths
- post-release discovery reports that publish late-bound output proof artifacts
  without mutating base discovery or creating self-referential hash cycles
- payment execution reports that reconcile instruction-only remittance rows against
  processor and escrow settlement evidence before settlement is claimed as paid
- payment rail attestations that require registered external processors to sign
  the hash-only settlement batches behind payment execution
- creator payout receipt reports that let creators verify their attributed works,
  payable/escrow/hold status, remittance row, execution row, and signed rail batch
  without exposing prompts, source text, customer data, or raw payment accounts
- rendered attribution audits that prove the user-visible Markdown answer, source
  footer, and claim-evidence rows match the signed response and grounding artifacts
- training-memory provenance reports that detect registered memorized source spans
  in the rendered answer and require visible attribution before display
- evidence-locked generation reports that reject post-hoc citation rationalization
  by requiring pre-generation evidence locks for every support-required answer unit
- emission evidence enforcement reports that bind proof-carrying response,
  serving-gateway egress, streaming chunks, and satisfied evidence locks to the
  same output
- live emission witness reports that require independent preflight and completion
  quorum signatures over the stream boundary
- attested attribution runtime reports that bind those live-transparent outputs to
  measured attribution-enforcement code and trusted attestor quotes
- claim-source attribution reports that replay every visible claim against
  candidate sources, anti-documents, Q&A nugget commitments, visual-region
  commitments, footer rows, and LOO-style source contribution
- causal evidence-utility reports that bind credited footer rows to current-turn
  retrieval/tool traces and source intervention trials so spurious, duplicate, or
  prior-context citations cannot receive footer credit or payout
- parametric memory attribution reports that bind model-weight answers to
  training-summary membership, memory probes, influence or model-signal evidence,
  anti-document separation, and current-context contamination checks
- style influence attribution reports that credit licensed creator style or voice
  profiles only when style similarity, declared intent, anti-style separation,
  copy-overlap guards, and royalty conservation pass
- model-lineage attribution reports that preserve upstream creator obligations
  when attributed outputs, synthetic data, or teacher traces train, fine-tune, or
  distill a downstream model
- black-box model provenance reports that challenge likely undisclosed derivative
  models with API-visible behavior, baseline distributions, watermark or
  fingerprint signals, source footers, and payout or escrow obligations
- attribution dispute adjudication reports that freeze disputed value, accept
  claimant and respondent evidence by hash commitment, require bonded independent
  verifier quorum, enforce appeal windows, release or preserve escrow, and record
  slashing or bounty outcomes without revealing private text
- post-adjudication settlement adjustment reports that preserve historical payment
  hashes while issuing forward-only top-ups, capped future netting, appeal freezes,
  and creator-visible adjustment receipts after attribution decisions change
- residual corpus royalty reports that settle diffuse licensed training-corpus
  value separately from visible answer footers and direct attribution payout
- valuation method audit reports that benchmark residual-corpus valuation methods
  against known contributors, hard anti-documents, duplicate guards, calibration,
  stability, method commitments, and privacy commitments before residual payout
- evidence-region binding reports that bind every rendered claim span and footer
  source row to exact page, line, character, bounding-box, or timecode regions and
  reject plausible but unsupported neighboring regions
- source access lease reports that require directly settled consumed sources to
  have creator-issued active leases, matching access logs, license-contract
  permission, region binding, and escrow for denied or unleased use
- content-protocol ingestion reports that prove external publisher rights
  protocols such as RSL, CoMP, SCP, ODRL, Croissant, robots.txt, and C2PA/TDM
  reservations were discovered, hash-preserved, and carried into RDLLM contracts,
  source-access leases, and escrow routing
- citation reliance receipts that prove visible footer sources were actually
  relied on through pre-generation evidence locks, rendered claim evidence,
  claim-source replay, causal utility, current-turn trace membership, access
  leases, and content-protocol permission
- license transaction receipts that prove each directly settled source had a
  signed license-server authorization token, license-ledger inclusion, access-log
  binding, protocol-term match, and valid transaction window before access
- grounded source footer receipts that prove the exact user-visible footer rows
  are backed by source confidence, source availability, public evidence-region
  bindings, citation reliance, license transactions, and public verifier handles
- source footer delivery receipts that prove those grounded footer rows, source
  labels, claim span handles, verifier metadata, proof-carrying responses, and
  serving-gateway egress hashes all match before client display
- foundation API attribution profiles that define the minimum model API response
  contract: required attribution headers, embedded proof objects, verifier
  endpoint, well-known discovery paths, verifier commands, and fail-closed client
  policy
- client attribution enforcement receipts that prove the relying client observed
  those headers and embedded proof objects, replayed the source-footer delivery,
  matched source labels, and blocked rendering on drift
- persistent memory provenance receipts that treat assistant, agent, or model
  memory cells as derived works with source labels, upstream proof hashes,
  license and retention policy, royalty carry-forward, delete tombstones, and
  visible footer carry-forward when reused
- private reasoning attribution receipts that keep chain-of-thought private while
  proving hidden scratchpads, delegation, and memory-influenced reasoning carry
  source labels, upstream proof hashes, and royalty rows into the verified footer
- post-training signal provenance receipts that prove RLHF, RLAIF, RLVR,
  preference, reward, verifier, and critique signals preserve source labels,
  upstream proof hashes, synthetic disclosure, attestations, model-lineage
  settlement, and royalty carry-forward before shaping later model behavior
- attribution bills of materials that publish a CycloneDX-aligned model supply
  chain record with source components, notice hashes, license-term hashes, proof
  artifact hashes, post-training provenance, and the proof-dependency graph
- creator attribution audit indexes that let creators query their works across
  release, footer, delivery, post-training, access, license, lineage, and payout
  proof surfaces with namespaced source identities and privacy-preserving handles
- creator attribution audit federations that let creators replay the same query
  across multiple provider-local indexes with provider-scoped namespaces,
  federation/exchange bindings, and creator identity conflict detection
- creator audit federation transparency reports that prove the L111 federation
  answer and participant index hashes were included in append-only logs and were
  not split-viewed or replaced for the same query/provider set
- creator audit transparency monitors that let creators and auditors scan L112
  logs for their query commitments, prove matching entry inclusion, report new
  appearances since the previous monitor run, and reject contradictory federation
  or participant-index answers
- creator audit private watch receipts that replace public stable monitor
  identifiers with keyed watch tokens for creator-side verification without
  leaking query hashes, provider-set hashes, subject hashes, provider IDs, or raw
  private text
- deep-research citation audit reports that parse rendered long-form answers,
  resolve every citation marker to materialized source rows, bind claim hashes to
  source and quote hashes, and reject source-looking citations that fail link,
  relevance, or factual-support checks
- source freshness audit reports that classify static, current, latest, recent,
  rapidly changing, and as-of claims, enforce retrieved-at/effective-at metadata,
  check source-version validity at answer time, and reject stale selected sources
  or ignored fresher supported candidates
- royalty-abuse audit reports that block direct settlement for source farms,
  sybil or linked creators, duplicate-source payout splitting, reciprocal
  boosting, undisclosed synthetic sources, and direct-payout concentration
- consent revocation propagation reports that prove opt-outs, revocations,
  lease expiry, or license changes reached retrieval indexes, source-access
  leases, license transactions, source footers, memory, private reasoning,
  post-training signals, attribution exchange, creator audit surfaces, downstream
  notices, and settlement before future use or direct payout
- evidence-force calibration reports that prove a cited claim's relation,
  modality, scope, temporal, and numeric force does not exceed what the cited
  evidence warrants, and that every visible verified footer claim has a matching
  calibrated force row before a footer can be verified or a source can be paid
  directly
- warranted source footer reports that expose those relation, modality, scope,
  temporal, and numeric warrant labels in the visible footer so users can see
  whether a source supports the answer wording without seeing private claim or
  evidence text
- source-origin lineage reports that prove each visible source is either a
  trusted human-origin source eligible for direct payout, a synthetic source with
  active upstream creator splits, or an unknown/unattributed synthetic source
  routed to origin-review escrow
- evidence-preview footer reports that publish short permissioned source
  snippets, source URLs, warrant labels, origin labels, settlement labels, and
  proof hashes for each verified visible claim without exposing full source text
- evidence-locator manifests that bind each public preview snippet to an exact
  resolver URL, resolver status, and snapshot or text-fragment proof so readers
  can inspect the precise cited passage
- citation URL-health reports that classify each public evidence locator as
  live, content-addressed, DOI-resolved, archival link rot, fabricated, or
  unverified, failing closed on fabricated and never-seen sources
- composite foundation adapter reports that map provider-native OpenAI Responses,
  Anthropic Messages, Google Gemini, Meta/Llama-style, Mistral, Cohere, xAI,
  Amazon Bedrock Converse, Azure OpenAI Responses, and OpenAI-compatible response
  objects into the same RDLLM response envelope, source-footer-delivery receipt,
  citation URL-health receipt, attribution headers, JSON proof fields,
  citation/tool paths, streaming final-event hashes, and fail-closed verifier
  policy
- foundation provider conformance matrices that require each provider family to
  publish hash-only positive and negative fixtures for sync response, streaming,
  tool use, citation/grounding, URL-health binding, claim-support footers,
  parametric-memory fallback, structured proof fields, and fail-closed behavior
- foundation runtime adapter receipts that verify a concrete native provider
  response against the RDLLM proof contract before display, including attribution
  headers, JSON proof hashes, stream-final metadata, citation paths, URL-health
  evidence, and source-footer bindings
- foundation runtime router receipts that verify multi-provider routing and
  fallback stacks before display, including selected-route binding to L127,
  adapter/conformance backing for every candidate route, route-health hashes, and
  fail-closed fallback decisions
- foundation model deployment attestations that verify the selected route is bound
  to an active provider deployment key, signed model/version commitments, and
  request/response boundary hashes before display
- universal composition receipts that verify each provider segment in a composite
  answer has one matching L129 deployment attestation, preserved footer
  obligations, telemetry span commitments, and conserved provider weights
- universal composition settlement receipts that verify each L130 segment's
  source labels and claim IDs clear into source-entitlement rows, payable/escrow/
  held creator obligations, preserved source-footer delivery, and conserved
  revenue allocation creator-pool totals
- universal foundation model contracts that verify every supported foundation
  provider family shares the same adapter, conformance, runtime, router,
  deployment, composition, settlement, discovery, and public-surface proof chain
  before a response can be released as RDLLM verified
- universal invocation guards that verify each concrete native provider call is
  preflight-authorized against the L132 contract, selected route, deployment
  attestation, request/response boundary, source-footer requirement, fail-closed
  headers, and GenAI telemetry before invocation
- universal invocation coverage reports that verify every native provider meter
  event reconciles to exactly one L133 guard, gateway egress row, source-footer
  binding, response-envelope binding, and invoice row before coverage is certified
- universal invocation witness reports that verify every L134-covered native
  provider call binds to a provider-signed usage receipt, independently observed
  egress event, and independent witness quorum before non-repudiation is certified
- universal content credentials that verify released or copied outputs bind the
  visible source footer, evidence previews, exact locators, URL-health rows,
  payout eligibility, output content credentials, durable watermark/fingerprint
  signals, public verifier surfaces, and the L135 invocation witness before the
  output can be treated as portable, grounded, and payable
- universal RDLLM passports that verify the complete L136 source/payout/content
  credential is bound to provider certification, public discovery, foundation
  adapters, runtime guardrails, invocation non-repudiation, verifier commands, and
  research-control rows across supported foundation-model provider families
- universal grounded reuse contracts that require cached or replayed answers to
  preserve L141 citation grounding, replay freshness and rights state, reject
  cache-collision risk, and emit a new royalty-metered reuse event before a cache
  hit can be served as grounded
- universal training-to-serving attribution contracts that bind pretraining,
  fine-tuning, adapters, post-training signals, distillation, synthetic data,
  release snapshots, provider routes, grounded reuse, visible citation footers,
  revocation propagation, residual royalties, valuation methods, and serving
  meters before a foundation-model deployment can claim attribution survives from
  training into served answers
- universal confidential attribution audits that bind private training,
  post-training, serving, citation, valuation, revocation, and creator-query
  evidence to hash commitments, ZK/TEE/selective-disclosure proof handles,
  auditor quorum, creator challenge routes, regulator export support, and
  fail-closed leakage checks without exposing raw corpora, prompts, answers,
  source text, reward data, customer logs, or model internals
- universal attribution authority control planes that bind model APIs, agent
  runtimes, MCP-style tools, retrieval connectors, memory stores, browser/file/code
  actions, enterprise gateways, and settlement gateways to signed actor, intent,
  context, tool, model-invocation, inference, memory, settlement, publication,
  challenge, intervention, and revocation authority before release
- universal RDLLM roots that bind certification, attestation, provider card,
  integration, discovery, assurance, proof graph, source-footer delivery,
  training-to-serving continuity, confidential audit, runtime authority, and
  settlement posture into one provider-neutral root before a deployment can claim
  that its grounded answer footers and creator settlements are globally verifiable
- universal emission enforcement gateways that bind each concrete response to the
  L146 root, release gate, proof-carrying response, serving gateway, delivered
  source footer, live witness, transparency log, invocation witness, foundation
  runtime route, and client display enforcement before display or settlement
- universal composite RDLLM profiles that bind the provider passport, adoption
  standard, interop kit, L146 root, L147 gateway, provider-family coverage,
  native API bindings, customer source-footer surfaces, telemetry, standards
  mappings, and fail-closed cases into one adopter-facing deployment contract
- universal runtime conformance receipts that bind live provider API routes,
  generation entrypoints, tool/agent actions, source-attribution modes, visible
  footer injection, client display enforcement, OpenTelemetry GenAI export, proof
  downloads, challenge routing, privacy filtering, and settlement meters before
  response display or creator settlement
- universal claim provenance envelopes that bind each displayed claim to
  generation-time source provenance, support relation, evidence region, citation
  identity, locator health, visible footer row, tool or memory trace, payout
  basis, and settlement meter before response display or direct settlement
- universal provider wire protocols that bind L150 claim provenance and L149
  runtime receipts to request headers, response headers, JSON bodies, streams,
  tool-call messages, SDK metadata, proxies, aggregators, batch callbacks,
  webhooks, exported copies, transform receipts, telemetry spans, and settlement
  meters before a provider route can claim grounded display or direct settlement
- universal accountability audit trails that bind provider-wire calls,
  governance approvals, delegated agents, tool and memory events, footer
  rendering, exports, challenges, and settlement meters into one append-only
  hash chain before attribution or direct creator settlement can be trusted
- universal accountability witness quorums that publish L152 audit checkpoints
  to transparency logs, verify inclusion and consistency proofs, monitor for
  split views, and require independent witness cosignatures before reliance or
  settlement
- universal grounded reliance contracts that authorize source footers, user
  confidence labels, procurement claims, regulator exports, and creator
  settlement only after claim support, locators, freshness, warrant labels,
  client rendering, L153 witness roots, and finance reconciliation all verify
- universal reliance correction ledgers that keep those footers and settlement
  claims live after publication by binding corrections, revocations, stale-source
  revalidation, copied-output status links, cache invalidations, client notices,
  regulator exports, and settlement holds or adjustments into append-only status
  rows
- universal foundation adoption kernels that make the same guarantees portable
  across foundation-model APIs: every provider adapter must preserve response
  metadata, source footers, status resolvers, claim-level text attribution,
  telemetry, streaming events, SDK fields, copy/export capsules, challenge
  routes, regulator exports, and settlement meters, or fail closed before display
- universal provider adapter harnesses that replay native provider fixtures from
  sync, streaming, tool, retrieval, batch, webhook, and copied-output modes into
  one normalized RDLLM response contract before display or settlement
- universal provider drift sentinels that continuously replay provider API,
  SDK, model-alias, streaming, gateway, citation-locator, source-footer, and
  settlement-meter canaries, revoking stale routes and holding settlement when
  drift breaks the published response contract
- universal attribution negotiation handshakes that require each client and
  provider route to agree on the exact attribution, source-footer, citation,
  drift-sentinel, telemetry, copy/export, privacy, and settlement contract before
  model invocation
- universal negotiated invocation enforcement that proves every actual SDK,
  gateway, stream, tool, MCP, retrieval, batch, fallback, and cache invocation
  carries the negotiated attribution contract before model execution, display, or
  creator settlement release
- universal certification trust federation that binds attribution, source-footer,
  invocation, and settlement conformance claims to trust anchors, accredited
  certifiers, conformance labs, trust marks, verifiable credentials, transparency
  inclusion, revocation status, and relying-party policy
- universal foundation provider adoption packs that bind the federated trust
  chain to provider-family adapters, public standards exports, runtime
  fail-closed gates, telemetry mappings, source-footer delivery, copied-output
  status links, creator audit routes, regulator exports, and settlement-release
  guards for hosted APIs, cloud gateways, routers, open-weight runtimes, and
  enterprise proxies
- universal industry adoption roots that bind the L162 adoption pack, current
  proof graph, public verifier endpoints, role obligations, creator audit
  paths, regulator exports, copied-output status links, and negative root
  fixtures into one acyclic public reliance root
- universal reference implementation distributions that bind the L163 root to
  signed reproducible SDKs, gateway middleware, MCP adapters, telemetry mappings,
  content-credential templates, trust-mark credentials, SCITT statements,
  settlement adapters, CI workflows, offline verifier containers, procurement
  policies, and SBOM/SLSA provenance
- universal live attribution proofs that bind response footers to source
  identity, claim support, evidence utility, factual confidence,
  knowledge-source classification, attribution-suppression checks, and
  settlement participation before response release or payout
- universal foundation-model release passports that bind named model versions to
  provider identity, model signing or attestation, training transparency,
  copyright/TDM policy, post-training lineage, provider routes, live attribution,
  revocation, and settlement before RDLLM model claims or provider invocations
- universal composite RDLLM contracts that bind model claims, provider
  invocation, response release, source-footer reliance, procurement reliance,
  and creator settlement into one signed verifier decision across all supported
  roles, API surfaces, decision gates, standard bindings, revocation checks, and
  negative fixtures
- universal foundation provider binding matrices that bind OpenAI, Anthropic,
  Google, Meta/Llama, Mistral, Cohere, xAI, DeepSeek, cloud, router,
  local-runtime, enterprise-gateway, RAG, and MCP/agent routes to the composite
  contract through native API, streaming, tool, citation, telemetry, revocation,
  audit, and settlement mappings
- universal provider conformance runner receipts that prove official fixture
  suites were freshly replayed against every bound provider route, with signed
  native transcripts, runner-stage evidence, public result hashes, negative
  canary rejection, and fail-closed gates for source-footer reliance,
  procurement reliance, and creator settlement
- universal production invocation admissions that prove each live provider call
  is admitted against the current conformance receipt, route, model alias,
  tenant scope, telemetry span, source-footer release gate, revocation snapshot,
  and settlement meter before response release, source-footer reliance, tool/MCP
  execution, retrieval reliance, or creator settlement
- universal source-grounded response receipts that prove the final answer binds
  L170 admission to visible source footer rows, claim-source support, citation
  metadata verification, copy/export preservation, and settlement rows before
  user reliance or creator settlement
- universal distribution reliance passports that prove copied, exported,
  embedded, relayed, screenshotted, and downstream-ingested AI outputs preserve
  source footers, source locators, status resolvers, content credentials, reuse
  meters, and settlement carry-forward obligations before third-party reliance
- universal adversarial provenance quorums that prove independent provenance
  signals and negative attack fixtures reject spoofed, stripped, replayed,
  split-viewed, proxied, or poisoned distributed outputs before reliance or
  creator settlement
- universal procurement/regulatory reliance contracts that prove provider
  terms, model-version claims, source-footer duties, machine-readable source
  duties, marketplace listings, enterprise procurement gates, regulator exports,
  creator challenge routes, jurisdiction mappings, and settlement remedies are
  bound to the L173 quorum before provider claims, procurement reliance,
  regulator reliance, or creator settlement
- universal provider onboarding/migration covenants that prove every supported
  foundation provider family, native API surface, SDK shim, gateway, marketplace
  listing, customer migration artifact, rollout gate, rollback path, and negative
  onboarding fixture is bound to the L174 reliance contract before provider
  support or enterprise migration is claimed
- universal model/provider registries that prove every declared hosted, routed,
  private, local, regional, marketplace, or open-weight model route is registered
  with adapter, catalog, lifecycle, source-footer, and settlement metadata before
  it can claim RDLLM support
- universal source-footer enforcement contracts that prove every registered route
  discovers sources, verifies claim support, renders visible and machine-readable
  footer rows, refuses unsupported claims, preserves footers across export
  surfaces, and holds settlement before final answer release
- universal provider catalog coverage contracts that prove every discovered
  provider, marketplace, gateway, private, local, regional, SDK, billing, and
  lifecycle catalog model is normalized, admitted into a registered
  source-footer-enforced route, or explicitly blocked before universal provider
  coverage can be claimed
- universal runtime route binding contracts that prove every actual runtime
  request, response model echo, alias, fallback, stream final event, tool or
  batch callback, telemetry span, source footer, and settlement meter binds to
  an L178 catalog-covered route before release
- universal verified source-footer contracts that prove every visible source row
  binds to live runtime route evidence, source materialization, link health,
  metadata fidelity, relevance, factual support, claim evidence, copy/export
  preservation, and settlement state before source reliance or payout
- universal model capability coverage contracts that prove every declared model
  capability, modality pair, operation surface, and catalog-covered route has a
  fixture-backed runtime binding, verified source-footer-or-abstention behavior,
  settlement-meter binding, and fail-closed negative coverage before model
  invocation, response release, source-footer reliance, or creator settlement
- universal live capability discovery contracts that prove provider capability
  declarations bind to fresh official or attested provider sources, endpoint
  compatibility, lifecycle and region evidence, and L181 route coverage before
  invocation, response release, source-footer reliance, or creator settlement
- universal native source annotation contracts that prove provider-native
  citations, grounding metadata, document citations, streaming citation deltas,
  router annotations, RAG contexts, local manifests, and media source metadata
  normalize into verified RDLLM footer rows before response release,
  source-footer reliance, or creator settlement
- universal claim-evidence footer verification contracts that prove each
  displayed footer source is parsed, materialized, source-suitable,
  intent-aligned, answer-faithful, and factually supportive of the exact
  generated claim before response release, source-footer reliance, or creator
  settlement
- universal provider meter normalization contracts that prove provider-native
  usage, cache, reasoning, tool/search, media, batch, invoice, router, pricing,
  and quota meters normalize into RDLLM settlement meters before response
  release, source-footer reliance, or creator settlement
- universal provider response-state normalization contracts that prove
  provider-native finish, stop, refusal, safety, guardrail, truncation, tool,
  stream-final, and error states normalize into RDLLM release gates before a
  response can be presented as a grounded answer with source-footer reliance or
  creator settlement

The report grades deployments from `RDLLM-L0` through `RDLLM-L186`. The highest level
requires end-to-end agreement across attribution, user-visible footer, claim evidence,
source-access traces, attribution-gap reports, rights decisions, registry decisions,
receipts, transparency proof, escrow, payout conservation, escrow release,
citation-quality scoring, portable credential/provenance exports, and
selective-disclosure receipts, OpenTelemetry-aligned provider trace exchange, and
privacy-preserving royalty statement rollups, creator challenge correction, and a
derivative-lineage report, provenance evaluation report, provider attribution card,
public training-content summary, public assurance bundle, user-facing answer
provenance card, public source verification report, portable response envelope,
provider integration profile, well-known discovery manifest, foundation API
attribution profile, client attribution enforcement receipt, persistent memory
provenance receipt, private reasoning attribution receipt, post-training signal
provenance receipt, attribution bill of materials, creator attribution audit
index, creator attribution audit federation, creator audit federation transparency
report, creator audit transparency monitor, creator audit private watch receipt,
deep-research citation audit, source freshness audit, royalty-abuse audit,
consent revocation propagation audit, evidence-force calibration audit, and counterfactual
influence report, media attribution report, model signal attribution report, and
rights remediation report, semantic text attribution report, and cross-provider
attribution exchange manifest, conformance vector pack, runtime federation
handshake, portable attribution capsule that remains verifiable after copy/paste,
reposting, report export, or metadata handoff, and response release gate that
blocks unsupported answers before display, plus a proof-carrying response that
enforces the gate in the delivered API object, plus a serving gateway report that
proves production API egress used that proof-carrying object, plus a creator
license contract that proves the source-use rights and compensation terms existed
before model use, plus a source confidence report that verifies footer rows,
claim rows, and hallucination taxonomy against public proof artifacts, plus a
citation footer contract that verifies the exact client-rendered source rows,
claim anchors, confidence labels, license status, royalty status, and footer hash,
plus a rendered attribution audit that parses the exact displayed Markdown answer
and verifies inline citations, footer source rows, and claim-evidence spans against
the signed response and grounding proof pack, plus a training-memory provenance
report that detects registered memorized spans in the displayed answer and blocks
hidden memory use before release, plus an evidence-locked generation report that
proves support-bearing answer units were evidence-bound before token emission,
plus an emission evidence enforcement report that proves served and streamed
chunks used those locks, plus a live emission witness report that proves
independent witnesses accepted the preflight gate and final stream chain,
plus a live emission transparency report that proves the witness report and every
witness attestation were included in append-only logs with no split-view roots,
plus an attested attribution runtime report that proves the measured enforcement
runtime and attestor quote bind to that live-transparent output path,
plus a claim-source attribution report that proves every visible claim has a
replayable source footer row or escrow/refusal decision, rejects topical
anti-documents, and requires visual-region commitments for credited visual
evidence, plus causal evidence-utility, parametric memory, style influence,
model-lineage, and black-box model provenance reports that bind source utility,
model-weight memory, licensed creative influence, downstream
training/distillation inheritance, and undisclosed derivative-model challenges to
the same verifiable settlement surface, plus an attribution dispute adjudication
report that turns disputed model/source attribution into a public, appeal-safe
escrow release or freeze decision, plus a post-adjudication settlement adjustment
report that corrects underpayments and overpayments without rewriting executed
payment rows,
plus a residual corpus royalty report that binds model-usage revenue rows,
training-content cohorts, creator-license terms, valuation evidence hashes,
direct-attribution exclusions, creator-level caps, payable-or-escrow conservation,
and creator residual receipts for diffuse licensed training value,
plus a valuation method audit report that binds every residual valuation method
used to method-code hashes, benchmark-suite hashes, known-contributor and
anti-document cases, duplicate guards, calibration rows, stability rows, and
privacy or zero-knowledge proof commitments,
plus a private audit challenge that opens redacted source-access, claim-evidence,
rights, and payout paths under auditor nonce without public disclosure, plus a
transitive attribution report that verifies copied-output reuse, preserves original
source rows, and conserves downstream pass-through settlement, plus a clearinghouse
report that converts provider statements and transitive reports into duplicate-safe
payable, escrow, and held settlement rows, plus a remittance report that converts
cleared obligations into instruction-only payment rows with payout-account hashes
and reconciliation references, plus a payment execution report that matches those
instructions to hash-only processor and escrow settlement records, plus a payment
rail attestation that requires registered processors to sign the matching
settlement batches, plus a creator payout receipt report that makes each creator's
paid, escrowed, or held value verifiable against the attribution, clearinghouse,
remittance, execution, and signed-rail evidence, plus a third-party audit
attestation that proves the
public proof pack can be independently replayed and drift-checked from hashes,
statuses, verifier contracts, and discovery surfaces, plus a revenue allocation
report that proves event-level gross revenue was allocated from conserved source
revenue pools before creator-pool payout, plus a finance ledger attestation that
proves those source pools reconcile to hash-only external finance records without
leaking customer or payment data, plus a proof dependency graph that gives
auditors a cycle-checked replay order for the public proof pack, plus a
publication monitor that proves the public attribution evidence remains
append-only, reproducible, and non-regressed after release, plus a publication
witness report that proves the monitor checkpoint was seen by an independent
quorum and was not split into conflicting histories, plus a trust registry that
proves the signing and witness keys behind the public proof chain are active,
rotated, and not revoked, plus a certification attestation that proves the
certification report hash, level summary, and case-status root were signed by a
certifier key that can be checked through the trust registry, plus a generated-code
attribution report that detects copied or adapted code, applies license checks, pays
compatible owners, and escrows incompatible copied-code value, plus a pre-settlement
claim-verification report that prevents weak, duplicate, or unverified registrations
from receiving direct payout, plus a source-availability report that prevents
stale, unreachable, or content-mismatched citation footers from being treated as
inspectable evidence, plus an evidence-sufficiency report that prevents redundant,
ambiguous, or non-best cited spans from being treated as grounded claim support,
plus a counterevidence report that prevents one-sided grounded answers from hiding
known contradictory source material, plus a generation-context closure report that
binds the final answer's verified claims to material actually present in the traced
generation context before response delivery, plus a source-boundary report that
proves retrieved source packets were evidence-only data rather than instructions,
control metadata, attribution-policy input, or payout-policy input, plus a
source-authenticity report that binds public source rows to trusted origin
evidence, active license terms, archive consensus, synthetic disclosure, and
poisoning/source-farm risk thresholds before direct payment, plus a
calibrated attribution confidence report that binds claim, footer, and payout
attribution to benchmark-backed lower bounds and rejects overstated certainty,
plus an evidence-force calibration report that rejects verified footers and direct
payment when answer wording overstates the cited evidence's relation, modality,
scope, temporal, or numeric warrant,
plus a warranted source footer that displays those warrant labels beside the
visible footer rows,
plus a source-origin lineage report that prevents synthetic wrapper sources from
receiving direct payout unless upstream origin and royalty shares are traceable,
plus a composite foundation adapter report that proves native foundation-model API
responses bind to the same RDLLM envelope, footer, URL-health, and verifier
contract before clients display grounded output,
plus a foundation provider conformance matrix that proves provider families have
hash-only fixtures for attribution-critical positive and fail-closed negative
response modes,
plus a streaming attribution manifest that proves chunk order, chunk hashes, final
gateway output, and footer completion all replay from the public proof response,
plus a conversation attribution ledger that proves inherited source obligations
survive multi-turn conversation state, previous-response IDs, and follow-up
answers, plus an agent-tool attribution ledger that proves each tool observation
supporting a source row or claim reaches the trace, the footer, and the
conversation obligation chain, plus a pinpoint provenance report that rejects
topical anti-documents and requires answer-critical fact support before footer
display or direct payout, plus a citation identity report that verifies public
source identifiers, titles, authors, years, and claim support against authority
records before footer display or direct payout, plus an attribution consensus
report that reconciles source confidence, authenticity, sufficiency,
counterevidence, pinpoint provenance, and citation identity before direct payout.

### Conversation Attribution Continuity

`rdllm-conversation-attribution-ledger/v1` binds a stateful session to ordered turn
rows. Each row records the proof response hash, serving gateway hash, streaming
manifest hash, visible source-row obligation hashes, inherited obligation hashes,
parent turn hashes, and final turn-chain hash. Any dependent turn must propagate
prior source obligations into its current visible source rows. Verification rejects
missing parents, reordered turns, dropped inherited obligations, failed proof,
gateway, or streaming replay, and private prompt or raw-output fields in the
ledger rows.

### Agent-Tool Attribution Trajectories

`rdllm-agent-tool-attribution-ledger/v1` closes the gap between agent traces and
user-visible attribution. It embeds the proof-carrying response, trace exchange,
and conversation attribution ledger, then derives one public row per source-access
tool observation. Each row binds a tool span ID, source-access ID, input
commitment hash, observation hash, visible source label, source obligation hash,
claim indexes, and evidence span hashes.

Verification rejects a ledger if the trace event does not match the proof response,
if any visible source row lacks a tool observation, if any supported claim lacks a
tool-backed support row, if a source obligation does not appear in the
conversation ledger, if the provider has not declared the agent-tool surface, or if
raw prompt, model, or tool-output text appears in public tool rows. This makes
web search, file search, retrieval, function calling, code execution, MCP, and
remote tools auditable without exposing the raw tool payload.

### Pinpoint Provenance and Anti-Document Guard

`rdllm-pinpoint-provenance-report/v1` closes the gap between "a source was
available" and "this source really supports the answer." It binds private prompt,
answer, claim, and candidate-document text to public hashes, ranked support rows,
source footers, and royalty decisions. A candidate can be topically similar and
still be rejected as an anti-document when it lacks answer-critical evidence.

Verification rejects a report if an anti-document is accepted, an accepted claim
lacks a footer row, uncertain claims are not escrowed, the creator pool is not
conserved, the report cannot be replayed from private inputs, or private text leaks
into public rows.

### Citation Identity and Metadata-Swap Guard

`rdllm-citation-identity-report/v1` closes the gap between "the supporting work was
found" and "the public citation shown to the user is real." It binds declared
citations to authority records, checks identifier, title, author, year, and claim
support consistency, emits canonical footer rows for accepted citations, and routes
fabricated or metadata-swapped citations to escrow.

Verification rejects a report if a fabricated citation is accepted, a real
identifier is paired with the wrong title or author set, a citation does not support
the bound claim, canonical footer rows drift, the creator pool is not conserved, the
report cannot be replayed from authority inputs, or private prompt, answer, claim,
source excerpt, or authority-content text leaks into public rows.

### Attribution Consensus Quorum

`rdllm-attribution-consensus-report/v1` closes the gap between individually valid
artifacts and settlement-ready attribution. It requires source confidence, source
authenticity, evidence sufficiency, counterevidence adjudication, pinpoint
provenance, and citation identity to bind to the same event hash. Accepted rows
must pass every required channel; incomplete or conflicting rows route to
`attribution_consensus_escrow`.

Verification rejects a report if event hashes diverge, an accepted row lacks a
required channel, a blocked row receives direct payout, the creator pool is not
conserved, the report cannot be replayed from public artifacts, or private prompt,
response, source, claim, authority, or tool text appears in public rows.

### Independent Verifier Quorum

`rdllm-verifier-quorum-report/v1` closes the remaining provider self-attestation
gap. It binds the L70 attribution consensus report to provider, certification,
and integration artifacts, then requires a configurable quorum of independently
signed replay attestations. If the quorum, independent-organization count, or
signature checks fail, all consensus payout rows are transformed into
`verifier_quorum_escrow` rows while preserving creator-pool conservation.

### Bonded Verifier Accountability

`rdllm-verifier-accountability-report/v1` closes the verifier self-interest gap.
It binds the accepted L71 verifier rows to active trust-registry identities,
matching verifier key hashes, non-revocation state, slashable bond rows, conflict
disclosure hashes, and accountability challenge rows. If any accepted verifier is
unregistered, under-bonded, unslashable, conflicted, revoked, or under a blocking
challenge, all verifier-approved payout rows are transformed into
`bonded_verifier_accountability_escrow` rows while preserving creator-pool
conservation and publishing a slashing-evidence root.

### Receipt Transparency Consistency

`rdllm-receipt-transparency-consistency-report/v1` closes the usage-log
equivocation gap. It binds required attribution receipts to observed transparency
log snapshots, verifies inclusion proofs and append-only prefixes, detects
same-size root forks, and transforms verifier-approved payouts into
`receipt_transparency_consistency_escrow` rows whenever the economic log is not
globally consistent.

### Watchtower Challenge Settlement

`rdllm-watchtower-challenge-settlement-report/v1` closes the enforcement gap
left after usage-log consistency. It requires active independent watchtower
entries in the trust registry, quorum attestations over the L73 subject, and a
clean challenge state. Open or accepted blocking challenges transform
receipt-transparent payouts into `watchtower_challenge_escrow` rows, and accepted
verifier-observation failures produce slashing and bounty commitments.

### Output Provenance Binding

`rdllm-output-provenance-binding-report/v1` closes the copy/export survival gap.
It requires proof-carrying response hashes, serving-gateway output hashes,
attribution-capsule hashes, watchtower-cleared settlement hashes, content
credentials, watermark commitments, fingerprint commitments, and public verifier
paths to agree before an exported answer is considered provenance-bound.

### Post-Release Discovery Publication

`rdllm-post-release-discovery-report/v1` closes the discovery-cycle gap left by
copy/export binding. It lets providers publish output-specific proof artifacts
after response release while preserving a stable base `/.well-known/rdllm.json`.
Verifiers reject reports when the base manifest does not advertise the
post-release surface, the output-binding report cannot be replayed, the proof graph
omits late output artifacts, or the post-release catalog is tampered.

## Third-Party Audit Attestation

The public proof pack should not depend on provider self-attestation. RDLLM
therefore emits `rdllm-third-party-audit-attestation/v1` as a signed, hash-only
external audit artifact over the provider's public evidence surface.

A third-party audit attestation contains:

- auditor identity, verifier identity, audit period, provider/model identifiers,
  minimum input level, and target certification level
- hash rows for the provider card, certification report, integration profile,
  discovery manifest, assurance bundle, response envelope, source-confidence
  report, citation-footer contract, clearinghouse report, remittance report,
  optional payment execution report, revenue allocation report, and finance ledger
  attestation
- readiness checks for independent auditor identity, L44-or-better input
  certification, provider-card binding, integration and discovery readiness,
  public verifier replay, response confidence, footer verification, clearinghouse
  duplicate safety, remittance conservation, optional payment execution replay, and
  private-field absence
- verifier-contract requirements for offline replay and negative controls such as
  stale certification hashes, missing assurance artifacts, response hash drift,
  footer suppression, remittance amount drift, payment execution amount drift,
  revenue allocation drift, and finance ledger drift
- privacy flags proving the attestation embeds no artifact payloads and discloses
  only hashes, statuses, counts, and schema references

The verifier recomputes the attestation from the public artifacts, replays the
public verifier chain where the required inputs are available, and rejects stale
hashes, footer suppression, unverifiable response envelopes, remittance drift,
payment execution drift, revenue allocation drift, finance ledger drift, missing discovery paths,
provider-only audit claims, signature drift, and private field leakage. This is
the layer that turns a provider proof pack into something an external auditor,
marketplace, regulator, collective manager, or enterprise buyer can cite without
trusting the provider's database.

## Revenue Allocation Report

The revenue allocation report closes a different trust gap: the system should not
assume event `gross_revenue` is true just because a provider wrote it into the
ledger. RDLLM therefore emits `rdllm-revenue-allocation-report/v1` before royalty
statement rollup.

A revenue allocation report contains:

- hashed revenue-source rows for subscription pools, advertising pools, API meter
  events, enterprise seats, marketplace orders, or other monetization sources
- an allocation policy such as `ledger_gross_revenue`, `equal_event_split`,
  `api_metered_tokens`, `subscription_usage`, `ad_impression`, or
  `weighted_engagement`
- per-event allocation rows binding event IDs, event hashes, receipt hashes, basis
  weights, source allocations, allocated gross revenue, ledger gross revenue,
  creator-pool rates, expected creator pools, and royalty-share roots
- commitments over the source rows, event allocation rows, receipts, ledger, gross
  revenue total, and creator-pool total
- privacy checks proving raw customer accounts, invoice text, payment methods, and
  raw billing records are absent from the public report

The verifier recomputes the report from the ledger, revenue-source declaration, and
optional receipts. It rejects unsupported allocation modes, non-conserved source
revenue, event rows whose allocated gross revenue does not match the ledger, creator
pool drift, missing receipt bindings, duplicate events, private billing fields, hash
drift, and signature drift. This gives creators and auditors a way to inspect the
money entering the attribution pipeline before clearinghouse and remittance steps.

## Finance Ledger Attestation

The finance ledger attestation closes the finance-source trust gap: the revenue
allocation report proves a declared pool was conserved into event economics, but
the pool itself still needs to be tied to billing, invoice, ad-server, API-meter,
enterprise-contract, marketplace-order, or other finance-system evidence. RDLLM
therefore emits `rdllm-finance-ledger-attestation/v1` after the revenue allocation
report.

A finance ledger attestation contains:

- hash-only finance record rows with source IDs, record types, external record
  hashes, gross amounts, currencies, event IDs, allocation-policy references, and
  row hashes
- revenue-source rollups that bind each source pool to the finance rows that back
  it, including record counts, source totals, allocation totals, amount-delta
  checks, currency checks, and rollup hashes
- commitments over finance record rows, source rollups, the finance total,
  revenue-allocation total, revenue-allocation report hash, source IDs, and schema
  version
- privacy checks proving customer IDs, customer emails, invoice text, raw finance
  records, payment methods, bank accounts, tax IDs, prompts, outputs, source text,
  and evidence text are absent from the public artifact

The verifier recomputes the attestation from the private finance export and the
public revenue allocation report. It rejects missing external record hashes,
duplicate finance rows, finance rows that map to no allocation source, allocation
sources with no finance rows, source-total drift, total gross drift, currency
drift, private-field leakage, stale attestation hashes, and signature drift. This
lets creators verify that payout economics flow from real revenue evidence while
letting providers keep regulated customer and payment records private.

## Proof Dependency Graph

The proof dependency graph closes the replay-order trust gap: a provider can
publish many correct artifacts, but an external auditor still needs to know which
artifacts must verify before downstream artifacts can rely on them. RDLLM therefore
emits `rdllm-proof-dependency-graph/v1` as a hash-only replay DAG over the public
proof pack.

A proof dependency graph contains:

- hash-only artifact rows with names, artifact types, declared hashes, payload
  hashes, hash-reproducibility status, and node hashes
- dependency rows that distinguish hard `replay_dependency` edges from
  `publication_commitment` edges such as Merkle bundle inclusion
- a deterministic `replay_order` and step-by-step verifier plan for offline audit
- commitments over artifact rows, dependency rows, replay order, replay steps, and
  schema version
- privacy checks proving artifact payloads, prompts, answers, source text,
  evidence text, customer records, and payment text are absent from the graph

The verifier recomputes the graph from the artifact payloads and declared edge
policy. It rejects unknown dependencies, self-dependencies, replay cycles, replay
orders that omit artifacts, stale graph hashes, non-reproducible artifact hashes,
private-field leakage, and signature drift. Publication commitments do not define
replay order; this lets assurance bundles and discovery surfaces publish hashes
without creating artificial cycles in the verifier plan.
Publication edges are derived from the assurance bundle's actual artifact entries,
not from every artifact named in the graph, so the graph cannot overclaim Merkle
inclusion for runtime artifacts that are advertised elsewhere.

## Publication Monitor

The publication monitor closes the proof-surface drift gap: a provider can pass an
audit once and later change its provider card, certification report, response
envelope, assurance bundle, or proof dependency graph. RDLLM therefore emits
`rdllm-publication-monitor/v1` as a signed append-only checkpoint history over the
public proof surface.

A publication monitor contains:

- hash-only artifact rows with declared hashes, payload hashes, entry hashes, and
  hash-reproducibility status
- a Merkle snapshot root and inclusion proofs for the current public artifact set
- an append-only checkpoint chain with previous checkpoint hashes
- a diff from the previous snapshot, including added, removed, changed, and
  unchanged artifacts
- regression checks for required artifact removal, certification-level downgrade,
  non-reproducible hashes, checkpoint-chain tampering, and private-field leakage

The verifier recomputes the current snapshot from public artifacts and, for append
mode, checks that the prior checkpoint history is preserved exactly. This makes
RDLLM attribution monitorable after publication: users can see grounded response
footers, while auditors can prove the public evidence behind those footers has not
silently regressed.

## Publication Witness

A monitor still leaves one failure mode: a provider could try to show different
monitor histories to different audiences. RDLLM therefore emits
`rdllm-publication-witness/v1` as a signed anti-equivocation report over the latest
publication-monitor checkpoints.

A publication witness report contains:

- checkpoint subjects with issuer, checkpoint index, checkpoint hash, snapshot
  root, artifact count, and monitor hash
- independent witness attestations over those checkpoint subjects
- a quorum policy with observed witness count, required quorum, and quorum status
- split-view detection grouped by issuer and checkpoint index
- checks for monitor self-consistency, subject completeness, witness signature
  validity, quorum satisfaction, absence of equivocation, and private-field leakage
- only hashes and metadata, not monitor artifact payloads, prompts, answers,
  evidence text, source text, finance records, or payout accounts

The verifier recomputes the monitor subjects, witness signatures, attestation
hashes, quorum result, split-view result, report hash, and provider signature. This
makes public source footers and royalty proofs harder to fork: a customer can
accept a response only when the cited source proof chain is not merely published,
but also witnessed by an independent quorum.

## Trust Registry

The witness layer still assumes verifiers know which provider, auditor, and witness
keys are valid. RDLLM therefore emits `rdllm-trust-registry/v1` as a signed public
trust-root registry for attribution proof artifacts.

A trust registry contains:

- principal rows for provider, auditor, and witness identities with key IDs, key
  hashes, roles, status, allowed signature algorithms, and entry hashes
- revoked-key rows and rotation rows that link old key hashes to active new key
  hashes without exposing raw signing secrets or private key material
- artifact bindings for signed public proof artifacts, including issuer, declared
  hash, payload hash, signature status, registered signer status, signing key ID,
  and revoked-key-use status
- witness bindings for publication-witness attestations, including monitor hash,
  checkpoint hash, witness key hash, attestation hash validity, signature validity,
  and revocation status
- commitments over principal, revoked-key, rotation, artifact-binding, and
  witness-binding roots
- privacy checks proving the registry uses only key hashes and artifact hashes

The verifier recomputes artifact signatures, witness signatures, key hashes,
rotation links, revoked-key use, registry hash, and provider signature. This maps
the reference HMAC proof model to production trust-root patterns such as JWKS key
sets, DID verification methods, and TUF-distributed trust roots, while keeping the
public attribution footer and payout proof independent of provider-only key claims.

## Certification Attestation

The trust registry binds signatures on public proof artifacts, but a certification
report is still weak if customers cannot tell who attested it or whether the
report hash was signed under a non-revoked certifier key. RDLLM therefore emits
`rdllm-certification-attestation/v1` as the certification-authority layer for the
public proof pack.

A certification attestation contains:

- certifier identity, issuer, creation time, optional validity window, and target
  provider
- the certification report hash, certification version, suite, issued time,
  implementation hash, levels root, case-status root, and case-status row count
- a compact certification summary with status, highest level, case count, passed
  count, failed count, and score
- checks for report-hash reproducibility, all-cases-passed status, minimum L51
  attested level, case-count consistency, empty failed-case root, non-embedded case
  artifacts, and schema declaration
- privacy flags proving the report payload, case artifacts, prompt text, source
  text, evidence text, customer data, and payment text are not embedded

The verifier recomputes the report hash, levels root, case-status root,
attestation hash, and certifier signature. The trust registry can then bind that
attestation artifact to a certifier key hash, turning a provider's certification
claim into a signed, replayable public proof.

## Grounding Quality Report

The grounding quality report is inspired by recent citation-evaluation work that
separates link/source availability from relevance and factual support. RDLLM uses
the same separation locally:

- `source_accessibility`: every visible source has a URI, hash, quote, and license
- `citation_integrity`: footer labels match source references, claim labels point to
  real sources, and evidence span hashes appear in the footer
- `evidence_relevance`: claim text overlaps its selected evidence span
- `fact_support`: supported claims have source labels, chunks, evidence text,
  reproducible span hashes, footer-visible span prefixes, and character offsets
- `policy_alignment`: allow/deny decisions agree with the event's policy status
- `payout_alignment`: paid chunks are visible sources, and escrow is used when value
  is unattributed, rights-blocked, or registry-disputed

The verdict can be `verified`, `warning`, `failed`, `unattributed`, or
`blocked_by_policy`, or `blocked_by_registry`. It is included in the event hash and
attribution receipt, so it is not a cosmetic score that can be changed after the
answer is delivered.

## Attribution Gap Report

The attribution-gap report answers the question that ordinary citation footers leave
open: did the model or retrieval path use anything that the user cannot see or that
the creator was not paid for?

Each event records `source_accesses` for retrieval and text-match paths. Every access
has a stable ID, access type, intended use, owner, work ID, chunk ID, source URI,
content hash, score, rank, policy decision, registry decision, and matched-text hash
when applicable. The `rdllm-attribution-gap/v1` report compares four sets:

- accessed sources
- visible source references in the footer and receipt
- paid non-escrow royalty shares
- policy-withheld or registry-withheld sources assigned to escrow

The report verdict is:

- `closed` when every allowed accessed source is visible and paid
- `escrowed` when sources are withheld only because policy or registry status blocks
  attribution, and value is held in the matching escrow account
- `unattributed` when no owner can be traced and the pool is held in unattributed
  escrow
- `open_gap` when a source is consumed without credit, cited without an access trace,
  paid while hidden from the footer, or withheld without a matching escrow reason

This converts attribution from a best-effort citation UX into a hard audit invariant:
the access trace, response footer, payout ledger, and escrow ledger must reconcile.

## User-Facing Source Footer

The system renders sources as part of the answer:

```text
Sources
[S1] Work Title - Creator Name; chunk=work:c1; uri=registered://...; support=0.625; text_match=0.900; hash=e94efa6d9bb3.
    Evidence: span_hashes=abc123def456. Short quote from the registered source.
Grounding: 2/2 claims supported; status=grounded.
Claim Evidence
[C1] S1; span=abc123def456; chars=0-88.
```

This footer serves three purposes:

- user trust: users can see why the answer is grounded
- creator attribution: owners are visible, not only paid invisibly
- auditability: source IDs and hashes connect the answer to the ledger
- evidence continuity: claim-level span hashes prove the exact supporting passage,
  not only the document or chunk

If the output matches a registered work that is not licensed for the attempted use,
the source quote is withheld from the visible footer, the event status becomes
`rights_blocked`, and the footer states that rights-conflict escrow was used.

If the output matches a registered work that is under duplicate ownership dispute,
the source quote is also withheld, the event status becomes `registry_disputed`, and
the footer states that registry-dispute escrow was used. Users still see that the
answer was not silently paid to a questionable owner.

## Five Implementation Paths

### Path 1: RAG-Time Royalties

This is the most provable path. The LLM is required to answer from licensed,
registered, retrieved context. The retrieval system knows which chunks were made
available to the model, and the output checker knows which chunks were cited or
lexically supported.

Best for:

- news and publishing
- legal and professional databases
- education
- music/film metadata and commentary
- enterprise knowledge bases
- creator marketplaces

Proof strength: high, because the input-output chain is recorded at generation time.

Policy rule: retrieval is not enough. A chunk may be permitted for indexing or
retrieval but prohibited for generation, display, or external attribution. The
prototype enforces that distinction before payout and receipt creation.

### Path 2: Text/Output Royalties

This path attributes generated text itself. A system can submit any output string,
whether produced by this prototype or by an external AI application. The matcher
compares the output against registered source chunks using:

- longest common token sequence
- n-gram containment
- exact or near-verbatim phrase overlap
- source content hashes

When a text match is strong, the owner can be paid even if the matched source was
not retrieved by the current prompt.

Proof strength: high for copied or near-copied text, medium for loose paraphrase,
low for style-only resemblance.

### Path 3: Citation Royalties

If an output cites `[chunk_id]` or `[work_id]`, the citation becomes an attribution
signal and is recorded in the payout basis. This supports systems that use explicit
source-aware generation or human-authored citations.

Proof strength: high when citation IDs are controlled by the attribution layer.

### Path 4: Training-Data Royalties

For base-model or fine-tuning data, direct per-output causality is much harder.
The practical path is periodic valuation. The prototype computes exact Shapley-style
values for small corpora and falls back to leave-one-out valuation for larger ones:

- cluster registered works into data cohorts
- run benchmark tasks or holdout evaluations
- estimate value with Data Shapley, leave-one-out, TracIn, influence functions, or
  other data attribution methods
- convert cohort value into `value_prior_i`
- distribute a training royalty pool periodically

Proof strength: medium. It is statistically defensible but not as direct as RAG.

### Path 5: Registry-Gated Claims, Escrow, and Disputes

Creators or automated matchers can flag outputs that are highly similar to registered
works. Claims can trigger:

- duplicate-registration detection before settlement
- payout redirection
- payout splitting
- temporary escrow
- output takedown
- appeal or human review
- registry-dispute escrow when multiple claimants register the same or near-same work
- post-dispute release to the resolved owner or split beneficiaries
- rights-conflict escrow when a traced source was not licensed for the attempted use

Proof strength: high for near-verbatim overlap, lower for style-only claims.

## Governance Requirements

A credible mechanism needs more than code:

- creator consent and opt-in registration
- license templates for training, retrieval, generation, and display
- ODRL-style permission, prohibition, and duty metadata
- Croissant/SPDX-compatible training and dataset manifests
- duplicate work detection
- dispute windows before settlement
- appeal process for contested claims
- fraud penalties for false registration or spam works
- minimum payout thresholds
- public transparency reports
- private creator dashboards
- regulator or third-party audit exports

## Why This Is Complete Enough To Prove

The included prototype proves the core invariant: every monetized AI usage event can
produce a replayable chain from registered source material, generated text, text
matches, claim evidence span hashes, rights decisions, training priors, attribution
weights, payout, and public disclosure commitments. When no owner can be traced, the
creator pool is assigned to an
unattributed escrow account. When an owner can be traced but the attempted use is not
licensed, the pool is assigned to rights-conflict escrow. When an owner claim itself
is contested by duplicate registration, the pool is assigned to registry-dispute
escrow. When the dispute is resolved, a separate settlement report releases the
escrow while preserving the original blocked event. This creates the accounting
substrate on which licensing, governance, and legal processes can operate.
