# Recent Research Notes: Grounded Attribution for AI Outputs

This note captures recent primary sources that directly shaped the current mechanism.
The conclusion is clear: payout attribution and user-facing source attribution should
share the same evidence trail.

## 2026-07 GitHub, SEO, and GEO Documentation Update

The onboarding surface now treats documentation as part of the product boundary.
Google's Search Central guidance frames SEO as making content easier for search
engines to crawl, index, and understand while still serving users first. The GEO
paper frames generative engines as systems that synthesize answers from multiple
sources and need citation precision and recall. Stack Overflow's 2025 Developer
Survey also shows why examples need to meet builders in common implementation
languages rather than only in the Python library path. 2026 language-speaker
rankings provide the basis for concise global quickstarts.

The repository therefore adds a GitHub start guide, live runtime use cases,
five implementation-language API examples, a public explanation ladder, and
localized quickstarts plus explainers in 15 languages. The new
`github_docs_readiness_audit` gate checks that these surfaces keep source
footers, Claim Evidence, support metrics, payout fields, and
source-disagreement status visible. This is not a ranking guarantee; it is a
maintenance rule that keeps the public docs crawlable, citeable, and useful to a
developer who has never seen RDLLM before.

References: https://developers.google.com/search/docs/fundamentals/seo-starter-guide,
https://arxiv.org/abs/2311.09735,
https://survey.stackoverflow.co/2025/technology,
and https://en.wikipedia.org/wiki/List_of_languages_by_total_number_of_speakers.

## 2026-07 Production-Readiness Update

The production target is now an open-source royalty platform that can be operated
by individuals, companies, institutions, governments, model providers, and public
sector deployments. The mechanism therefore adds a separate production-readiness
gate for live operation. This gate is distinct from the artifact ship gate: it
requires an operator profile, tenancy controls, runtime admission controls,
source-footer enforcement, rights governance, dispute escrow, payment or
instruction-only settlement controls, incident response, backup testing,
public-sector controls, and public proof surfaces.

The controls are anchored to NIST AI RMF GenAI Profile, NIST SSDF, OWASP Top 10
for LLM Applications 2025, and SLSA because RDLLM production readiness is not
only a model-quality claim. It is an operational claim about secure software,
AI-risk controls, source-grounding integrity, supply-chain provenance, privacy,
and auditable settlement.

## 2026-07 Runtime Display-Surface Update

Recent citation-failure work pushes the runtime boundary beyond "there is a
footer object somewhere in the JSON." `Cited but Not Verified` separates link
validity, relevance, and factual support; `Detecting and Correcting Reference
Hallucinations in Commercial LLMs and Deep Research Agents` shows that
source-looking URLs can be fabricated or stale even in search/deep-research
systems; `CiteCheck` separates real citations from metadata drift and fabricated
references; `CiteGuard` treats citation validation as retrieval-grounded
attribution alignment; and `Correctness is not Faithfulness in RAG
Attributions` shows why post-rationalized citations can look correct while not
reflecting model reliance.

The production rule is therefore that a response is not ready for display unless
the client-renderable answer surface is bound to the event hash and source-footer
hash. The service response now carries `display.rendered_text`, a
`display_hash`, and an `answer_plus_verified_source_footer` render policy.
`rdllm-service-response-verify` recomputes the display surface from the raw
answer and verified footer rows, then fails if the rendered answer/footer surface
is missing, modified, or detached from the summary hash. This keeps user trust
anchored to the exact answer the client can render, not to a hidden payout ledger
or decorative citation list.

## 2026-07 Inline Citation Marker Gate Update

Recent source-attribution results make one additional production rule necessary:
the answer text cannot contain citation-shaped markers that fail to resolve to
the verified footer. `Cited but Not Verified` shows that link validity and
topical relevance can mask much lower factual support, FACTUM treats citation
hallucination as distinct from generic RAG hallucination, SourceCheckup reports
large unsupported-statement rates even when answers cite sources, and
sub-sentence citation work argues that users need concise, sufficient evidence
anchors rather than broad citation spans.

The service therefore now treats unresolved inline markers such as `[2]`,
`[Source: 3]`, or `[S9]` as display-blocking audit errors unless they match a
verified source-footer source label or supported claim label. Numeric markers
resolve as source aliases, so `[1]` and `[Source: 1]` are accepted only when
verified source row `S1` exists; numeric groups and ranges must fully resolve,
while four-digit bracketed years are ignored as non-citation text. The response
verifier publishes
`answer_citation_marker_count`, `resolved_answer_citation_marker_count`,
`citation_marker_status`, and detected/resolved/unresolved marker lists inside
`source_grounding_acceptance`, so operators can distinguish a grounded answer
with no inline markers from one that contains misleading citation-shaped text.

References: https://arxiv.org/abs/2605.06635,
https://arxiv.org/abs/2601.05866,
https://www.nature.com/articles/s41467-025-58551-6,
and https://arxiv.org/abs/2509.20859.

## 2026-07 Answer-Link Source Binding Update

New deep-research citation papers add a display gap that bracket-marker parsing
does not cover: generated answers can include Markdown links or bare URLs that
look like source citations while bypassing the verified footer. `Cited but Not
Verified` evaluates inline citations in Markdown reports by parsing the
generated report, retrieving cited content, and separating link accessibility,
topical relevance, and factual support. `ProvenAI` similarly separates answer
correctness, citation fidelity, and document influence, showing that clean
surface citation audits can coexist with weak influence from cited sources.
`How Do LLMs Cite?` reinforces the product risk: inline citations can create a
false sense of security when citation behavior is not proof of source use.

The service therefore now treats answer-link URIs as a production display gate.
Any `scheme://...` URI in the generated answer, including Markdown links, must
match a verified footer `source_uri`; otherwise attribution returns a blocked
response and `rdllm-service-response-verify` fails ready responses. The verifier
publishes `answer_link_uris`, `resolved_answer_link_uris`,
`unresolved_answer_link_uris`, URI counts, and `answer_link_status` inside
`source_grounding_acceptance`. This does not claim the linked page is factually
sufficient by itself; it prevents generated answers from introducing foreign
source-looking locators outside the auditable footer.

References: https://arxiv.org/abs/2605.06635,
https://arxiv.org/abs/2606.26449, and https://arxiv.org/abs/2606.28358.

## 2026-07 Answer-Claim Coverage Update

Recent claim-level verification work shows why valid source rows are not enough:
the displayed answer can contain extra factual units that never receive a
claim-evidence row. PaperTrail decomposes LLM answers and source documents into
discrete claims and evidence to reveal unsupported assertions and omissions.
MedRAGChecker similarly treats generated biomedical answers as atomic claims and
aggregates claim decisions into answer-level diagnostics. The Google AI
Overviews measurement study decomposed generated responses into 98,020 atomic
claims and found unsupported claims even when cited pages were high quality,
showing that source quality and claim fidelity are separate dimensions.

The service verifier now exposes answer-claim coverage inside
`source_grounding_acceptance`. It recomputes answer claim units from
`event.answer_text`, compares their hashes with footer `claim_rows`, and reports
`answer_claim_unit_count`, `answer_claim_row_coverage_count`,
`uncovered_answer_claim_hashes`, `extra_claim_row_hashes`, and
`answer_claim_coverage_status`. A ready response fails verification if answer
text claims and footer claim rows do not match exactly. This is a display
integrity gate: it prevents rehashed responses from adding unsupported answer
text outside the footer; the existing claim-evidence and support-score gates
still decide whether each covered claim is strongly supported.

References: https://arxiv.org/abs/2602.21045,
https://arxiv.org/abs/2601.06519,
and https://arxiv.org/abs/2605.14021.

## 2026-07 Evidence-Force Calibration Update

Recent cited-RAG evaluation work shows that claim coverage is still too weak
when a source is merely related to a claim. `Relevant Is Not Warranted` frames
this as citation laundering: the evidence may be real and relevant while failing
to warrant the exact force of the attached wording. Its FORCEBENCH stress test
uses five localized force axes: relation, modality, scope, temporal validity,
and numeric specificity. `Know Before You Fetch` also argues for calibrated
interfaces that make retrieval and abstention decisions explicit rather than
treating a raw score as a universal confidence signal.

The service footer therefore now renders claim-level warrant metadata. Each
Claim Evidence row includes `claim_preview`, `claim_warrant_profile`,
`claim_force_flags`, `evidence_force_flags`, `warrant_mismatch_flags`, and
`warrant_strength_status`. The response verifier recomputes those fields from
the claim and evidence text, fails grounded display when a supported claim's
evidence does not carry the same relation/modality/scope/temporal/numeric force,
and exposes `claim_warrant_strength_status` inside
`source_grounding_acceptance`. The public source-footer verifier enforces the
same gate for copied/exported footer artifacts. This moves RDLLM from "there is
a related evidence span" to "the evidence visibly warrants the strength of the
displayed claim."

References: https://arxiv.org/abs/2605.28044,
https://arxiv.org/abs/2606.29959,
and https://arxiv.org/abs/2605.06635.

## 2026-07 Visible Source-Disagreement Update

Recent conflict-aware RAG work adds a transparency requirement beyond source
support: systems should not assume retrieved or visible sources agree with each
other. `ConflictRAG` explicitly detects, classifies, and resolves knowledge
conflicts before answer generation. `ArbGraph` separates evidence arbitration
from generation by building support/contradiction relations over atomic claims.
`Contradiction to Consensus` shows why single-source verification is
insufficient: claim verification should retrieve both original and negated
perspectives and expose source-level disagreement.

The service footer now renders conservative source-disagreement metadata in
Claim Evidence rows. Each supported claim carries
`source_disagreement_profile`, `agreement_source_labels`,
`disagreement_source_labels`, and `source_disagreement_status`. The verifier
recomputes those fields from the visible source rows and fails grounded display
when a high-overlap visible source has opposite negation polarity for the claim.
The public source-footer verifier enforces the same gate for copied/exported
footers. This does not claim complete semantic conflict resolution; it prevents
the product from presenting a claim as cleanly grounded while a visible source
plainly says the opposite.

References: https://arxiv.org/abs/2605.17301,
https://arxiv.org/abs/2604.18362,
and https://arxiv.org/abs/2602.18693.

## 2026-07 Model-Reliance Claim Discipline Update

Recent attribution and explanation papers add a separate trust risk: answer text
can imply that the model internally used, reasoned over, or was influenced by a
source even when RDLLM has only observable source-support and allocation
evidence. `How Do LLMs Cite?` shows that citation behavior can diverge from the
model's internal computational pathway. `ProvenAI` separates citation fidelity
from per-document influence and gives examples where cited and influential
evidence diverge. `Evaluating the False Trust Engendered by LLM Explanations`
shows that reasoning traces and post-hoc explanations can persuade users without
being faithful provenance.

The service now blocks model-internal reliance claims on the public answer
surface. Phrases such as `I used`, `my reasoning`, or `sources shaped the
answer` fail display unless they are removed from the answer and represented
instead as observable footer support/allocation fields or as a separate,
verifiable model-signal artifact. `source_grounding_acceptance` publishes
`model_reliance_claim_markers`, `model_reliance_claim_marker_count`, and
`model_reliance_claim_status`, so operators can distinguish "this claim is
supported by a footer row" from the stronger and usually unverifiable statement
"the model internally relied on this source."

References: https://arxiv.org/abs/2606.28358,
https://arxiv.org/abs/2606.26449,
and https://arxiv.org/abs/2605.10930.

## 2026-07 Source-Usage Transparency Update

The latest papers point to a second display problem: even when the footer source
is real and claim-support verified, users still need to know what role the source
played in the answer. `Explicit Evidence Grounding via Structured Inline
Citation Generation` reports that document-level citation is easier than precise
evidence-span grounding; `How Do LLMs Cite?` warns that inline citations can
create a false sense of security because citation behavior may not reflect the
internal computation path; VERICITE shows that sentence-level citation support
can remain low even with retrieved medical abstracts; and `What's a Credit
Worth?` argues that noisy attribution signals materially change whether royalty
or fixed-fee compensation is welfare-optimal. `A Human-Centric Framework for Data
Attribution in Large Language Models` also frames attribution as a negotiated
stakeholder contract rather than a single universal score.

The runtime now renders source-usage metrics directly in service footers. Each
visible source row includes `support`, `text_match`, `weight`, and `payout`,
alongside source identity, verification handle, claim count, confidence,
selection rationale, settlement state, and content hash. These fields are
recomputed by both the saved response verifier and the public source-footer
verifier, so a copied or exported answer cannot silently replace the user-facing
usage explanation. `source_grounding_acceptance` now also reports
`source_usage_metric_names`, `source_usage_metric_row_count`, and
`source_usage_metric_status`, failing grounded display when a visible source row
does not expose the required usage/allocation metrics. The same verifier now
publishes `claim_evidence_row_count` and `claim_evidence_status`; every
supported claim must expose a visible Claim Evidence row whose claim hash,
support score, evidence span hash, character offsets, and evidence preview
recompute from the footer payload. That closes the gap between source-level
allocation and sentence- or claim-level factual support. RDLLM still
distinguishes observable attribution and settlement allocation from hidden
model-internal reliance; internal usage should only be claimed when provider
model-signal telemetry is separately verified.

References: https://arxiv.org/abs/2606.07130,
https://arxiv.org/abs/2606.28358,
https://aclanthology.org/2026.bionlp-1.62.pdf,
https://arxiv.org/abs/2607.00641,
and https://arxiv.org/abs/2602.10995.

## 2026-07 Source-Usage Metric Provenance Update

The latest attribution and verification papers add a sharper constraint:
showing a source-usage number is not enough unless the response also says which
metric profile produced that number and what the number is allowed to mean.
`Do LLM Attribution Metrics Transfer?` shows that attribution metrics do not
reliably transfer across datasets or constructs, so a product should not present
`support` or `text_match` as universal truth without exposing the metric method
and validation scope. `LLM-as-a-Verifier` treats verifier design choices such as
criteria decomposition, score granularity, and repeated scoring as part of the
calibration surface. `ProvenAI` separates answer correctness, citation fidelity,
and document influence, reinforcing that a clean source row is not proof of
hidden model-internal reliance.

The service footer now renders metric provenance beside every source-usage
number. Each visible source row carries `usage_metric_profile`,
`usage_metric_scope`, `support_metric_method`, `text_match_metric_method`,
`weight_metric_method`, and `payout_metric_method`, all hash-bound into the row
and visible in `source_footer.rendered_text`. The response verifier publishes
`source_usage_metric_provenance_count` and
`source_usage_metric_provenance_status`, failing grounded display unless every
visible source row exposes the expected profile, scope, and methods. The public
source-footer verifier enforces the same gate for copied/exported footer
artifacts. This keeps attribution auditable without implying that observable
support/allocation metrics reveal the model's private computational reliance.

References: https://arxiv.org/abs/2606.23915,
https://arxiv.org/abs/2607.05391,
and https://arxiv.org/abs/2606.26449.

## 2026-07 Attribution-Gap Closure Update

Recent LLM-search attribution work separates source use from source credit. `The
attribution crisis in LLM search results` defines the attribution gap as relevant
content consumed by a search-enabled LLM minus sources credited in the output,
and reports that deployed systems can cite fewer sources than they consume or
emit citations that do not appear in the disclosed search trace. `Cited but Not
Verified` adds the companion citation-quality problem: source links may resolve
and look relevant while factual support remains much lower. `Citation Grounding`
and `CiteCheck` show the same pattern in domain-specific settings by separating
existence, relevance, metadata fidelity, and temporal validity from generic
fluency.

The verifier now exposes attribution-gap closure as its own production display
dimension. `source_grounding_acceptance` publishes `attribution_gap_status`,
`attribution_gap_verdict`, accessed and credited source counts, and failure
counters for consumed-without-credit, cited-without-access, and paid-hidden
sources. Grounded display fails unless the attribution-gap verdict is `closed`
and those failure counters are zero. This keeps payout attribution, source
footer attribution, and source-access telemetry aligned before a ready response
can imply that its sourcing is complete.

References: https://www.cambridge.org/core/journals/data-and-policy/article/attribution-crisis-in-llm-search-results-estimating-ecosystem-exploitation/170DD0B88E5F5AEA8F69F2E9AF1328E3,
https://arxiv.org/abs/2605.06635,
https://arxiv.org/abs/2606.00898,
and https://arxiv.org/abs/2605.27700.

## 2026-07 Source-Identity Binding Update

Recent citation-hallucination papers make source identity a separate runtime
failure mode. `CiteCheck` distinguishes exact citation matches from minor
metadata corruption and major fabricated references, showing that a plausible
reference must be grounded against external source metadata rather than trusted
from its surface form. `Phantom References` uses a stricter identity-level
definition of hallucinated citations: the referenced work must exist with
compatible authorship. `Detecting and Correcting Reference Hallucinations`
similarly treats URL validity as measurable and correctable, while `Cited but Not
Verified` separates link accessibility, topical relevance, and factual support.

The service response verifier now binds every visible source row back to the
event's source-reference metadata. `source_grounding_acceptance` publishes
`source_identity_count` and `source_identity_status`; grounded display fails if a
footer row's title, creator, work ID, chunk ID, URI, license, content hash,
support/allocation metrics, evidence preview, or evidence span hashes diverge
from the event source reference it claims to expose. This blocks a
self-consistently rehashed footer from swapping a displayed URI or creator while
leaving the private event trace unchanged.

References: https://arxiv.org/abs/2605.27700,
https://arxiv.org/abs/2607.00738,
https://arxiv.org/abs/2604.03173,
and https://arxiv.org/abs/2605.06635.

## 2026-07 Temporal Grounding Disclosure Update

Recent temporal-RAG and public-information work adds another display failure
class: a source can be real, correctly identified, and relevant while still being
too stale for a current, latest, recent, or as-of claim. `Freshness and the
Limits of Heuristic Trend Detection in Temporal RAG` shows that semantic
similarity alone ignores time and can surface stale evidence for recency-sensitive
queries. `Citation Grounding` includes citation temporality as a separate
dimension from existence and relevance. `Curated retrieval versus open web
search in public AI information services` frames currency and source
trustworthiness as information-quality dimensions that remain invisible unless
measured. `When Benchmarks Age` shows the same temporal-misalignment problem in
factuality evaluation: static evidence can become wrong as the world changes.

The service verifier now exposes `temporal_claim_markers`,
`temporal_claim_marker_count`, `source_temporal_metadata_count`, and
`temporal_grounding_status`. Static answers pass without requiring temporal
metadata. If the rendered answer uses temporal wording such as `current`,
`latest`, `recent`, `today`, `now`, or `as of`, grounded display fails unless
every visible source row carries temporal freshness metadata. This does not
replace the full `rdllm-source-freshness-audit/v1` artifact; it prevents the
runtime response from implying freshness when the footer has no timestamped
source basis to verify.

References: https://arxiv.org/abs/2509.19376,
https://arxiv.org/abs/2606.00898,
https://arxiv.org/abs/2607.05217,
and https://arxiv.org/abs/2510.07238.

## 2026-07 Claim-Source Closure Update

Recent source-aware verification work adds a stricter failure class than
unsupported citation: a claim can be supported somewhere while being attributed
to the wrong visible source. `ProvenanceGuard` calls this cross-source
conflation and evaluates source-aware factuality with per-claim source IDs,
source-specific evidence routing, and attribution-swap probes. `Citation-Closure
Retrieval and Per-Rule Attribution` makes a related point for regulated QA:
systems need explicit claim-to-source closure rather than flattened, post-hoc
source lists. `Cited but Not Verified` reinforces the same runtime rule by
separating source accessibility, relevance, and factual support.

The service verifier therefore now treats claim-source closure as a production
display gate. `source_grounding_acceptance` publishes
`claim_source_closure_count` and `claim_source_closure_status`; every supported
claim must bind to the visible source row whose label, work ID, and chunk ID
match the claim row. A self-consistently rehashed footer that points a supported
claim at a different work or chunk now fails before display, even if the evidence
span itself remains syntactically valid.

References: https://arxiv.org/abs/2606.18037,
https://arxiv.org/abs/2605.29742, and https://arxiv.org/abs/2605.06635.

## 2026-07 Source-Locator Integrity Update

Recent citation-reliability work separates source existence and accessibility
from claim support. `Cited but Not Verified` evaluates source attribution across
Link Works, Relevant Content, and Fact Check because factual support can remain
weak even when links resolve. `Detecting and Correcting Reference Hallucinations
in Commercial LLMs and Deep Research Agents` finds that retrieval-enabled and
deep-research systems still emit hallucinated or non-resolving URLs, and shows
that URL health is measurable and correctable. `CiteCheck` makes a similar point
for scholarly citations: verifying that the referenced work exists and is
correctly specified complements claim-level verification.

The service verifier now treats visible source locators as their own production
display dimension. `source_grounding_acceptance` publishes
`source_locator_count` and `source_locator_status`; every visible source row must
render its `uri`, deterministic `verify` handle, and content-hash prefix in the
footer. This keeps a client from showing fact-support and payout metrics while
hiding the locator information a user or auditor needs to check the source.

References: https://arxiv.org/abs/2605.06635,
https://arxiv.org/abs/2604.03173, and https://arxiv.org/abs/2605.27700.

## 2026-07 Runtime Audit-Commit Update

The same recent work also changes the service audit boundary. A response is not
production-ready merely because it can render claim-level source rows; the
operator must later prove that the exact event, footer hash, display hash, source
count, and audit-error state were durably committed before release. `PaperTrail`
argues for user-facing claim-evidence provenance, `CiteGuard` and `CiteCheck`
show that citation attribution needs retrieval-grounded and metadata-aware
verification, and LLM-search attribution-gap measurements show that consumed
sources and displayed citations can diverge in deployed systems. The Nature
hallucination-incentives result also reinforces that systems need explicit
abstention/fail-closed incentives rather than rewarding plausible answers that
lack verifiable support.

The runtime therefore treats the hash-chained service audit log as part of the
answer release gate. Readiness rejects corrupt existing audit chains, and
attribution routes return a blocked response without answer, display, or source
footer payload if the new audit entry cannot be committed. This keeps public
source footers grounded in an operator-verifiable event history instead of
becoming unprovable presentation text.

References: https://arxiv.org/abs/2602.21045,
https://aclanthology.org/2026.acl-long.282/,
https://arxiv.org/abs/2605.27700,
https://www.cambridge.org/core/journals/data-and-policy/article/attribution-crisis-in-llm-search-results-estimating-ecosystem-exploitation/170DD0B88E5F5AEA8F69F2E9AF1328E3,
and https://www.nature.com/articles/s41586-026-10549-w.

## 2026-07 Verification-Contract Update

The client verifier now publishes a standalone schema for
`rdllm-service-response-verification/v1`, not only for the response payload. This
is a product requirement, not a packaging detail: clients, launch gates, support
bundles, and auditors need to validate the verifier result that says whether an
answer/footer surface is displayable.

Recent work supports treating verifier outputs as first-class artifacts.
`Cited but Not Verified` evaluates citation quality by separating URL
accessibility, topical relevance, and factual support. `CiteCheck` separates
retrieval from verification and emits structured comparison results for exact,
minor, and major citation hallucinations. `PaperTrail` shows the value of
claim-evidence provenance, while also showing that provenance detail must be
usable enough to affect operator and user behavior. A Nature Communications
medical-citation study found high rates of unsupported cited statements, which
reinforces that a source-looking footer is not enough for display approval.

References: https://arxiv.org/abs/2605.06635,
https://arxiv.org/abs/2605.27700, https://arxiv.org/abs/2602.21045, and
https://www.nature.com/articles/s41467-025-58551-6.

The runtime now also fails closed on non-display-safe grounding. If the embedded
grounding verdict is `warning`, `failed`, `blocked_by_policy`, or
`blocked_by_registry`, the service response is `blocked`, includes a
`grounding_quality:` audit error, and renders unsupported claim hashes in the
footer. This follows the same recent evidence: citation systems can produce
working links and plausible metadata while the cited source does not support the
claim, so users need an explicit blocked status and unsupported-claim disclosure
instead of a source-looking footer alone.

## 2026-07 Source-Grounded Acceptance Update

The verifier now exposes a nested
`rdllm-service-source-grounding-acceptance/v1` profile. This turns the research
distinction between link presence, source relevance, factual support, and
faithful citation into a machine-checkable product gate. A response can be
internally consistent for audit while still failing grounded display acceptance;
production display now requires visible verified source rows, supported claim
evidence, minimum support score, non-escrow royalty-share coverage, and a
rendered answer that includes the bound source footer.

This update follows three recent findings. `Cited but Not Verified` shows that
high link validity and relevance do not imply factual citation correctness.
`How Do LLMs Cite?` warns that inline citations can be produced by a distributed
attribution heuristic rather than faithful source use. `Citation-Closure
Retrieval and Per-Rule Attribution` shows that regulated workflows need
claim-to-source closure, not post-hoc source lists. Indirect-prompt-injection
benchmarks also reinforce that attribution must be evaluated end-to-end from
ingestion through answer release.

References: https://arxiv.org/abs/2605.06635,
https://arxiv.org/abs/2606.28358, https://arxiv.org/abs/2605.29742, and
https://arxiv.org/abs/2601.10923.

## 2026-07 Launch-Gate Update

The operator surface now has a fail-closed launch gate because the newest
citation and attribution papers keep separating visible citation shape from
actual source support. `Cited but Not Verified` shows that working, relevant
links can still fail factual support; `Explicit Evidence Grounding via
Structured Inline Citation Generation` shows that document-level citation is
easier than precise evidence-span grounding; `How Do LLMs Cite?` argues that
inline citations may follow shallow attribution heuristics rather than faithful
source use; `Citation-Closure Retrieval and Per-Rule Attribution` shows that
regulated workflows need closure over all required rules, not just a plausible
single source; and legal-citation hallucination benchmarks show that subtle
misquotes and mismatches remain hard even for agentic verifiers.

The practical product rule is that an operator cannot rely on a clean README, a
valid service config, or a source-looking footer in isolation. Before production
display traffic, the deployment must jointly verify the profile controls,
runtime service readiness, bootstrap manifest when present, and at least one
saved attribution response footer. The launch gate is therefore a product
decision surface, while the support bundle is the redacted artifact to share when
the gate blocks.

References: https://arxiv.org/abs/2605.06635,
https://arxiv.org/abs/2606.07130, https://arxiv.org/abs/2606.28358,
https://arxiv.org/abs/2605.29742, and https://arxiv.org/abs/2606.21155.

## 2026-07 Source-Rationale Update

Recent citation-verification papers changed the mechanism target from "show a
source and pay it" to "explain why this source is in the answer footer." The
implementation now treats every visible footer row as a compact attribution
claim: the row must name the source identity, claim-support path, source
availability, reliance/licensing state, settlement state, and a stable
`source_rationale_hash`. The rendered Markdown footer also carries a `why=...`
reason code, and the rendered-attribution audit rejects source rows that do not
explain source selection.

This update follows the recent evidence that citation-looking strings are not
enough: source links can resolve without fact support, scholarly citations can
have subtle metadata drift, and generative feature attribution needs an explicit
contract for what is being explained. The practical rule is therefore fail
closed: cite only rows with verified identity, support, availability, reliance,
rights, and royalty/settlement coverage; otherwise downgrade the footer row to a
review/escrow state.

## Design Takeaways

1. Cite every supported claim, not just the answer as a whole.
2. Treat citation markers as constrained source pointers, not free-form text.
3. Verify generated claims against cited evidence after generation.
4. Keep retrieval, text matching, citation scoring, and training-data attribution as
   separate channels in the ledger.
5. Show users a footer with source identity, evidence quote, source URI, content hash,
   evidence span hash, and grounding coverage.
6. Hold value in escrow when no registered source can be traced.
7. Enforce rights before attribution: a source can be retrievable but not licensed
   for generation, display, quote, external attribution, or training.
8. Log span hashes and policy decisions because reproducible evidence identity can
   be weaker than document-level overlap.
9. Treat conformance as a first-class product artifact. A provider should be able to
   prove that links, relevance, fact support, rights, receipts, and payouts agree.
10. Separate source availability, source quality, citation integrity, and factual
   support. A working URL or registered source is not the same as evidence that
   supports a claim.
11. Separate ownership proof from content matching. A hash can prove that two
    registrations point to the same text, but not which claimant is legally entitled
    to royalties; open conflicts should therefore escrow value until resolved.
12. Make attribution portable. Receipts should not be trapped in one vendor's JSON
    API; they need credential-style proofs and provenance graphs that can move into
    wallets, registries, enterprise audit tools, and transparency services.
13. Close the attribution gap explicitly. A source that was accessed, retrieved, or
    text-matched must be visible to the user, paid, or withheld with a reproducible
    rights/registry escrow reason.
14. Separate public confidence from private audit. Users should see source and
    claim-support facts, while auditors can verify salted commitments for private
    prompts, evidence text, access traces, and economics.
15. Bind provider telemetry to attribution receipts. A source footer is not enough
    if the provider can omit the retrieval/text-match trace; source-access spans,
    citation spans, and claim-support spans need shared hashes and portable
    verification.
16. Treat probabilistic or model-internal attribution as evidence, not final truth.
    Token-level sensitivity, hidden-state probes, activation traces, and influence
    scores should be committed as auditable signals that can support, but not
    silently replace, runtime source and claim evidence.
17. Make attribution configurable by stakeholder objective. Creator compensation,
    user confidence, publisher compliance, and platform auditability need different
    disclosure surfaces over the same signed event.
18. Publish a provider-level attribution card. Per-answer receipts prove individual
    events; model buyers, regulators, creators, and platforms also need a signed,
    comparable deployment summary covering certification, source coverage,
    evidence channels, challenge handling, and known limitations.
19. Publish the proof pack itself. Public confidence should not depend on a provider
    claiming that receipts, traces, statements, challenges, cards, summaries, and
    certification reports exist; the artifact set should have hash roots and
    inclusion proofs that independent verifiers can check.
20. Make the user-facing answer verifiable. A source footer should have a companion
    answer provenance card that binds footer labels and claim span hashes back to
    the receipt and trace without exposing private prompt or evidence text.
21. Materialize cited sources, not just citation strings. A grounded answer should
    carry a verifier report proving source hashes, quote hashes, claim evidence
    spans, source URIs, and answer-card bindings resolve to registered content
    without publishing private source text.
22. Package the answer as a verifiable API object. Foundation-model adoption needs a
    response envelope that returns the rendered answer and embedded public proof
    artifacts together, so customers can verify the response boundary without
    private ledger access.
23. Publish a provider integration profile. A foundation-model API needs a
    machine-readable contract for endpoints, response-envelope format, schemas,
    verifier commands, public surfaces, readiness checks, and bound proof hashes;
    otherwise attribution remains a custom integration instead of a deployable
    standard.
24. Publish a well-known discovery manifest. Customers, creators, auditors, and
    downstream platforms need one stable entry point that tells them where the
    provider card, certification report, integration profile, response envelope,
    assurance bundle, schemas, verifier commands, and proof hashes live.
25. Preserve derivative lineage. Foundation-model and agent pipelines increasingly
    use summaries, synthetic data, tool outputs, and transformed corpora; attribution
    must carry upstream work edges so derivative artifacts do not erase original
    owners from settlement.
26. Benchmark provenance, not only payout. A provider should publish replayable
    attribution-quality evidence across clean, paraphrased, hard-decoy, escrow, and
    derivative-lineage cases so source finding is independently testable.
27. Prove source influence, not just source presence. RAG attribution research now
    separates exposure, utility, and attribution, while counterfactual RAG papers
    test whether evidence changes decisions. Provider proof should therefore ablate
    credited sources and publish replayable influence margins.
28. Treat consent as a lifecycle, not a one-time ingest flag. Rights reservations,
    opt-outs, and revocations need changed-policy hashes, preserved historical event
    hashes, and future-use denial probes so providers can prove they honor updated
    owner intent without rewriting past royalty records.
29. Propagate consent changes across every attribution surface. A source can be
    correctly blocked at retrieval while still leaking through persistent memory,
    private reasoning, post-training signals, stale source footers, downstream
    exchange manifests, or settlement queues. The rights event therefore needs an
    SLA-bound propagation report over all those surfaces before future use or direct
    payout continues.
30. Negotiate attribution before cross-provider use. Static proof publication is
    not enough when one AI system consumes another provider's answer or generated
    work; the caller needs a signed handshake that binds minimum level, required
    artifacts, source-footer relay, escrow relay, runtime headers, and downgrade
    rejection before the content enters a downstream workflow.
31. Make attribution survive copying. Recent LLM-search work shows that relevant
    pages can be consumed without equivalent visible credit; therefore the answer
    itself needs a portable capsule binding the output hash, source-footer proof,
    federation handshake, C2PA-compatible assertion, and SCITT-like statement
    subject after it leaves the original product surface.
32. Make footer confidence explicit. Recent citation-hallucination work shows that
    source-looking strings can be fabricated, stale, or weakly supportive, so the
    response should expose verified/warning/failed footer rows and a hallucination
    taxonomy grounded in source materialization and license proof.
33. Bind the rendered footer itself. Recent verification work increasingly separates
    source identity, source support, confidence calibration, and human inspection,
    so the response should ship a signed client-rendering contract for the exact
    source rows and claim anchors users will see.
34. Make private evidence challengeable. The public footer should not expose private
    prompts, evidence text, access traces, or payout accounts, but auditors still
    need a nonce-bound way to test whether redacted receipt paths open to the
    committed source, claim, rights, and royalty facts.
35. Prevent attribution laundering after copy/reuse. Data-lineage and citation
    hallucination research both point to a second-hop problem: once an AI answer is
    copied into another workflow, downstream systems can cite only the wrapper or
    invent fresh citations. A portable report should bind the downstream event to
    the upstream capsule, verify the copied body hash, carry original source rows
    forward, and settle a pass-through pool to upstream owners.
36. Clear obligations across providers. Data-valuation papers can estimate source
    influence, and citation-evaluation papers can test grounding, but a royalty
    market also needs a neutral clearing artifact that ingests provider statements
    and transitive reuse reports, deduplicates repeated submissions, holds
    overlapping evidence for review, and publishes payable/escrow totals.
37. Bind attribution to payment instructions without overclaiming settlement.
    Once obligations are cleared, creators need remittance rows that can be
    reconciled by payment systems, but the attribution layer should not pretend a
    bank transfer has executed. Therefore the mechanism emits instruction-only
    rows with payout-account hashes, end-to-end IDs, remittance references, and
    hold preservation.
38. Name attribution suppression explicitly. Recent attribution-bias work shows
    that a model can have source or authorship information and still omit visible
    attribution. RDLLM therefore treats footer omissions as an explicit
    `attribution_suppression_count` in answer cards and source-confidence reports,
    so a provider cannot hide known sources behind a generic citation failure.
39. Require independent replay, not provider self-attestation. Recent citation and
    provenance work separates correctness, faithfulness, and support; RDLLM-L45
    therefore turns the whole proof pack into a third-party audit attestation that
    binds public artifacts by hash, replays available verifiers, and records
    negative controls without publishing private prompts, source text, or payout
    accounts.
40. Prove event revenue before payout. Attribution and clearing are not enough if
    the `gross_revenue` field is trusted input, so RDLLM-L46 adds revenue allocation
    reports that bind hashed subscription, advertising, API, enterprise, and
    marketplace revenue pools to event-level gross revenue and creator-pool totals
    before statements, clearing, and remittance.
41. Prove the revenue pools themselves. A provider could conserve a fabricated
    pool, so RDLLM-L47 adds finance ledger attestations that reconcile hash-only
    invoice, billing, ad-server, API-meter, enterprise-contract, and marketplace
    exports to each revenue source without disclosing customer records.
42. Publish the proof pack's replay order. A rich artifact set is not enough if
    auditors must infer verifier order by hand, so RDLLM-L48 adds proof dependency
    graphs that bind artifact hashes, separate hard replay dependencies from
    publication commitments, emit a topological replay order, and reject cycles.
43. Monitor published proof surfaces after release. Attribution is only trustworthy
    if the provider card, certification report, response envelope, assurance
    bundle, and replay graph remain reproducible over time, so RDLLM-L49 adds an
    append-only publication monitor with Merkle snapshots, checkpoint history,
    artifact diffs, and certification-regression blocking.
44. Bind proof artifacts to public trust roots. A witnessed checkpoint is still weak
    if verifier software does not know which provider, auditor, or witness keys are
    active or revoked, so RDLLM-L51 adds a trust registry for signer key hashes,
    key IDs, rotations, revocations, artifact signatures, and witness signatures.
45. Make certification itself independently attestable. A certification report hash
    is useful, but adoption requires a signed object that a customer can verify
    without trusting the provider's web page. RDLLM-L52 adds certification
    attestations that bind the certification report hash, levels root,
    case-status root, certifier identity, target provider, and signature, then lets
    the trust registry verify the certifier key.
46. Prove evidence sufficiency, not only source existence. Recent citation and
    evidence-ranking work shows that a valid source can still be redundant,
    ambiguous, or not the best support for a claim. RDLLM-L56 therefore ranks
    candidate spans per claim, requires the displayed span to be the top-ranked
    minimal sufficient evidence, and records a decoy margin before treating the
    footer as grounded.
47. Adjudicate counterevidence before release. Citation verification and evidence
    ranking still allow one-sided answers when a claim has support but registered
    material directly disputes it. RDLLM-L57 therefore scans registered source
    spans for contradiction candidates and fails answers with unaddressed
    counterevidence before display or settlement.
48. Close the release/application gap. A provider can publish correct late-stage
    grounding artifacts and still serve an answer envelope that does not depend on
    them. RDLLM-L58 therefore requires L55-L57 source availability, evidence
    sufficiency, and counterevidence reports to be embedded and bound in the
    response envelope before a high-certification release gate can emit.
49. Close the answer-surface coverage gap. Sentence-level citation systems and
    claim-evidence interfaces still leave a serving risk: a provider can append an
    unsupported factual sentence to an otherwise grounded response. RDLLM-L59
    therefore hashes every support-bearing public answer sentence and requires it
    to replay to a verified, sufficient, counterevidence-free claim row before
    release.
50. Close the post-hoc citation gap. Retrieval-aware citation systems can still
    attach plausible sources after generation. RDLLM-L60 therefore binds every
    verified displayed claim to source-access spans and redacted generation-context
    block commitments captured before response delivery.
51. Treat retrieved source text as evidence, not instructions. Recent prompt
    injection research shows that webpages, documents, and reusable prompts can
    carry machine-targeted instructions that alter model behavior. RDLLM-L61
    therefore adds source boundary reports: each source packet must be
    hash-bound, role-labeled as evidence, excluded from control/instruction
    channels, and unable to modify attribution or payout policy.
52. Prove which proof channels influenced the final answer. Recent attribution,
    citation, and prompt-injection work converges on the same operational gap:
    users need not only source footers, but a replayable reason why a source was
    cited, paid, or ignored. RDLLM-L62 therefore adds a decision provenance graph
    over claim grounding, visible footer rows, payout participation, and release
    decisions, with source text admitted as evidence only and never as payout or
    policy control.
53. Calibrate attribution confidence instead of implying certainty. Recent RAG and
    faithfulness work shows that source correctness, actual reliance, and metric
    faithfulness can diverge. RDLLM-L63 therefore adds a calibrated attribution
    confidence report: every public claim, footer row, and payout-participation row
    carries a benchmark-backed lower confidence bound, and low-confidence rows must
    be disclosed or escrowed.
54. Verify source authenticity before direct credit or payment. Recent poisoning
    work shows that retrieved knowledge bases can be adversarially injected, and
    source-attribution work shows that influence must be traced to the actual text
    responsible for a generation. RDLLM-L64 therefore binds public source rows to
    trusted origin evidence, archive consensus, active license terms, source-farm
    risk, poisoning risk, and synthetic-source disclosure; failed rows remain
    visible only with warnings and route payment to escrow until review.
55. Make external verification economically accountable. Recent citation and
    provenance work motivates independent replay, but settlement systems also need
    consequences for incorrect or conflicted verifier attestations. RDLLM-L72
    binds accepted verifier rows to trust-registry identity, non-revoked key
    hashes, slashable bond coverage, conflict disclosures, challenge rows, and
    slashing evidence before verifier-approved settlement can leave escrow.
56. Make the economic usage log globally consistent, not merely signed. Certificate
    Transparency, SCITT, and witness systems show that inclusion proofs are not
    enough if different parties can be shown different roots. RDLLM-L73 therefore
    compares receipt-log snapshots across provider, creator, customer, and witness
    views, verifies append-only prefixes and required receipt inclusion, detects
    split-view roots, and escrows settlement when the usage log cannot be replayed
    as one consistent history.
57. Make monitoring economically live. Transparency logs still fail in practice
    when nobody watches them, when monitors are incomplete, or when a provider can
    delay remediation after a public defect is discovered. RDLLM-L74 therefore
    requires registered independent watchtower attestations over the L73 subject,
    treats open or accepted public challenges as settlement blockers, and emits
    hash-only slashing and bounty rows for accepted verifier-observation failures.
58. Prove that footer sources were actually relied on. Recent citation work shows
    that correct-looking references and source-support checks can still diverge
    from actual generation reliance. RDLLM-L100 therefore emits citation reliance
    receipts that bind visible footer rows to pre-generation evidence locks,
    rendered claim-evidence rows, claim-source replay, causal utility trials,
    current-turn trace membership, source-access leases, and content-protocol
    permission before a directly settled source can be treated as faithful.
59. Make license authorization transactional, not just declared. Machine-readable
    rights protocols and provenance ledgers are necessary but insufficient if the
    provider cannot prove the publisher or license server actually authorized the
    exact source access. RDLLM-L101 therefore emits license transaction receipts:
    signed authorization tokens, license-ledger inclusion, source-access nonce and
    meter binding, protocol-term matching, transaction validity checks, and escrow
    routing for missing, expired, unsigned, non-ledgered, or mismatched tokens.
60. Make the answer footer the verification surface. Recent work separates source
    identity, factual support, actual reliance, confidence calibration, and
    rights authorization, so RDLLM-L102 emits grounded source footer receipts that
    bind each visible footer row to confidence, availability, exact public
    evidence regions, citation reliance, license transactions, and public
    verifier handles without exposing prompt, answer, source, evidence, or payout
    data.
61. Make delivery part of attribution, not a UI convention. Faithful citations and
    grounded footer receipts still fail users if the served answer drops footer
    rows, span handles, or verifier metadata. RDLLM-L103 therefore emits source
    footer delivery receipts that bind the grounded footer to the proof-carrying
    response, copied output, gateway egress hash, source labels, claim span
    handles, and public verifier metadata.
62. Make attribution portable as a minimum model API contract. Recent citation,
    provenance, and content-credential work points to the same deployment problem:
    a citation row is not trustworthy unless generic clients know which headers,
    embedded proof objects, verifier paths, and fail-closed policies must be
    present. RDLLM-L104 therefore emits foundation API attribution profiles that
    bind the provider card, certification report, integration profile, discovery
    manifest, response envelope, and L103 source-footer-delivery receipt into a
    vendor-neutral response contract.
63. Make the relying client prove enforcement. API-boundary attestation work and
    content-provenance deployments show that provider metadata is insufficient if
    downstream clients can strip, ignore, or rewrite it. RDLLM-L105 therefore
    emits client attribution enforcement receipts that bind observed response
    headers, embedded proof objects, verifier commands, source labels, and the
    client's render/block decision before a chat, search, agent, or relay surface
    displays an attributed answer.
64. Make persistent memory a provenance-bearing derived work. Long-running agents
    increasingly write summaries, profile facts, and cross-session memories; if
    those memory cells are later used in an answer, the user and creator need the
    same source carry-forward that a direct retrieval answer would have. RDLLM-L106
    therefore emits persistent memory provenance receipts that bind memory writes,
    reads, source labels, upstream proof hashes, license and retention policy,
    royalty obligations, delete tombstones, and visible footer labels.
65. Make private reasoning attribution auditable without exposing chain-of-thought.
    Foundation models, routers, and agent runtimes increasingly use hidden
    scratchpads, delegated reviewers, and intermediate summaries. RDLLM-L107 emits
    private reasoning attribution receipts that commit to those private traces by
    hash, bind them to L106 memory and L105 client proofs, require every hidden
    source label to appear in the verified footer, and preserve royalty rows
    without publishing raw reasoning text.
66. Prevent synthetic-source attribution laundering. Recent source-attribution and
    cited-RAG work shows that a visible source can be relevant, reachable, and
    cited while still being an AI-generated wrapper or weakly supported proxy for
    the original human work. RDLLM-L121 therefore adds source-origin lineage:
    direct payout requires trusted human-origin attestation; synthetic sources
    require upstream creator lineage and share conservation; unknown or
    unattributed synthetic sources are shown to users but settled to
    origin-review escrow.
67. Make the footer human-inspectable without exposing full source text. Recent
    citation-auditing work emphasizes that users over-trust bare citations and
    need visible evidence that the source actually supports the answer. RDLLM-L122
    therefore adds evidence-preview footers: each verified visible claim must
    publish a short permissioned snippet, source URL, warrant label, origin label,
    and proof hash, while full source text, prompts, answers, private reasoning,
    and payment data remain undisclosed.
68. Make the source preview click-through verifiable. Recent citation-verification
    and source-auditing work shows that link labels and snippets are still weak
    unless the reader can resolve the exact passage that grounded the claim.
    RDLLM-L123 therefore adds evidence-locator manifests: each preview snippet
    must bind to an exact public resolver URL, resolver status, and snapshot or
    text-fragment proof without redisclosing full source or excerpt text.
69. Make foundation-model attribution provider-neutral. Current model APIs expose
    different native response envelopes, tool-call shapes, citation annotations,
    streaming events, and metadata surfaces. RDLLM-L125 therefore adds a composite
    foundation adapter: OpenAI Responses, Anthropic Messages, Google Gemini,
    Meta/Llama-style, Mistral, Cohere, xAI, Bedrock, Azure OpenAI, and
    OpenAI-compatible responses must bind their
    native output hash, headers, JSON proof fields, citation/tool paths, and final
    streaming metadata to the same RDLLM response envelope, source-footer delivery,
    and citation URL-health receipts before a client can call the answer grounded.
70. Make provider compatibility fixture-backed. RDLLM-L126 adds a foundation
    provider conformance matrix so every supported provider family publishes
    hash-only positive and negative fixtures for attribution-critical response
    modes, claim-support footers, parametric-memory fallback, and fail-closed
    citation or proof failures.
71. Make provider compatibility executable at response time. RDLLM-L127 adds a
    foundation runtime adapter receipt so a concrete native provider response
    either normalizes into the RDLLM response envelope, footer, URL-health proof,
    attribution headers, JSON proof fields, citation paths, and stream-final
    hashes, or fails closed before display.
72. Make multi-provider routing non-bypassable. RDLLM-L128 adds a foundation
    runtime router receipt so broker APIs, fallback stacks, latency routers, and
    cost routers must prove every candidate provider route is adapter-backed,
    conformance-backed, hash-committed, and fail-closed before any selected
    provider response is displayed.
73. Make backend model substitution non-bypassable. RDLLM-L129 adds a foundation
    model deployment attestation so the selected route must bind to an active
    provider deployment key, signed model/version commitments, and
    request/response boundary hashes before display.
74. Make composite answers non-bypassable. RDLLM-L130 adds a universal composition
    receipt so an answer assembled from multiple foundation providers must bind
    every segment to one released L129 deployment attestation, source-footer
    delivery hash, telemetry span commitment, and conserved provider weight.
75. Make source-grounded composition settleable. RDLLM-L131 adds a universal
    composition settlement receipt so every L130 provider segment must bind its
    displayed source labels and claim IDs to source-entitlement weights,
    creator-obligation rows, preserved source-footer delivery, and conserved
    revenue allocation totals. Payable rows require licensed or verified sources;
    unresolved rows go to escrow, and disputed, blocked, or revoked rows are held.
76. Make foundation-model adoption one contract, not a provider-by-provider
    assertion. RDLLM-L132 adds a universal foundation model contract so all
    supported provider families must share the same adapter, conformance,
    runtime, router, deployment, composition, settlement, discovery, and public
    surface proof chain before a response can be released as RDLLM verified.
77. Make native provider calls pass through an attribution gate before invocation.
    RDLLM-L133 adds a universal invocation guard so a raw OpenAI-, Anthropic-,
    Gemini-, Bedrock-, Azure-, xAI-, Cohere-, Mistral-, Meta/Llama-, or
    OpenAI-compatible call cannot bypass the L132 contract, selected route,
    deployment attestation, request/response boundary, source-footer requirement,
    fail-closed headers, or GenAI telemetry.
78. Make deployment-wide provider usage reconcile to the gate. RDLLM-L134 adds a
    universal invocation coverage report so every native provider meter event must
    match one L133 guard, gateway egress record, source-footer delivery hash,
    response-envelope hash, billed unit row, gross-revenue row, creator-pool row,
    and provider invoice row before complete attribution coverage can be certified.
79. Make coverage non-repudiable. RDLLM-L135 adds a universal invocation witness
    report so every L134-covered native provider call must bind to a
    provider-signed usage receipt, independently observed egress event, and
    independent witness quorum before a deployment can claim omitted calls would
    be externally detectable.
80. Make exported content carry attribution after it leaves the chat surface.
    RDLLM-L136 adds a universal content credential that binds output hashes,
    source-footer delivery, response envelopes, invocation witnesses, and
    C2PA/VC-shaped provenance assertions so copied text, media, files, and agent
    handoffs can still point back to their attribution proof chain.
81. Make deployment adoption inspectable as one public passport. RDLLM-L137 adds a
    universal RDLLM passport that binds certification, provider card, integration
    profile, discovery manifest, assurance bundle, proof graph, foundation
    adapters, invocation controls, composition/settlement receipts, and content
    credentials into a single offline-verifiable provider object.
82. Make adoption provider-neutral and procurement-ready. RDLLM-L138 adds a
    universal adoption standard package with required artifacts, implementer
    roles, SDK surfaces, public discovery surfaces, verifier commands,
    procurement gates, and standards mappings, so a foundation-model provider,
    gateway, enterprise client, auditor, registry, or clearinghouse can adopt the
    same attribution mechanism without private integration rules.
83. Make adoption executable before compatibility claims. RDLLM-L139 adds a
    universal interop test kit with provider-family golden fixtures, SDK
    bindings, CI/offline runners, negative mutation cases, verifier commands, and
    discovery paths, so a provider, gateway, SDK, client, or auditor can replay
    compatibility instead of trusting an implementation declaration.
84. Make runtime context access become attributable evidence before the answer is
    released. RDLLM-L140 adds a universal context provenance bridge for MCP
    tools, retrieval, vector stores, file search, browser search, enterprise
    connectors, creator license endpoints, memory, and media credentials. Every
    context event must be authorized, licensed, projected into a source claim,
    rendered in the footer when it supports the answer, bound to agent-step
    attribution, and projected into royalty settlement. Unauthorized context,
    stale leases, hallucinated citations, missing footers, unbound agent steps,
    rights-denied sources, token-audience mismatches, connector audit gaps, and
    private text leaks fail closed.
85. Make displayed citations independently verifiable before users rely on them.
    RDLLM-L141 adds a universal citation verification contract that binds the
    L140 context bridge to source identity, resolver/URL health, exact evidence
    locators, metadata fidelity, claim support, evidence-force calibration,
    source confidence, warranted footer rows, rendered attribution audits, source
    authenticity, and royalty state. Nonexistent sources, metadata drift,
    inaccessible locators, unsupported cited claims, overclaimed evidence force,
    footer/context mismatches, hallucinated labels, missing royalty state, stale
    snapshots, and private-text leaks fail closed.
86. Treat cached or reused answers as fresh attributable usage, not as free
    provider-side bypasses. RDLLM-L142 adds a universal grounded reuse contract
    for semantic answer caches, gateway response caches, native provider
    prompt/KV caches, reusable agent reports, and enterprise RAG caches. It
    requires query-equivalence and evidence-overlap checks, source freshness,
    consent/license continuity, L141 citation continuity, cache-collision
    resistance, provider-family coverage, and a new royalty-metered reuse event
    before a cache hit can be displayed as grounded.
87. Cover every declared model capability, not just text responses. Recent
    citation-integrity work shows that a source-looking footer can be fabricated,
    unsupported, stale, or metadata-drifted, while current model APIs expose
    attribution-relevant behavior across tools, web search, files, vision, audio,
    realtime sessions, image/video generation, embeddings, reranking, fine-tuning,
    batch, safety, and local-runtime surfaces. RDLLM-L181 therefore makes every
    declared capability and modality pair prove either verified source-footer
    behavior or an explicit no-source abstention path, with settlement held and
    invocation blocked for uncovered capability rows.

## 2 June 2026 Verification Addendum

The L130 implementation pass rechecked the most relevant recent primary sources
for the production bypass case: a model gateway, broker API, or fallback stack can
strip attribution even if one upstream provider response was correctly grounded.
The update maps those sources into a concrete invariant: attribution cannot be a
single-provider response feature; it must be enforced by the router that chooses
the model actually displayed to the user.
The L129 pass extends the same evidence boundary from the router to the selected
backend deployment: a route label is not enough unless the provider signs the
model deployment identity and binds it to the concrete request/response boundary.
The L131 pass extends the boundary from attribution proof to settlement proof:
showing a source footer is not enough unless the same source rows, claim IDs, and
provider segment weights reconcile to payable, escrowed, or held creator
obligations under a conserved revenue allocation pool.
The L132 pass turns L125-L131 into a single adoption contract: provider families
with different native APIs can only claim RDLLM compatibility when they publish
one reproducible proof chain that covers provider discovery, public surfaces,
runtime route selection, deployment identity, source footer, and settlement
readiness.
The L133 pass moves that contract from publication to pre-call enforcement: the
gateway must prove the exact native invocation carries the L132 hash, route hash,
deployment hash, request-projection hash, response-binding hash, source-footer
delivery hash, response-envelope hash, fail-closed header contract, and
provider/model telemetry before it calls the model.
The L134 pass moves enforcement from a single invocation to a deployment window:
native provider meters, gateway egress logs, L133 guard receipts, source-footer
delivery hashes, response-envelope hashes, invoice rows, gross revenue, and
creator-pool rows must reconcile one-to-one, or the deployment cannot claim that
all foundation-model usage is attributable and settlement-ready.
The L135 pass adds non-repudiation to that window: provider-signed usage receipts,
independent egress observations, and independent witness quorum evidence must
bind to each covered invocation, or the deployment cannot claim omitted
foundation-model calls are externally detectable.
The L136 pass makes source attribution survive export and copying: the generated
asset itself carries a credential-style proof pointer to the answer envelope,
source-footer delivery, invocation witness, and upstream proof chain.
The L137 pass makes provider adoption inspectable: every proof artifact needed to
evaluate a deployment is bound into one passport with public surfaces and verifier
commands.
The L138 pass turns that passport into an implementer-facing standard: the package
names the required artifacts, roles, SDK surfaces, procurement gates, discovery
paths, and standards mappings needed for universal adoption across foundation
model providers, gateways, enterprise clients, creator registries, auditors, and
clearinghouses.
The L139 pass turns the standard into an executable compatibility kit: provider
families must ship golden request/response fixtures, SDKs must prove fail-closed
footer/proof handling, CI and offline runners must replay the kit, and negative
mutation cases must block before a deployment claims universal RDLLM adoption.

- OpenTelemetry's GenAI semantic conventions explicitly account for proxied or
  hosted provider paths: multiple providers can expose OpenAI-compatible APIs, and
  request model, response model, provider, and server attributes are needed to
  identify the actual system in use. RDLLM-L128 turns that observability warning
  into a release rule: each candidate route is hash-bound to provider identity,
  adapter coverage, conformance fixtures, and fail-closed fallback behavior before
  display: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
- Sovereign Context Protocol argues that creator-owned data access should be
  logged, licensed, and attributable at runtime, not only summarized after
  training. RDLLM-L128 extends that runtime principle to multi-provider routing:
  a gateway cannot consume or relay model output unless the selected route carries
  the same attribution and license proof chain: https://arxiv.org/abs/2603.27094
- Cited but Not Verified and CiteCheck show why visible citations are not enough:
  a source row must resolve to accessible, relevant, fact-supporting, and
  metadata-faithful evidence. RDLLM-L128 therefore requires the selected route to
  bind to L123-L127 evidence-locator, URL-health, adapter, conformance, and
  runtime-normalization artifacts rather than accepting provider-written citation
  strings: https://arxiv.org/abs/2605.06635 and https://arxiv.org/abs/2605.27700
- AuthGraph shows the value of comparing actual execution provenance against an
  authorization graph at tool and parameter-source level. RDLLM-L128 applies the
  same idea to economic attribution: the actual router decision must match the
  authorized provider-route graph, and unproven route substitutions fail closed:
  https://arxiv.org/abs/2605.26497
- The Attribution Contract and probabilistic token-attribution work reinforce that
  attribution claims need an explicit contract and uncertainty-aware evidence. The
  router receipt therefore does not claim to prove hidden model causality by
  itself; it proves the deployment boundary: which provider output was selected,
  which attribution proof artifacts accompanied it, and whether fallback choices
  preserved or broke that proof chain: https://arxiv.org/abs/2605.23080 and
  https://arxiv.org/abs/2605.21726
- AEX and provider-neutral GenAI telemetry make the API-boundary problem explicit:
  model calls can pass through intermediaries, compatibility layers, and hosted
  gateways. RDLLM-L129 therefore binds the public selected-route row to a signed
  deployment statement, active deployment-key hash, opaque model commitments, and
  native response/output hashes rather than trusting model-name strings alone:
  https://arxiv.org/abs/2603.14283 and
  https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
- AEX also separates source outputs from transformed, buffered, aggregated, or
  repackaged outputs; OpenTelemetry GenAI spans provide provider/model/response
  correlation fields. RDLLM-L130 uses those observations for composition: it
  treats a merged answer as a new proof object whose provider segments must carry
  their own deployment attestations, trace-span commitments, source-footer hashes,
  and weight conservation before release.
- The Attribution Contract requires attribution claims to specify the output,
  eligible features, generation process, held-fixed values, and attributed score.
  RDLLM-L131 maps that contract shape into settlement: source-entitlement rows
  must name the L130 segment, source label, claim ID, entitlement weight, rights
  status, and claimant status before any creator obligation can be recomputed:
  https://arxiv.org/abs/2605.23080
- A Human-Centric Framework for Data Attribution in LLMs emphasizes that
  attribution systems must serve different stakeholder objectives. RDLLM-L131
  therefore keeps public source footers, private audit hashes, revenue allocation,
  and creator payment/escrow/hold status as separate but linked artifacts:
  https://arxiv.org/abs/2602.10995
- SoK: Blockchain Agent-to-Agent Payments identifies a four-stage lifecycle for
  trustworthy agent payments: discovery, authorization, execution, and accounting.
  RDLLM-L131 applies the same separation to creator royalties: source attribution
  and rights authorization are not treated as final settlement unless the
  accounting artifact conserves creator-pool value and exposes payable, escrow,
  and held totals: https://arxiv.org/abs/2604.03733
- Official provider APIs expose materially different response, streaming, tool,
  citation, model, and deployment surfaces. RDLLM-L132 therefore treats provider
  compatibility as a contract over artifacts rather than as one JSON shape:
  OpenAI Responses, Anthropic Messages, Google Gemini, Amazon Bedrock Converse,
  Azure OpenAI Responses, Mistral, Cohere, xAI, Meta/Llama-style, and
  OpenAI-compatible rows all have to map into the same public RDLLM proof chain:
  https://platform.openai.com/docs/api-reference/responses
- AEX's API-boundary attestation model, SEAR's multi-provider gateway schema,
  OpenTelemetry GenAI provider/model attributes, AuthGraph's provenance-vs-
  authorization comparison, and DataDignity/OLMoTrace output-to-source tracing all
  point to the same engineering rule: attribution cannot be added only after a
  model answers. RDLLM-L133 therefore makes the gateway admission decision itself
  a signed artifact, with missing headers, route drift, request/response drift,
  source-footer omission, telemetry drift, or private-text leakage blocking the
  native provider call. RDLLM-L134 adds the complementary accounting control:
  provider-side meter and invoice rows must reconcile against those admission
  artifacts so compliant sample calls cannot hide unguarded production calls.
  RDLLM-L135 adds the non-repudiation control: coverage rows must be backed by
  provider receipts, independent egress observations, and independent witnesses:
  https://arxiv.org/abs/2603.14283
  https://arxiv.org/abs/2603.26728
  https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
  https://arxiv.org/abs/2605.26497
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2504.07096
  https://docs.anthropic.com/en/api/messages
  https://ai.google.dev/gemini-api/docs
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
  https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses
  https://docs.mistral.ai/api/
  https://docs.cohere.com/reference/chat
  https://docs.x.ai/docs/api-reference
- C2PA 2.2, W3C Verifiable Credentials/Data Integrity, SCITT/RFC 9943, and
  OpenTelemetry GenAI conventions provide the closest existing interoperability
  anchors for RDLLM-L136 through L139: signed provenance assertions, portable
  proof-carrying claims, transparency statements, and provider-neutral telemetry.
  RDLLM adds the missing AI-royalty-specific contract: visible source footers,
  exact claim/source bindings, rights gates, payout/escrow rows, provider
  passports, and adoption gates must all hash back to the same proof chain:
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
  https://www.w3.org/TR/vc-data-integrity/
  https://www.w3.org/TR/vc-data-model/
  https://www.rfc-editor.org/rfc/rfc9943.html
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
- The newest citation-integrity papers make L138's visible-footer requirement
  non-optional. Cited but Not Verified separates link validity, relevance, and
  factual support; CiteCheck separates existence from metadata faithfulness; and
  LLM Hallucinations in the Wild shows fabricated references entering scholarly
  corpora at scale. L138 therefore requires source-footer rendering and verifier
  commands as procurement gates, not as UI decoration:
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.27700
  https://arxiv.org/abs/2605.07723
- Recent data-provenance and attribution-protocol work pushes the mechanism
  beyond one payout table. Sovereign Context Protocol argues for logged,
  licensed, runtime-attributable source access; Tracing the Data Trail surveys
  provenance, transparency, and traceability across LLM lifecycles; DataDignity
  frames output auditing as pinpoint provenance; and ProToken shows token-level
  attribution can be represented without exposing private training records.
  RDLLM-L137/L138/L139 therefore treats runtime footers, training summaries,
  invocation telemetry, private audit commitments, and settlement rows as linked
  but distinct proof surfaces:
  https://arxiv.org/abs/2603.27094
  https://arxiv.org/abs/2601.14311
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2601.19672
- The L181 pass adds capability coverage because the recent citation literature
  and provider API surfaces now point to the same deployment risk: attribution
  cannot be proved only for a canonical text chat endpoint. Cited but Not
  Verified, CiteCheck, LLM Hallucinations in the Wild, and URL-health work show
  that source rows need materialization, metadata, link-health, relevance, and
  support checks; official OpenAI, Gemini, Claude, and Bedrock documentation show
  that source-affecting work happens through tools, web search, files, streaming,
  realtime, citations, multimodal inputs, batch, and async surfaces. RDLLM-L181
  therefore requires capability fixtures, modality-pair fixtures, operation
  surface fixtures, route-capability rows, and negative fail-closed fixtures
  before a provider can claim model invocation, response release, footer reliance,
  or creator settlement:
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.27700
  https://arxiv.org/abs/2605.07723
  https://arxiv.org/abs/2604.03173
  https://platform.openai.com/docs/api-reference/responses
  https://platform.openai.com/docs/guides/tools
  https://platform.claude.com/docs/en/build-with-claude/citations
  https://ai.google.dev/gemini-api/docs/function-calling
  https://ai.google.dev/gemini-api/docs/live
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
- The L182 pass adds live provider-capability discovery because current source
  footers can otherwise imply confidence from stale or undocumented model
  capability claims. Recent May 2026 citation papers show that link validity and
  citation shape are not enough; source rows need verification against actual
  materialized evidence and citation metadata. Provider docs also show that
  model capability support lives in mutable catalogs and endpoint-specific docs:
  OpenAI Responses/tools, Claude citations/tool use/model docs, Gemini models,
  Search grounding, function calling, Live API, Batch API, and Bedrock Converse
  supported-model surfaces. RDLLM-L182 therefore binds every capability claim to
  fresh official or attested provider evidence, endpoint compatibility, lifecycle
  status, region/tenant scope, L181 route coverage, and negative fixtures before
  invocation, response release, footer reliance, or creator settlement:
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.07723
  https://arxiv.org/abs/2605.08583
  https://arxiv.org/abs/2605.27700
  https://www.microsoft.com/en-us/research/publication/datadignity-training-data-attribution-for-large-language-models/
  https://platform.openai.com/docs/api-reference/responses
  https://platform.openai.com/docs/guides/tools
  https://platform.openai.com/docs/guides/tools-web-search
  https://platform.claude.com/docs/en/build-with-claude/citations
  https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
  https://ai.google.dev/gemini-api/docs/models
  https://ai.google.dev/gemini-api/docs/google-search
  https://ai.google.dev/gemini-api/docs/function-calling
  https://ai.google.dev/gemini-api/docs/live
  https://ai.google.dev/gemini-api/docs/batch-api
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
  https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html
- The L183 pass adds native source-annotation normalization because official
  provider APIs expose source evidence in incompatible response shapes. OpenAI
  Responses output text can carry URL, file, container-file, and file-path
  annotations; Claude citations expose character, page, content-block, and
  streaming citation-delta forms; Gemini Search grounding returns
  `groundingMetadata` with search queries, grounding chunks, and grounding
  supports; and Bedrock Converse document blocks can enable document-specific
  citations. RDLLM-L183 therefore treats provider-native annotations as source
  evidence that must be parsed, hash-bound, normalized into RDLLM footer fields,
  finalized for streams/batches, and rejected if dropped, unsupported, or
  mismatched against the rendered footer:
  https://platform.openai.com/docs/api-reference/responses/create
  https://platform.openai.com/docs/guides/tools-web-search
  https://platform.openai.com/docs/guides/tools-file-search
  https://platform.claude.com/docs/en/build-with-claude/citations
  https://platform.claude.com/docs/en/api/python/messages
  https://ai.google.dev/gemini-api/docs/google-search
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html

## May 2026 Literature and Standards Scan

The latest improvement pass focused on sources that directly affect attribution
quality, training-data provenance, and privacy-preserving proof:

- Memori (arXiv, 23 March 2026) treats persistent memory as an explicit layer for
  context-aware LLM agents. RDLLM-L106 adds the missing attribution controls for
  that layer: memory writes and reads are not trusted unless they preserve source
  labels, upstream proof hashes, license/retention terms, royalty obligations, and
  delete tombstones, and unless downstream answers carry the memory's source labels
  into the verified footer: https://arxiv.org/abs/2603.19935
- MemIR (arXiv, 25 May 2026) identifies "provenance-role collapse" in long-term
  agents when historical interactions are stored as flat text. Its typed memory
  representation separates raw evidence, retrieval cues, and truth-bearing claims.
  RDLLM-L106 adopts the same failure boundary at the receipt layer: memory cells
  must declare source roles, upstream proof hashes, and visible footer carry-forward
  before later answers can rely on them: https://arxiv.org/abs/2605.25869
- MemORAI (arXiv, 2 May 2026) reports that graph memory systems can lack provenance
  tracking and proposes turn-level factual-origin tracking in a multi-relational
  graph. RDLLM-L106 turns that architectural idea into a portable audit receipt:
  source labels, memory reads, rendered-output hashes, and royalty obligations are
  replayable outside the memory runtime: https://arxiv.org/abs/2605.01386
- MemTrace (arXiv, 27 May 2026) frames memory reliability as executable evolution
  graphs and root-cause attribution for memory failures. RDLLM-L106 therefore
  treats memory writes, reads, tombstones, and carried source labels as audit
  events rather than opaque assistant state: https://arxiv.org/abs/2605.28732
- MemLineage, MemQ, and MemMark (May 2026) sharpen the remaining design constraints:
  memory entries need cryptographic lineage and derivation DAGs; credit can
  propagate through memory provenance DAGs; and attribution should survive leaked
  or migrated snapshots with commitments or watermark-style evidence. RDLLM-L106
  does not make watermarking mandatory, but its proof slots can carry such evidence
  alongside source-label and royalty carry-forward receipts:
  https://arxiv.org/abs/2605.14421, https://arxiv.org/abs/2605.08374, and
  https://arxiv.org/abs/2605.25002
- The Model Context Protocol specification standardizes agent access to external
  context and tools. RDLLM-L106 extends the same systems view to persistent memory:
  durable context is treated as a provenance-bearing input, not invisible model
  state: https://modelcontextprotocol.io/specification/2025-06-18
- TRACER (arXiv, 11 May 2026), AEX, and agent tracing practice all point at a
  multi-stage provenance problem: generated outputs can depend on tool calls,
  intermediate reasoning, model handoffs, and runtime routing, not only the final
  answer text. RDLLM-L107 adds a privacy-preserving receipt for that boundary:
  source-influenced hidden steps are represented by commitments, artifact hashes,
  source labels, memory/tool/delegation references, and royalty rows, while raw
  chain-of-thought remains private:
  https://arxiv.org/abs/2605.09934, https://arxiv.org/abs/2603.14283, and
  https://openai.github.io/openai-agents-js/guides/tracing
- DataDignity (arXiv, 7 May 2026) frames output auditing as pinpoint provenance:
  an auditor may need to identify the source document most likely supporting a
  response. RDLLM maps that idea into `claim_support`, source commitments, and a
  public source footer: https://arxiv.org/abs/2605.05687
- RISE (arXiv, 17 April 2026) makes data attribution and valuation more scalable
  by sketching output-layer influence signals rather than indexing full gradients.
  RDLLM treats that as an adoption-grade model-native evidence channel that can
  inform training-value priors while remaining separate from runtime source proof:
  https://arxiv.org/abs/2604.16197
- ZK-Value (arXiv, 5 May 2026) shows a practical zero-knowledge path for
  verifiable data valuation, including an LSH-Shapley primitive and compact
  verification. RDLLM-L95 uses the same privacy-verifiability direction for
  residual corpus royalty evidence, and RDLLM-L96 adds a benchmarked
  valuation-method audit before those residual rows can be trusted: public rows
  carry evidence hashes, benchmark commitments, and conservation checks rather
  than raw validation data or source text:
  https://arxiv.org/abs/2605.03581
- Cited but Not Verified (arXiv, 7 May 2026) and CiteAudit (arXiv v3,
  1 May 2026) show that link validity, topical relevance, and plausible metadata
  are not enough; the cited content must factually support the claim. RDLLM-L97
  responds by binding rendered claim spans and source-footer labels to exact
  page, line, character, bounding-box, or timecode regions and by requiring
  wrong-region controls to fail:
  https://arxiv.org/abs/2605.06635 and https://arxiv.org/abs/2602.23452
- Sovereign Context Protocol (arXiv, 28 March 2026) argues that attribution
  should become a default property of source access, with logged, licensed, and
  attributable creator-owned data consumption. RDLLM-L98 implements creator-side
  access leases, and RDLLM-L99 extends the idea to external web-scale protocol
  ingestion so RSL, CoMP, SCP, ODRL, Croissant, robots.txt, and C2PA/TDM signals
  can be preserved into RDLLM contracts, leases, and escrow routing:
  https://arxiv.org/abs/2603.27094
- RSL and CoMP style publisher protocols turn content access into a
  machine-readable licensing and compensation negotiation surface. RDLLM-L99 does
  not replace those protocols; it verifies that their terms were discovered,
  hash-preserved, and enforced inside the RDLLM proof chain:
  https://rslstandard.org/
- The 2026 ACL survey on attribution, citation, and quotation highlights the
  fragmented evaluation landscape for evidence-based text generation. RDLLM maps
  that taxonomy into separate artifacts for citation identity, claim support,
  footer rendering, and exact source-region binding:
  https://arxiv.org/abs/2508.15396
- Concept Influence (arXiv, 16 February 2026) attributes model behavior to
  semantic directions rather than only individual examples. RDLLM treats that as
  a possible valuation-evidence method for residual training value, but still
  requires rights gating, direct-attribution exclusion, creator caps, receipts,
  and escrow:
  https://arxiv.org/abs/2602.14869
- Probabilistic Attribution For Large Language Models (arXiv, 20 May 2026) defines
  token attribution from next-token probabilities and entropy, which is useful for
  identifying unstable or influential parts of a generation. RDLLM treats that as a
  model-internal evidence channel that can be attached to telemetry without
  substituting for source proof: https://arxiv.org/abs/2605.21726
- Attribution Bias in Large Language Models (arXiv, 6 April 2026) introduces
  attribution suppression: models can omit attribution even when authorship
  information is available. RDLLM maps that failure mode into visible footer
  checks, source-confidence taxonomy, and release-gate blocking rather than
  treating it as a vague citation-quality issue: https://arxiv.org/abs/2604.05224
- Key-discovery and trust-root standards show how this should surface in a
  production provider contract: RFC 7517 defines JSON Web Keys and key IDs, W3C
  DID Core defines verification methods for decentralized identifiers, and
  Sigstore distributes root-of-trust material through TUF. RDLLM-L51 maps those
  patterns into a provider-neutral trust registry for attribution proofs:
  https://www.rfc-editor.org/rfc/rfc7517
  https://www.w3.org/TR/did-core/
  https://docs.sigstore.dev/about/security/
  https://docs.sigstore.dev/cosign/signing/overview/
- The Attribution Contract (arXiv, 21 May 2026) argues that feature-attribution
  claims need an explicit contract naming the output, eligible features, held-fixed
  assumptions, and attributed score. RDLLM maps that into signed artifacts: every
  footer, source-confidence row, model-signal row, and certification attestation
  declares exactly what is being explained and what hash roots were bound:
  https://arxiv.org/abs/2605.23080
- CiteCheck (arXiv, 26 May 2026) reinforces that citation verification must check
  both existence and metadata faithfulness. RDLLM uses that distinction in source
  verification and citation-footer contracts, then adds L52 so users can verify
  that the whole citation-proof mechanism was certified by a signer rather than
  only asserted by the response provider: https://arxiv.org/abs/2605.27700
- SURE-RAG (arXiv, 5 May 2026) treats evidence sufficiency as a set-level property:
  individual passage scores can miss missing hops, unresolved conflicts, and
  retrieval uncertainty. RDLLM-L56 and L57 now mirror that separation by requiring
  claim-level sufficient support and explicit counterevidence adjudication before
  the L58 release gate can emit: https://arxiv.org/abs/2605.03534
- Towards Dependable Retrieval-Augmented Generation Using Factual Confidence
  Prediction (arXiv, 4 May 2026) uses conformal prediction and diagnostic checks
  to attach confidence to whether retrieved chunks came from a correct source and
  whether generated answers are consistent with retrieved context. RDLLM-L63 maps
  that design pressure into public lower-bound confidence fields rather than a
  single uncalibrated source score: https://arxiv.org/abs/2605.05244
- Faithfulness Metrics Don't Measure Faithfulness (arXiv, 24 May 2026) warns that
  many faithfulness metrics perform near chance under ground-truth evaluation.
  RDLLM-L63 therefore does not let a provider publish a bare faithfulness number:
  it binds attribution claims to benchmark case counts, observed rates, Wilson
  lower bounds, and disclosure duties: https://arxiv.org/abs/2605.25052
- RAGVUE (EACL 2026) decomposes RAG evaluation into retrieval quality, answer
  relevance/completeness, strict claim-level faithfulness, and judge calibration.
  RDLLM-L63 uses the same decomposition principle for deployable source footers:
  claim confidence, footer confidence, and payout-participation confidence are
  separate public rows: https://aclanthology.org/2026.eacl-demo.35/
- GhostCite (arXiv, 6 February 2026) studies citation validity at scale and reports
  model hallucination rates and human-review gaps around fabricated references.
  RDLLM maps this into verifier-readable citation fields, footer contracts, source
  availability snapshots, and release blocking instead of relying on human-visible
  bibliography text: https://arxiv.org/abs/2602.06718
- Source or It Didn't Happen / CiteTracer (arXiv, 9 May 2026) reframes citation
  hallucination detection as field-level adjudication rather than a binary
  found/not-found check. RDLLM maps that into typed verifier rows, citation-footer
  contracts, source-availability reports, and counterevidence adjudication so
  source rows can fail for specific, auditable reasons:
  https://arxiv.org/abs/2605.08583
- A Human-Centric Framework for Data Attribution in LLMs (arXiv v2, 8 May 2026)
  argues that attribution design depends on stakeholder objectives and domain
  criteria. RDLLM maps those negotiated objectives into policy, public footer,
  selective disclosure, and settlement artifacts: https://arxiv.org/abs/2602.10995

## Late-2025 to May-2026 Attribution Scan

This pass focused on papers and standards that affect the exact question the
mechanism must prove: not only who should be paid, but which source material the
model relied on, whether the visible citation is faithful, and whether retrieved
source text was safely treated as data.

- Correctness is not Faithfulness in Retrieval Augmented Generation Attributions
  (ICTIR 2025) distinguishes citation correctness from citation faithfulness and
  reports that plausible citations can be post-rationalized rather than genuinely
  used. RDLLM-L60, L61, and L62 respond by proving pre-generation context
  presence, source-boundary integrity, and decision provenance before or at
  release:
  https://doi.org/10.1145/3731120.3744592
- Source Attribution in Retrieval-Augmented Generation (arXiv, July 2025) adapts
  Shapley-style attribution to identify influential retrieved documents in RAG,
  but notes that repeated LLM utility evaluations are expensive. RDLLM uses this
  as support for a two-channel design: runtime source proof for user trust and
  sampled counterfactual/Shapley evidence for payout weighting:
  https://arxiv.org/abs/2507.04480
- CiteGuard (arXiv v4, April 2026; ACL 2026) reframes citation evaluation as
  citation-attribution alignment and uses retrieval-aware validation rather than
  trusting LLM-as-judge alone. RDLLM maps this into source verification,
  source-confidence reports, and citation-footer contracts:
  https://arxiv.org/abs/2510.17853
- RAGOrigin / Who Taught the Lie? (arXiv, September 2025; IEEE S&P 2026) treats
  poisoned RAG output as a responsibility-attribution problem and assigns scores
  to candidate texts using retrieval ranking, semantic relevance, and influence on
  the generated response. RDLLM-L64 maps this into source-authenticity rows that
  must bind a footer source to origin evidence and low poisoning risk before direct
  payout:
  https://arxiv.org/abs/2509.13772
- Poisoned-MRAG (arXiv, March 2025) shows that a small number of malicious
  image-text pairs can steer multimodal RAG outputs, and M3Att (arXiv, May 2026;
  ACL 2026) shows query-agnostic poisoning in medical multimodal RAG using covert
  misinformation and visual triggers. RDLLM-L64 therefore treats source
  authenticity as a first-class gate across text and media, not as a cosmetic URL
  check:
  https://arxiv.org/abs/2503.06254
  https://arxiv.org/abs/2605.10253
- Attribution Techniques for Mitigating Hallucinated Information in RAG Systems
  (arXiv, January 2026) surveys attribution methods across RAG hallucination
  classes. RDLLM reflects the same separation by splitting source availability,
  evidence sufficiency, counterevidence, claim coverage, and context closure into
  independent artifacts: https://arxiv.org/abs/2601.19927
- MaxShapley (arXiv v2, May 2026) targets incentive-compatible generative search
  compensation by computing fair context attribution more efficiently than exact
  Shapley. RDLLM uses the same economic direction but requires public proof
  artifacts before settlement so compensation does not rely on an opaque score:
  https://arxiv.org/abs/2512.05958
- LoRIF (arXiv v2, May 2026) makes gradient-based training data attribution more
  practical at large scale by reducing storage and query-time overhead. RDLLM
  treats these model-internal signals as useful training-value evidence, but keeps
  them separate from response-time source proof and visible footer grounding:
  https://arxiv.org/abs/2601.21929
- Mechanistic Data Attribution (arXiv, January 2026) traces interpretable LLM
  units back to training samples with influence functions and validates causal
  effects through interventions. RDLLM maps this to provider-private model-signal
  reports and training-content summaries rather than claiming deterministic
  event-level royalties from base-model memory alone:
  https://arxiv.org/abs/2601.21996
- Indirect Prompt Injection in the Wild (arXiv, April 2026) analyzes 1.2B URLs
  and finds validated machine-targeted prompt injections across webpages and HTTP
  responses. RDLLM-L61 maps that risk into source boundary telemetry and verifier
  checks that prove retrieved content was evidence-only:
  https://arxiv.org/abs/2604.27202
- ARGUS (arXiv, May 2026) constructs an influence provenance graph for LLM-agent
  decisions and reports strong reductions in context-aware prompt-injection
  success. RDLLM-L62 applies the same provenance-auditing direction to source
  attribution: claim, footer, payout, and release decisions must expose authorized
  influence edges rather than merely displaying citations:
  https://arxiv.org/abs/2605.03378
- AuthGraph (arXiv, May 2026) compares execution provenance against a clean
  authorization graph to detect tool and parameter-source deviations. RDLLM-L62
  uses the analogous separation for royalties: retrieved source text may justify
  evidence, but policy and payout participation must come from explicit license,
  accounting, boundary, and release-gate proof channels:
  https://arxiv.org/abs/2605.26497
- AIP: Subverting Retrieval-Augmented Generation via Adversarial Instructional
  Prompt (EMNLP 2025) shows that trusted instructional prompts can be weaponized
  to alter RAG behavior. RDLLM-L61 therefore binds not only source packets but also
  the boundary profile that separates source data from control, instruction,
  attribution, and payout channels: https://arxiv.org/abs/2509.15159
- OWASP LLM01:2025 identifies direct and indirect prompt injection as a primary
  LLM application risk and recommends segregating external content. RDLLM-L61
  converts that recommendation into a signed, replayable source-boundary artifact:
  https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- TREC 2025 RAG evaluates attribution-rich answers using response completeness,
  attribution verification, and agreement analysis. RDLLM treats this as evidence
  that attribution quality must be benchmarked and published, not just asserted:
  https://pages.nist.gov/trec-browser/trec34/rag/proceedings/
- C2PA Technical Specification 2.2 and W3C PROV-O remain relevant interoperability
  anchors for provenance metadata and graph-shaped lineage. RDLLM uses analogous
  signed claims, content hashes, and provenance edges for AI response proof packs,
  while the 2026 C2PA security analysis reinforces why high-stakes use needs
  independent verification beyond metadata presence alone:
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
  https://www.w3.org/TR/prov-o/
  https://arxiv.org/abs/2604.24890
- Probing for Knowledge Attribution in LLMs (arXiv v2, 27 May 2026) separates
  context-use errors from internal-knowledge errors and shows that hidden-state
  probes can identify dominant knowledge source. RDLLM does not require hidden
  states in the reference implementation, but the trace exchange gives providers a
  stable place to attach model-internal attribution signals:
  https://arxiv.org/abs/2602.22787
- DATE-LM (arXiv, July 2025) proposes data attribution evaluation for language
  models. RDLLM uses that lesson operationally: attribution evidence has to be
  scoreable, but it also has to flow into receipts, statements, transitive reports,
  and now clearinghouse settlement rows:
  https://arxiv.org/abs/2507.09424
- Large-Scale Training Data Attribution with Efficient Influence Functions
  (ICLR 2025 submission, modified February 2025) frames training data attribution
  as useful for data citation, curation, and debugging. RDLLM keeps that as a
  training-value signal while requiring runtime source proof and separate
  settlement proof before creators are paid:
  https://openreview.net/forum?id=jZw0CWXuDc
- C2PA's technical specification and conformance program make content credentials
  portable across media supply chains. RDLLM maps that portability idea to AI text
  by binding output hashes, response envelopes, copy markers, transitive reports,
  and clearinghouse settlement artifacts:
  https://c2pa.org/specifications/specifications/2.2/index.html
- Verifiable Provenance and Watermarking for Generative AI (arXiv, 20 May 2026)
  combines cryptographic provenance, watermarking, and zero-knowledge attestation
  under a laundering and forgery threat model. RDLLM applies the same evidentiary
  stance to generated answers: provenance signatures are necessary, but high-level
  answer release also needs source availability, sufficient evidence,
  counterevidence adjudication, and trust-root verification:
  https://arxiv.org/abs/2605.21002
- RLVR Datasets and Where to Find Them (arXiv, 26 May 2026) documents provenance
  collapse in reasoning-training datasets and attributes more than 99% of a large
  RLVR corpus back to atomic sources. RDLLM's registry, trace exchange, and
  training-value channels are designed so derived datasets do not erase upstream
  source identity: https://arxiv.org/abs/2605.26971
- Tracing the Roots (arXiv, April 2026) introduces data lineage for post-training
  LLM datasets and reconstructs dataset-evolution graphs. RDLLM-L24 turns that
  lineage idea into settlement logic: derivative works carry upstream edges and
  pass-through royalty obligations: https://arxiv.org/abs/2604.10480
- Provable Model Provenance Set for LLMs (arXiv, February 2026) argues that model
  provenance claims need coverage guarantees across multiple possible sources,
  not heuristic single-source labels. RDLLM-L91 maps that concern into declared
  training-lineage reports, while RDLLM-L92 maps it into black-box provenance-set
  challenge reports for undisclosed derivative models:
  https://arxiv.org/abs/2602.00772
- Model Provenance Testing for LLMs (arXiv, February 2025) shows that derived
  models preserve statistically detectable output similarities under black-box
  API access. RDLLM-L92 operationalizes that into baseline-calibrated candidate
  model provenance sets and settlement challenges:
  https://arxiv.org/abs/2502.00706
- TextSeal (arXiv, May 2026) introduces localized watermarking whose signal can
  transfer through distillation, while VOW (arXiv, April 2026) adds verifiable
  oblivious watermark detection. RDLLM-L92 treats watermark evidence as one
  auditable signal, never as the only basis for payout:
  https://arxiv.org/abs/2605.12456 and https://arxiv.org/abs/2604.27666
- Behavioral Fingerprint via Refusal Vectors (arXiv, February 2026) and
  text-preserving fine-tune provenance auditing (arXiv, October 2025) show that
  derivative models can carry behavioral or document-level traces even when
  weights and training data are hidden. RDLLM-L92 combines those signals with
  multiple-testing controls and source-row settlement:
  https://arxiv.org/abs/2602.09434 and https://arxiv.org/abs/2510.09655
- Where does output diversity collapse in post-training? (arXiv, April 2026)
  shows that data composition can embed downstream behavior changes in model
  weights. RDLLM-L91 treats fine-tuning and distillation lineage as an ongoing
  attribution and settlement surface rather than a one-time dataset note:
  https://arxiv.org/abs/2604.16027
- Tracing the Data Trail (arXiv, January 2026) surveys LLM data provenance,
  transparency, and traceability. RDLLM maps those axes into source-access traces,
  training summaries, lineage reports, and public proof surfaces:
  https://arxiv.org/abs/2601.14311
- The TREC 2025 RAG Track overview (arXiv, 10 March 2026) evaluates systems on
  relevance, response completeness, attribution verification, and agreement
  analysis. RDLLM maps those evaluation dimensions into source footers, answer
  provenance cards, source verification reports, and response envelopes:
  https://arxiv.org/abs/2603.09891
- Who Benefits from RAG? (arXiv, 25 March 2026) separates group exposure, utility,
  and attribution, showing that fair source treatment requires more than retrieval
  frequency. RDLLM maps that distinction into source-access traces, provenance
  benchmarks, and counterfactual influence reports:
  https://arxiv.org/abs/2603.24218
- Counterfactual Reasoning for Retrieval-Augmented Generation (ICLR 2026) argues
  that RAG systems must distinguish causally decisive evidence from correlated but
  misleading evidence. RDLLM-L26 operationalizes that idea by removing each
  credited work and replaying the attribution path:
  https://openreview.net/forum?id=9U51rOnGko
- Beyond Semantic Relevance (arXiv, 2 May 2026) proposes counterfactual risk
  minimization for RAG and argues that semantic relevance can fail as a proxy for
  utility. RDLLM uses source-ablation reports as an audit artifact for the same
  distinction:
  https://arxiv.org/abs/2605.01302
- Source Attribution in Retrieval-Augmented Generation (arXiv, July 2025) adapts
  Shapley-style document attribution for RAG and studies lower-cost
  approximations. RDLLM uses a deployment-friendly replay layer: benchmark reports
  test source ranking, while counterfactual reports test source influence for
  individual paid events:
  https://arxiv.org/abs/2507.04480
- VISA (ACL 2025) introduces visual source attribution for RAG and localizes
  supporting evidence in the original document view with bounding boxes. RDLLM maps
  that requirement into media attribution reports and footer rows that can carry
  text spans, perceptual-hash commitments, source regions, and rendered evidence
  pointers instead of treating attribution as prose-only:
  https://aclanthology.org/2025.acl-long.1456/
- Ask in Any Modality (arXiv, February 2025), MAVIS (AAAI 2026), and MiRAGE
  (arXiv, October 2025) show that source attribution cannot remain text-only when
  models retrieve and generate from images, audio, video, and mixed documents.
  RDLLM-L27 adds a media attribution report with content hashes, perceptual-hash
  commitments, descriptor-hash commitments, ranked match scores, payouts, and
  unattributed-media escrow:
  https://arxiv.org/abs/2502.08826
  https://ojs.aaai.org/index.php/AAAI/article/view/40585
  https://arxiv.org/abs/2510.24870
- Verifying Provenance of Digital Media (arXiv, April 2026) warns that C2PA-style
  content provenance should not be treated as sufficient for high-stakes media
  trust by itself. RDLLM uses provenance metadata as an input but requires private
  replay, hash roots, payout conservation, escrow, and signed verifier artifacts:
  https://arxiv.org/abs/2604.24890
- Toward Accountable AI-Generated Content on Social Platforms (arXiv, April 2026)
  studies signed identifiers and multimodal attribution verification for generated
  imagery. RDLLM uses the same accountability direction but makes the payout and
  escrow ledger explicit:
  https://arxiv.org/abs/2604.10460
- The Attribution Contract (arXiv, 21 May 2026) argues that generative-model
  attribution must name the output being explained, eligible features, assumed
  generation process, held-fixed values, and attributed score. RDLLM-L28 now embeds
  that contract directly in model-signal reports:
  https://arxiv.org/abs/2605.23080
- Probabilistic Attribution for Large Language Models (arXiv, 20 May 2026) uses
  next-token log-probabilities to infer token influence in a model-agnostic way.
  RDLLM maps that idea into a `logprob_delta` signal channel rather than treating
  citation labels as the only evidence of source use:
  https://arxiv.org/abs/2605.21726
- Explaining the Reasoning of Large Language Models Using Attribution Graphs
  (arXiv, December 2025) argues that generated tokens influence later generated
  tokens through a causal graph, improving context attribution faithfulness. RDLLM
  uses this as a reason to keep model-signal attribution separate from public
  footer citations:
  https://arxiv.org/abs/2512.15663
- Cited but Not Verified (arXiv, May 2026) shows that link validity and topical
  relevance can coexist with much lower factual support in deep-research reports.
  RDLLM therefore keeps source materialization and answer provenance verification
  as public artifacts:
  https://arxiv.org/abs/2605.06635
- DAVinCI (arXiv, 23 April 2026) introduces a dual attribution and verification
  framework that attributes generated claims to internal model components and
  external sources, then verifies them with entailment reasoning and calibrated
  confidence. RDLLM-L40 maps that idea into a product surface: the exact footer
  rows and claim anchors shown to users must be verified before display, and
  RDLLM-L41 adds a private audit challenge for the redacted evidence behind those
  rows:
  https://arxiv.org/abs/2604.21193
- CiteVQA (arXiv, May 2026) introduces Strict Attributed Accuracy, crediting an
  answer only when both the answer and evidence region are correct, and reports
  attribution hallucination in current document models. RDLLM's source verification,
  media attribution, and model-signal layers target the same answer-plus-evidence
  requirement:
  https://arxiv.org/abs/2605.12882
- TRACER (arXiv, 11 May 2026) frames multimodal tool-using agents as having a
  provenance gap: tool trajectories and final answers do not say which observation
  supports which generated claim. RDLLM-L33 maps that concern to cross-provider
  runtime use: a downstream agent must verify the upstream provider's source-footer
  relay, escrow relay, artifact hashes, and downgrade policy before consuming the
  generated result:
  https://arxiv.org/abs/2605.09934
- The Attribution Crisis in LLM Search Results (Data & Policy, published 28 April
  2026) measures a gap between relevant URLs consumed and URLs cited in real-world
  search-enabled LLM conversations. RDLLM-L34 directly targets the portability side
  of that gap by making the output hash and proof-chain pointer travel with copied
  answers:
  https://www.cambridge.org/core/journals/data-and-policy/article/attribution-crisis-in-llm-search-results-estimating-ecosystem-exploitation/170DD0B88E5F5AEA8F69F2E9AF1328E3
- VeriCite (arXiv, October 2025) verifies generated claims, selects supporting
  evidence, and refines answers around evidence. RDLLM hardens the same pattern by
  hashing claim evidence spans and binding them into receipts and answer cards:
  https://arxiv.org/abs/2510.11394
- SAFE (arXiv v2, September 2025) emphasizes sentence-level in-generation
  attribution so users can verify sentences while reading. RDLLM's answer card and
  source verification report provide the public proof surface for that level of
  granularity: https://arxiv.org/abs/2505.12621
- FRAMES (NAACL 2025) shows that end-to-end RAG must evaluate factuality,
  retrieval, and reasoning together rather than as isolated modules. RDLLM keeps
  retrieval traces, claim support, grounding quality, and payout evidence as
  cross-checking artifacts: https://aclanthology.org/2025.naacl-long.243/
- Mechanistic Data Attribution (arXiv, 29 January 2026) uses influence functions to
  trace interpretable model units back to training samples. RDLLM treats such
  mechanistic evidence as a future provider signal that can be committed in receipt
  telemetry without replacing runtime source evidence: https://arxiv.org/abs/2601.21996
- The European Commission's GPAI guidance requires copyright policies and public
  training-content summaries for general-purpose AI models. It says providers must
  identify and respect rights reservations, and that summaries help rightsholders
  assess whether lawful text and data mining conditions were respected. RDLLM-L29
  turns that lifecycle requirement into a replayable changed-rights report:
  https://digital-strategy.ec.europa.eu/en/faqs/guidelines-obligations-general-purpose-ai-providers
- IPTC's Generative AI Opt-Out Best Practices recommend visible reservations,
  metadata declarations, robots/TDMRep/trust.txt signals, and asset-level metadata
  while warning that declaration protocols do not guarantee crawler compliance.
  RDLLM-L29 adds the missing provider-side proof that those rights changes were
  actually enforced after ingestion:
  https://iptc.org/wp-content/uploads/2025/05/IPTC-Generative-AI-Opt-Out-Best-Practices.pdf
- C2PA 1.3 defines a Training and Data Mining assertion for AI training,
  generative training, inference, and data-mining use states. RDLLM treats these
  asset-level signals as inputs to a broader text-and-media rights manifest, then
  requires remediation reports when those policy states change:
  https://c2pa.org/specifications/specifications/1.3/specs/_attachments/C2PA_Specification.pdf
- The Attribution Crisis in LLM Search Results (Data & Policy, 2026) argues that
  commercial LLMs need transparent search telemetry covering query, retrieval,
  reranking, and citation, and notes that OpenTelemetry GenAI conventions can carry
  source IDs and scores. RDLLM-L13 implements that bridge as a verifiable trace
  exchange: https://doi.org/10.1017/dap.2026.10064
- OpenTelemetry GenAI semantic conventions define provider-neutral attributes for
  GenAI spans, including data-source IDs and structured retrieval documents. RDLLM
  aligns source-access spans with those conventions while adding royalty-specific
  commitments: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
- C2PA's January 2026 clarification states that Content Credentials record
  provenance and authenticity, not text-and-data-mining permissions. RDLLM keeps
  provenance, rights policy, and settlement as separate but linked artifacts:
  https://c2pa.ai/news/tdm-clarification
- W3C ODRL, C2PA provenance, SCITT transparency receipts, and EU GPAI copyright
  obligations point to a common deployment boundary: rights state cannot be a
  static registry field. RDLLM-L118 therefore adds an SLA-bound propagation audit
  proving that opt-outs, revocations, lease expiry, and license changes reached
  retrieval indexes, access leases, license transactions, source footers,
  persistent memory, private reasoning, post-training signals, attribution
  exchanges, downstream notices, and settlement before future direct use:
  https://www.w3.org/TR/odrl-model/
  https://c2pa.org/specifications/specifications/2.2/index.html
  https://www.rfc-editor.org/rfc/rfc9943.html
  https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai
- OpenAI's May 2026 provenance update shows frontier providers moving toward
  multi-layer provenance, C2PA conformance, durable watermarking, and public
  verification tooling. RDLLM extends that ecosystem pattern from AI-origin
  detection to source attribution, royalty settlement, provider attribution cards,
  and assurance bundles: https://openai.com/index/advancing-content-provenance/
- Nature Machine Intelligence's March 2025 editorial on training-data transparency
  argues that resolving generative-AI copyright disputes starts with knowing which
  copyrighted data were used and where they entered the training pipeline. RDLLM
  converts that transparency goal into signed source registries, training-data
  summaries, source-footed responses, and provider-level discovery manifests:
  https://www.nature.com/articles/s42256-025-01023-9
- Samuelson's forthcoming PNAS paper on collective licensing for generative-AI
  training data emphasizes the normative, economic, and operational difficulty of
  compensating rightsholders at scale. RDLLM-L46 responds by separating policy
  choices from proof mechanics: providers can adopt licensing, statutory, pool, or
  marketplace regimes while still publishing conserved revenue-allocation evidence:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6051014
- Peukert's September 2025 economics paper argues that royalties can help sustain
  fresh creative supply only if coverage is broad and administrative cost stays
  low. RDLLM-L46 therefore keeps allocation modes explicit, machine-verifiable, and
  hash-only for private billing fields, so creators can audit totals without
  forcing every provider into the same business model:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5532959
- PrivaRisk (Journal of Information Security and Applications, July 2025) and PrivChain-AI (Scientific Reports,
  December 2025) both point at the same finance-audit pattern: sensitive financial
  data should remain private while commitments, hashes, and authorized audit paths
  prove consistency. RDLLM-L47 applies that pattern to AI royalty finance exports:
  creators can verify that revenue pools reconcile without seeing customer records:
  https://www.sciencedirect.com/science/article/pii/S2214212625001310
  https://www.nature.com/articles/s41598-025-32606-6
- CiteCheck (arXiv, 26 May 2026) verifies both whether a citation maps to a real
  scholarly work and whether metadata is faithful to that work. RDLLM uses the same
  philosophy at response time: source labels, claim-support spans, and footer
  entries must resolve to registered, hash-bound sources rather than model-written
  citation strings: https://arxiv.org/abs/2605.27700
- CiteAudit (arXiv v3, 1 May 2026) decomposes scientific citation verification into
  metadata extraction, retrieval, passage matching, reasoning, and calibrated
  judgment. RDLLM mirrors that decomposition by separating source materialization,
  claim-support spans, source quality, and certification failure modes:
  https://arxiv.org/abs/2602.23452
- Correctness is not Faithfulness in RAG Attributions (ICTIR 2025) shows why a
  citation can support a statement yet still be post-rationalized rather than the
  source the model genuinely relied on. RDLLM keeps corroborative source footers,
  contributive influence evidence, and independent audit attestation as separate
  proof channels:
  https://repository.tudelft.nl/record/uuid:bab4a12e-455b-49ea-bdf8-7f6a88478f60
- User-Centric Evidence Ranking (EACL 2026) argues that attribution systems should
  rank sufficient evidence early enough for humans to verify efficiently, instead
  of dumping redundant snippets. RDLLM maps that into visible source footers,
  support scores, claim-span hashes, and answer provenance cards:
  https://aclanthology.org/2026.eacl-long.340/
- SciTrue (EACL 2026) provides source-level accountability and evidence traceability
  for scientific claim verification, linking claim components to explicit sources
  that users can inspect and challenge. RDLLM generalizes that requirement beyond
  science through source verification reports and challenge-correction reports:
  https://aclanthology.org/2026.eacl-demo.27/
- SCITT/RFC 9943, RFC 9162 Certificate Transparency, Rekor, transparency-dev
  witness, in-toto, and the C2PA
  conformance program show that public verification ecosystems converge on signed
  statements, append-only Merkle logs, inclusion proofs, attestation subjects, and
  conformance evidence. Witness cosigning adds the missing anti-equivocation
  control: a log checkpoint should be rejected if an independent quorum has not
  seen the same checkpoint view. RDLLM-L18 turns the attribution proof pack into that kind
  of assurance bundle, RDLLM-L45 adds an independent audit attestation over the
  full public proof pack, RDLLM-L49 adds ongoing publication checkpoints, and
  RDLLM-L50 adds witness quorum and split-view detection over those checkpoints:
  https://www.rfc-editor.org/rfc/rfc9943.html
  https://www.rfc-editor.org/rfc/rfc9162.html
  https://docs.sigstore.dev/logging/overview/
  https://pkg.go.dev/github.com/transparency-dev/witness
  https://github.com/in-toto/attestation
  https://opensource.contentauthenticity.org/docs/conformance/
- Sovereign Context Protocol (arXiv, March 2026) proposes an attribution-aware
  runtime access layer where every creator-content access is logged, licensed, and
  attributable. RDLLM's source-access trace and provider card make the same adoption
  pressure auditable across receipts, ledgers, and certification reports:
  https://arxiv.org/abs/2603.27094
- Cited but Not Verified (arXiv, 7 May 2026) shows that strong models can maintain
  high link validity and relevance while factual accuracy against cited sources
  remains much lower. RDLLM therefore reports citation integrity, fact support, and
  provider-level coverage as separate fields: https://arxiv.org/abs/2605.06635
- CiteCheck (arXiv, 26 May 2026) verifies whether generated scientific citations
  correspond to real scholarly works and faithful metadata, using retrieval and
  calibrated exact/minor/major labels. RDLLM maps that into source-confidence rows,
  citation-footer contracts, and verifier failure modes for metadata drift:
  https://arxiv.org/abs/2605.27700
- LLM hallucinations in the wild (arXiv, 8 May 2026) audits 111 million references
  and estimates 146,932 hallucinated citations in 2025 alone. RDLLM treats source
  identity and claim support as machine-checkable obligations rather than trust in
  model-written references: https://arxiv.org/abs/2605.07723
- MAVIS (AAAI 2026) shows that source attribution is already moving beyond text:
  multimodal systems need fact-level citations across visual and text documents.
  RDLLM-L27 declares multimodal source attribution support explicitly through a
  media attribution report instead of implying unimplemented coverage:
  https://doi.org/10.1609/aaai.v40i39.40585
- PaperTrail (arXiv, 24 February 2026) argues that document-level citations are not
  granular enough for scholarly verification and studies claim-evidence mappings.
  RDLLM therefore exposes public claim-support metadata, evidence span hashes, and
  private audit challenges for the redacted evidence text behind those hashes:
  https://arxiv.org/abs/2602.21045
- Efficient and Scalable Provenance Tracking for LLM-Generated Code Snippets
  (arXiv, May 2026) combines vector search and fingerprinting to trace generated
  code snippets back to likely source snippets. RDLLM treats code as another
  content class that needs the same source footer, license, and audit-challenge
  machinery as prose: https://arxiv.org/abs/2605.28510
- Concept Influence (arXiv, 16 February 2026) attributes behavior to semantic
  directions rather than only individual examples. RDLLM keeps runtime source
  attribution, training-value priors, and future model-internal influence evidence
  as separate ledger channels: https://arxiv.org/abs/2602.14869
- CUE-R (arXiv, April 2026) emphasizes intervention-style utility for individual
  retrieved evidence items in multi-step RAG. RDLLM's attribution-gap report treats
  every accessed item as an accountable object: https://arxiv.org/abs/2604.05467
- Source Attribution in RAG (arXiv, July 2025) applies Shapley-style attribution to
  retrieved documents but highlights LLM-call cost. RDLLM uses deterministic local
  weights by default and leaves room for Shapley/SHAP evidence as a higher-cost
  production signal: https://arxiv.org/abs/2507.04480
- CiteGuard (arXiv, October 2025) treats citation evaluation as citation-attribution
  alignment and uses retrieval-aware validation. RDLLM makes that alignment
  machine-checkable through footer labels, claim support, and receipt verification:
  https://arxiv.org/abs/2510.17853
- CiteAudit (2026): builds a benchmark and multi-stage verification pipeline for
  hallucinated scientific references, reinforcing RDLLM's split between citation
  identity, metadata fidelity, and claim support.
- User-Centric Evidence Ranking (EACL 2026): evaluates evidence ordering for
  attribution and fact verification, supporting RDLLM's choice to expose ranked
  source/support facts rather than opaque citation markers.
- SciTrue (EACL 2026): demonstrates source-level accountability and traceability
  for scientific claim verification, supporting RDLLM's source-materialization and
  creator-challenge layers.
- Correctness is not Faithfulness in RAG Attributions (arXiv, December 2024) shows
  that citation correctness alone is not enough; citations can be correct-looking
  but unfaithful to actual model use. RDLLM therefore records source-access traces
  separately from visible citations: https://arxiv.org/abs/2412.18004
- OLMoTrace (arXiv, April 2025) demonstrates real-time tracing from model output
  segments to massive training corpora for verbatim matches. RDLLM turns that class
  of output-to-training evidence into a receipt field and settlement signal:
  https://arxiv.org/abs/2504.07096
- W3C Verifiable Credentials Data Model v2.0 defines selective disclosure as
  fine-grained holder control and defines tamper-evident credentials and
  presentations. RDLLM's VC-shaped interop layer follows that portability pattern:
  https://www.w3.org/TR/vc-data-model/
- IETF RFC 9901 SD-JWT specifies issuer-signed JSON claims plus selected
  disclosures, digest verification, and salt entropy requirements. RDLLM's
  disclosure package mirrors those properties with per-path salts and root
  commitments: https://www.ietf.org/ietf-ftp/rfc/rfc9901.pdf
- W3C Data Integrity BBS Cryptosuites v1.0 targets selective disclosure and
  unlinkable derived proofs. RDLLM's current hash-based package is deliberately
  migration-friendly toward BBS-style production credentials:
  https://www.w3.org/TR/vc-di-bbs/
- W3C Data Integrity 1.0 explains that selective disclosure requires capable
  cryptosuites and can reveal only parts of a signed message while preserving
  verifiability. RDLLM applies that principle to attribution receipts:
  https://www.w3.org/TR/vc-data-integrity/

## Papers and Relevance

- AIS, "Measuring Attribution in Natural Language Generation Models" (2023):
  defines attribution to identified sources as an evaluation target for generated
  statements.
- ALCE, "Enabling Large Language Models to Generate Text with Citations" (2023):
  evaluates citation quality alongside correctness and fluency, and shows citation
  support remains incomplete in long-form generation.
- RAGChecker (2024): argues for fine-grained diagnostics across retrieval and
  generation modules.
- RECLAIM, "Ground Every Sentence" (NAACL 2025): generates sentence-level citations
  through interleaved reference-claim generation.
- Think&Cite (ACL 2025): treats attributed text generation as a search problem and
  scores both generation progress and attribution progress.
- FRAMES (NAACL 2025): evaluates factuality, retrieval, and reasoning together for
  end-to-end RAG, showing that attribution belongs in the full task pipeline.
- VeriCite (2025): validates claims and supporting evidence before answer
  refinement, reinforcing claim-level verification.
- Source Attribution in RAG (2025): explores Shapley-style attribution for retrieved
  documents and highlights cost constraints.
- VISA (ACL 2025): localizes visual source evidence in document views, reinforcing
  that attribution must cover images, scanned PDFs, figures, screenshots, and
  multimodal source regions as well as plain text spans.
- SAFE (2025): classifies generated sentences before attribution so systems can
  decide whether a sentence needs no citation, one quote, or multiple quotes.
- OLMoTrace (2025): traces language model outputs to verbatim matches across very
  large training corpora, showing why runtime output-to-training provenance tools
  are becoming practical for open-data models.
- What Is Your Data Worth to GPT? (NeurIPS 2025, revised 2026): scales
  influence-function data valuation to recent LLMs and large training sets.
- DATE-LM (NeurIPS 2025): benchmarks data-attribution methods across training data
  selection, toxicity/bias filtering, and factual attribution, and reports that
  attribution methods have task-specific trade-offs rather than one universal winner.
- RISE (2026): compresses LLM influence evidence for retrospective attribution and
  prospective data valuation, reinforcing RDLLM's choice to expose model-native
  evidence as an auditable signal rather than a hidden payout oracle.
- Cited but Not Verified (2026): evaluates deep-research citations by checking
  link validity, topical relevance, and factual support against the actually cited
  content; it shows that surface citation quality can mask weak factual grounding.
- SourceBench (2026): scores cited web sources across relevance, factual accuracy,
  objectivity, freshness, authority/accountability, and clarity, reinforcing the
  need to score source quality separately from answer quality.
- LegalCiteBench (2026): shows that closed-book legal citation generation remains
  brittle and that concrete but incorrect authorities are a high-risk failure mode.
- Dependable RAG with factual confidence prediction (2026): argues for confidence
  measures around whether retrieved chunks support generated answers.
- DataDignity (2026): frames output auditing as pinpoint
  provenance, ranking candidate documents that best support a response.
- Probabilistic Attribution for LLMs (2026): attributes tokens through
  next-token probability inversions and entropy, reinforcing the need to expose
  uncertainty and token sensitivity separately from royalty splits.
- A Human-Centric Framework for Data Attribution in LLMs (2026): connects
  attribution methods to stakeholder objectives, negotiation, and sustainable
  creator incentives.
- Mechanistic Data Attribution (2026): traces interpretable LLM units back to
  training samples with influence-style methods, reinforcing that training-origin
  evidence and runtime citation evidence should be represented separately.
- DebugLM (2026): proposes training data provenance tags that trace model behavior
  to responsible datasets and enable source-specific remediation.
- Generation-Time vs. Post-hoc Citation (NeurIPS 2025 workshop): finds a practical
  trade-off between citation coverage and correctness, and recommends
  retrieval-centric post-hoc citation for many high-stakes applications.
- The Attribution Crisis in LLM Search Results (2025): documents a gap between web
  pages consumed by LLM search systems and sources credited to users.
- Document Overlap Is Not Evidence Continuity (ACL EvalEval 2026 submission):
  shows that document-level citation overlap can hide span-level turnover, motivating
  exact span hashes in audits.
- CiteGuard (arXiv 2025): validates citation attribution through retrieval-aware
  checking rather than relying only on LLM-as-judge.
- C2-Cite (2026): makes citation markers active knowledge pointers aligned to
  retrieved content.
- MedRAGChecker (2026): decomposes biomedical answers into atomic claims and checks
  evidence support.
- LUMINA (ICLR 2026): shows RAG can still hallucinate when the model underuses
  external context or overuses internal knowledge.
- MAVIS (AAAI 2026): extends source attribution to multimodal long-form VQA with
  fact-level citations.
- Samuelson (PNAS forthcoming, 2026 posting) and Peukert (SSRN 2025): show why
  compensation mechanisms need collective, statutory, or market-compatible revenue
  proof rather than only one-off permission or model-level claims.
- LLM hallucinations in the wild (2026): demonstrates that fabricated citations are
  entering scholarly corpora at scale.
- CiteTracer / Source or It Didn't Happen (arXiv, May 2026): reframes citation
  hallucination detection as field-level adjudication with a taxonomy of real,
  potential, and hallucinated citation errors, reinforcing RDLLM's typed source
  footers and verifier-readable citation metadata.

## Standards and Policy Signals

- W3C ODRL 2.2 defines a rights language for permissions, prohibitions, duties, and
  constraints over content and services: https://www.w3.org/TR/odrl-model/
- MLCommons Croissant 1.1 adds machine-actionable provenance and structured usage
  policies for automated consent and licensing enforcement:
  https://docs.mlcommons.org/croissant/docs/croissant-spec-1.1.html
- SPDX 3.0.1 includes Dataset and AI profiles with hashes, intended use, limitations,
  and bill-of-materials relationships: https://spdx.github.io/spdx-spec/v3.0.1/
- The EU AI Act Article 53 requires GPAI providers to maintain a copyright policy
  and publish a sufficiently detailed summary of training content:
  https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- The European Commission's 2026 FAQ says the public training-content template is
  mandatory under Article 53(1)(d), with updates generally required at six-month
  intervals or sooner for material changes:
  https://digital-strategy.ec.europa.eu/en/faqs/template-general-purpose-ai-model-providers-summarise-their-training-content
- C2PA clarified in January 2026 that Content Credentials are for provenance and
  authenticity, not TDM opt-out or AI-training preferences; RDLLM therefore treats
  C2PA-style provenance as complementary to ODRL/Croissant-style rights metadata:
  https://c2pa.ai/news/tdm-clarification
- The C2PA conformance program shows how provenance systems can move from
  specification to vetted product behavior:
  https://opensource.contentauthenticity.org/docs/conformance/
- IETF SCITT/RFC 9943 defines signed statements, transparency services, and
  verification roles for transparent digital supply chains:
  https://www.rfc-editor.org/rfc/rfc9943.html
- W3C Verifiable Credentials Data Model v2.0 is a W3C Recommendation for portable,
  proof-carrying claims and presentations:
  https://www.w3.org/TR/vc-data-model/
- OpenID Federation 1.0 defines a trust-chain and entity-statement pattern for
  cross-organization federation, which RDLLM maps to provider-scoped creator audit
  federation participants:
  https://openid.net/specs/openid-federation-1_0.html
- IETF RFC 9901 standardizes SD-JWT selective disclosure for JSON claims, including
  selected disclosures, digest verification, and salt-entropy security requirements:
  https://www.ietf.org/ietf-ftp/rfc/rfc9901.pdf
- W3C Data Integrity BBS Cryptosuites v1.0 describes selective disclosure and
  unlinkable derived proofs for VC data integrity:
  https://www.w3.org/TR/vc-di-bbs/
- W3C PROV defines a web provenance model built around entities, activities, agents,
  and relations, which RDLLM uses as the shape of answer-level provenance graphs:
  https://www.w3.org/TR/prov-overview/

## Implementation Changes Made

- The engine now stores `answer_text` separately from rendered `output`.
- Rendered output includes a `Sources` footer.
- Source references expose source labels, owners, work IDs, chunk IDs, source URIs,
  evidence quotes, hashes, support scores, and payout shares.
- Claim support is computed per sentence with a lightweight local verifier and now
  records supporting work IDs, chunk IDs, evidence text, character offsets, and span
  hashes.
- The event hash includes the answer text, rendered output, payout shares, source
  references, claim evidence spans, and grounding report.
- Audits verify source-reference hashes in addition to royalty-share hashes.
- Conformance now fails if a supported claim's evidence span hash is absent from the
  rendered footer.
- Rights policies are now first-class: allowed uses, prohibited uses, jurisdiction,
  minimum royalty rate, and revocation are enforced before payout.
- Receipts now include policy decisions, and conformance fails if receipt rights
  decisions drift from the ledger.
- The engine exports a rights manifest aligned with ODRL, Croissant, SPDX, and PROV
  vocabulary concepts.
- The `certify` command now emits an RDLLM-L0 through RDLLM-L186 report that tests
  grounded generation, external text attribution, escrow, rights blocking, receipt
  transparency, tamper detection, rights-manifest export, and grounding-quality
  scoring, registry dispute, escrow resolution, interoperability export,
  attribution-gap accountability, selective disclosure, trace exchange, and
  royalty-statement rollup, attribution-challenge correction, and provider-card
  verification, training-content-summary verification, assurance-bundle
  publication, answer-provenance-card verification, and source-materialization
  verification, response-envelope public verification, integration-profile
  contract verification, discovery-manifest publication, foundation-API
  attribution-profile verification, client-attribution-enforcement verification,
  persistent-memory-provenance verification,
  private-reasoning-attribution verification, post-training-signal-provenance verification,
  attribution-bom verification,
  creator-attribution-audit-index verification,
  creator-attribution-audit-federation verification,
  creator-audit-federation-transparency verification,
  derivative-lineage
  royalty verification, provenance-benchmark evaluation, counterfactual influence
  verification, multimodal media attribution verification, and model-internal
  signal attribution verification, rights-remediation verification, semantic
  text attribution verification, cross-provider attribution-exchange verification,
  portable conformance-vector verification, runtime federation-handshake
  verification, portable attribution-capsule verification, and response-release
  gate verification, proof-carrying-response verification, and serving-gateway
  verification, creator-license-contract verification, source-confidence
  verification, citation-footer-contract verification, private-audit-challenge
  verification, transitive-attribution-flow verification, and
  cross-provider-clearinghouse-settlement verification, verifiable-remittance
  verification, payment-execution attestation, payment-rail authenticity,
  creator-facing payout receipts, rendered-attribution-audit verification,
  training-memory provenance verification, and evidence-locked generation
  verification, emission evidence enforcement, live emission witness
  verification, live emission transparency verification, evidence-region binding
  verification, source-access lease verification, content-protocol ingestion
  verification, citation-reliance receipt verification, license-transaction
  receipt verification, grounded-source-footer verification, creator-audit
  federation verification, creator-audit federation transparency verification,
  source-freshness-audit verification, royalty-abuse-audit verification, and
  consent-revocation-propagation verification, citation URL-health verification,
  composite-foundation-adapter verification, foundation-provider-conformance
  verification, foundation-runtime-adapter verification, and
  foundation-runtime-router verification, and
  foundation-model-deployment-attestation verification, and
  universal-composition-receipt verification, and
  universal-composition-settlement verification, and
  universal-foundation-model-contract verification, and
  universal-invocation-guard verification, and
  universal-invocation-coverage verification, and
  universal-invocation-witness verification, universal-content-credential
  verification, universal-rdllm-passport verification, universal-adoption-standard
  verification, universal-interop-test-kit verification, and
  universal-context-provenance-bridge verification, and
  universal-citation-verification-contract verification, universal-grounded-reuse
  verification, universal-training-serving-contract verification,
  universal-confidential-attribution-audit verification, and
  universal-reliance-correction-ledger verification,
  universal-foundation-adoption-kernel verification, and
  universal-provider-adapter-harness verification, and
  universal-provider-drift-sentinel verification, and
  universal-attribution-negotiation-handshake verification, and
  universal-negotiated-invocation-enforcement verification, and
  universal-certification-trust-federation verification, and
  universal-foundation-provider-adoption-pack verification, and
  universal-industry-adoption-root verification, and
  universal-reference-implementation-distribution verification,
  universal-live-attribution-proof verification,
  universal-foundation-model-release-passport verification, and
  universal-composite-RDLLM-contract verification, and
  universal-foundation-provider-binding-matrix verification, and
  universal-provider-conformance-runner-receipt verification, and
  universal-production-invocation-admission verification, and
  universal-source-grounded-response-receipt verification. L158 turns static provider
  conformance into a continuously replayed drift control: provider API schemas,
  SDK response shapes, model aliases, streaming events, gateway transforms,
  citation locators, source-footer rendering, and settlement meters must keep
  matching the published RDLLM contract, or grounded display and creator payout
  release are revoked until remediation is published. L159 adds request-time
  negotiation: a client and provider route must agree on source footers, citation
  locators, claim provenance, model alias resolution, drift-sentinel status,
  telemetry, copy/export status links, privacy redaction, and settlement meters
  before generation, directly addressing recent findings that citation-looking
  output can remain unsupported unless source and metadata commitments are bound
  before answers are produced. L160 adds invocation enforcement: every actual
  SDK call, gateway proxy, stream, tool/MCP call, retrieval context, batch
  callback, fallback route, and cache reuse must bind an invocation receipt to
  the negotiated attribution contract before display or payout, aligning RDLLM
  with recent GenAI observability and citation-verification work that requires
  traceable calls and source-support metadata rather than self-asserted
  citations. L161 adds the portable trust-federation layer: attribution footers,
  invocation receipts, creator-settlement proofs, and anti-hallucination reliance
  signals must be certified through trust anchors, accredited conformance labs,
  trust marks, verifiable credentials, transparency inclusion, revocation status,
  and relying-party policy before a provider claim is treated as grounded rather
  than self-asserted. L162 turns that trust chain into a provider-neutral
  adoption pack: all hosted APIs, cloud gateways, OpenAI-compatible routers,
  local open-weight runtimes, and enterprise proxies must expose the same
  adapter evidence, standard exports, fail-closed invocation gates,
  source-footer delivery, telemetry mappings, copied-output status links,
  creator-audit paths, regulator exports, and settlement-release guards before
  attribution or anti-hallucination reliance can be claimed. The
  L117 layer adds platform-scale settlement integrity: source-farm, sybil,
  duplicate-source, reciprocal-boosting, undisclosed synthetic-source, and
  direct-payout concentration signals must route suspicious value to abuse-review
  escrow before direct payout. The L118 layer adds stale-rights prevention:
  revocation, opt-out, lease-expiry, and license-change events must propagate to
  source selection, footers, memory, private reasoning, post-training signals,
  attribution exchange, downstream notices, and settlement before future use or
  direct payout can continue. The L71 layer adds
  independent verifier quorum checks so direct settlement requires external
  signed replay agreement, not only provider-produced proof. The L72 layer adds
  bonded verifier accountability: accepted verifier attestations must bind to
  active trust-registry identities, non-revoked key hashes, slashable bond rows,
  conflict disclosures, and no open accountability challenge before settlement can
  leave escrow. The L73 layer adds receipt transparency consistency: required
  usage receipts must appear in append-only transparency-log snapshots with valid
  inclusion proofs, matching receipt payload/envelope hashes, and no split-view
  roots before verifier-approved settlement can leave escrow. The L74 layer adds
  watchtower challenge settlement: registered independent watchtowers must attest
  to the L73 subject, and open or accepted public challenges force settlement into
  escrow with slashing and bounty commitments. The L75 layer adds output
  provenance binding: copied or exported output must bind to proof-carrying
  responses, serving-gateway hashes, attribution capsules, watchtower-cleared
  settlement, content credentials, watermark commitments, fingerprint commitments,
  and public verification paths without exposing raw generated text. The L40 level rejects
  source-row drift,
  claim-anchor drift, inactive license or royalty duties, failed confidence rows,
  signature drift, and private text leakage before a client renders the public
  source footer. The L41 level rejects nonce replay, hidden-path drift, opening
  mismatch, and private evidence or payout leakage in audit challenges. The L42
  level rejects copied-output marker loss, copied-body hash drift, upstream source
  row loss, transitive payout non-conservation, and copied prompt/output leakage.
  The L43 level rejects clearinghouse hash drift, non-ready transitive inputs,
  duplicate rows paid instead of held, payable/escrow conservation drift, and
  private prompt/output/source/copied-output leakage. The L44 level rejects
  remittance drift, missing payout-account hashes, inactive license terms, missing
  holds, and settlement overclaims. The L45 level rejects provider-only audit
  claims, missing audit discovery surfaces, failed public verifier replay,
  proof-pack hash drift, remittance amount drift, footer suppression, and private
  text or payout-account leakage in the audit attestation. The L46 level rejects
  non-conserved source revenue, event gross-revenue drift, creator-pool drift,
  missing receipt bindings, raw billing fields, and revenue-allocation tampering.
  The L47 level rejects finance-record hash drift, missing external record hashes,
  source-pool mismatch, total gross-revenue mismatch, unmapped finance records,
  unbacked allocation sources, private customer fields, and finance-attestation
  tampering. The L48 level rejects proof-dependency cycles, unknown dependencies,
  stale replay orders, overclaimed publication edges, private-field leakage, and
  graph tampering. The L49 level rejects publication-monitor checkpoint tampering,
  required public proof-surface removal, certification downgrades, snapshot-proof
  drift, non-reproducible hashes, and private-field leakage. The L50 level rejects
  publication-witness signature drift, missing witness quorum, split-view
  equivocation, inconsistent monitor subjects, and monitor payload leakage. The
  L51 level rejects unknown artifact signers, invalid artifact signatures, wrong
  witness keys, revoked active keys, broken key rotations, registry hash drift,
  trust-registry signature drift, and raw key-material leakage. The L52 level
  rejects non-reproducible certification report hashes, failed case-status roots,
  below-L51 attested reports, certification-attestation signature drift, missing
  trust-registry binding, and private case-payload leakage. The L53 level rejects
  copied-code scoring drift, missing compatible-owner payouts, incompatible copied
  code released without escrow/review, creator-pool non-conservation, private code
  leakage, and code-attribution report tampering. The L54 level rejects direct
  settlement without trusted signed ownership evidence, duplicate or weak ownership
  claims that bypass escrow, claim-row hash drift, private work/payment/issuer
  leakage, and claim-verification report tampering. The L55 level rejects stale,
  unreachable, footer-unbound, source-mismatched, or claim-span-mismatched citation
  sources and source-availability report tampering. The L56 level rejects cited
  spans that are not top-ranked minimal sufficient evidence, ambiguous decoy
  margins, broken source-availability bindings, footer-binding drift, and
  evidence-sufficiency report tampering. The L57 level rejects unaddressed
  counterevidence, answer acknowledgement drift, broken sufficiency bindings, and
  counterevidence report tampering. The L58 level rejects detached late-grounding
  reports by requiring source availability, evidence sufficiency, and
  counterevidence reports to be embedded and release-gate verified in the response
  envelope. The L59 level rejects unsupported factual sentences anywhere in the
  public answer surface. The L60 level rejects post-hoc citation attachment by
  requiring verified claims to be present in pre-generation context commitments.
  The L61 level rejects source packets that can act as instruction/control
  channels or mutate attribution and payout policy, and requires source-boundary
  telemetry to replay against the trace and generation context closure report. The
  L62 level rejects decision provenance graphs with missing proof edges, unknown
  influence channels, private prompt/source text, payout rows influenced directly
  by retrieved source text, or release decisions that do not bind response
  envelope, release gate, trace exchange, attribution capsule, and source-boundary
  proofs. The L63 level rejects calibrated attribution reports with benchmark
  drift, missing decision provenance, private text leakage, undisclosed
  low-confidence attribution, or confidence bounds that cannot be reproduced from
  the provenance benchmark. The L64 level rejects source-authenticity reports with
  unsigned or untrusted origin evidence, synthetic-source nondisclosure,
  source-farm or poisoning risk above policy thresholds, missing archive
  consensus, active-license drift, private text leakage, unauthenticated direct
  payout, or source-authenticity report tampering. The L65 level rejects streamed
  responses whose chunk lengths, chunk hashes, previous-chain hashes, final chain
  hash, gateway delivered-output hash, proof timing, or final attribution footer
  cannot be replayed from the public proof-carrying response and serving gateway
  report.
- The L66 level rejects conversation ledgers that skip parent turns, reorder the
  turn chain, drop inherited source-obligation hashes, fail proof/gateway/stream
  replay, omit visible inherited source rows, or disclose private prompt/raw-output
  fields in ledger rows.
- The L67 level rejects agent-tool attribution ledgers that fail to bind tool
  observations to trace spans, visible source rows, supported claims,
  conversation-level source obligations, and raw-tool-output privacy boundaries.
- The L68 level rejects pinpoint provenance reports that accept topical
  anti-documents, publish footer sources without answer-critical fact support, fail
  to escrow uncertain claims, drift from private replay inputs, or leak prompt,
  response, claim, source, or evidence-phrase text.
- The L69 level rejects citation identity reports that allow fabricated,
  unresolved, metadata-swapped, or claim-unsupported citations into canonical
  footers or citation-linked payout. This directly answers the recent
  citation-verification finding that link validity, topical relevance, and source
  labels are insufficient unless the citation identity and claim support can be
  replayed against authority records.
- The L70 level rejects direct settlement unless source confidence, source
  authenticity, evidence sufficiency, counterevidence adjudication, pinpoint
  provenance, and citation identity agree on the same event. This converts recent
  multi-source attribution and citation-verification work into a settlement rule:
  disagreement is not silently averaged away; it becomes public
  `attribution_consensus_escrow`.
- The L71 level rejects direct settlement unless multiple independent verifier
  attestations sign the same artifact root for the attribution consensus report,
  provider card, certification report, and integration profile. This responds to
  the same failure mode highlighted by recent citation-audit work: a plausible
  footer or internally consistent proof pack is not enough unless an external
  verifier can replay the cited evidence and sign the result. Disagreement
  produces `verifier_quorum_escrow` rather than direct settlement:
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.27700
  https://arxiv.org/abs/2604.21193
- The L77 level rejects settlement-finality claims unless the instruction-only
  remittance report is reconciled against hash-only external processor records.
  This closes the gap left by attribution and clearing papers: they can identify
  which work should be credited and paid, but they do not prove that a payment rail
  or escrow rail actually executed the instruction. RDLLM-L77 requires matching
  amounts, currencies, end-to-end IDs, payout/escrow account hashes, processor
  statuses, duplicate-record checks, unmatched-record checks, hold preservation, and
  raw-bank-field rejection before a provider can mark payout value as externally
  executed. The resulting report is still privacy-preserving: public verifiers see
  hashes, statuses, counts, and reconciliation IDs, not creator bank details.
- The L78 level rejects payout-finality claims unless registered external payment
  or escrow processors sign the settlement batches behind the L77 execution rows.
  This closes the next gap after reconciliation: a provider can no longer present
  internally consistent processor rows unless the trust registry recognizes the
  processor identity and the processor signature covers the batch hashes, row
  hashes, totals, currencies, counts, and statuses. Public verifiers still see only
  hashes, signatures, roles, registry entries, and aggregate totals.
- The L79 level makes payout proof creator-facing rather than only auditor-facing.
  Each `rdllm-creator-payout-receipt-report/v1` row binds a credited creator,
  work, chunk list, origin hashes, clearinghouse settlement row, remittance
  instruction, execution row, processor record hash, signed rail batch, and paid,
  escrowed, or held status. The report rejects totals drift, missing signed rail
  coverage, and private prompt, source, customer, tax, or raw account fields.
- The L80 level makes attribution proof user-facing rather than only artifact-facing.
  Each `rdllm-rendered-attribution-audit/v1` report parses the exact Markdown
  displayed to the user, verifies inline `[S#]` markers against response-envelope
  source labels, verifies footer source rows against the citation footer contract,
  and verifies claim-evidence span rows against answer coverage, source
  availability, evidence sufficiency, and counterevidence reports. This directly
  responds to recent citation-verification work: a generated footer is not enough
  unless the visible marker, footer row, source URI, content hash, and claim span
  all replay from signed evidence.
- Current streaming model APIs return incremental chunks over event streams, so a
  final proof object is not enough for production adoption: the proof must commit
  each partial emission and prove the footer arrived by stream completion. RDLLM-L65
  turns this into a hash-chain manifest rather than treating streaming as a UI
  concern:
  https://developers.openai.com/api/docs/guides/streaming-responses
- Current stateful response APIs carry prior responses into later turns through
  conversation objects or `previous_response_id`. RDLLM-L66 adds a conversation
  ledger so this state does not become an attribution laundering channel:
  https://developers.openai.com/api/docs/guides/conversation-state
- Current model APIs expose hosted and remote tools, including web search, file
  search, function calling, and MCP. RDLLM-L67 treats each tool observation as a
  provenance-bearing evidence event rather than trusting the final citation list:
  https://platform.openai.com/docs/guides/tools?api-mode=responses
- Current agent SDK tracing records LLM generations, tool calls, handoffs,
  guardrails, and custom events, which is the right substrate for a replayable
  source-obligation ledger but not by itself a royalty or citation proof:
  https://openai.github.io/openai-agents-js/guides/tracing
- H-RAG at SemEval-2026 Task 8 shows why multi-turn RAG needs separate treatment:
  its generation task requires accurate answers and faithful grounding in retrieved
  evidence across conversation turns. RDLLM-L66 turns that research pressure into
  a production invariant by requiring dependent turns to inherit source obligations:
  https://arxiv.org/abs/2605.00631
- AILS-NTUA at the same SemEval-2026 task decomposes reference-grounded generation
  into evidence span extraction, candidate drafting, and calibrated multi-judge
  selection, reinforcing that multi-turn grounding needs explicit evidence-state
  handling rather than a final-answer-only citation pass:
  https://arxiv.org/abs/2603.10524
- Recent citation-aware and source-attribution RAG papers reinforce that sources are
  operational evidence, not decorative links. Hybrid retrieval/reranking with a
  claim judge, Shapley-style source attribution, and intervention-based evidence
  utility all motivate hash-bound source rows that survive generation and session
  state:
  https://arxiv.org/abs/2605.01664
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2604.05467
- Recent agent-provenance papers make the L67 boundary sharper. TRACER argues for
  sentence-level provenance records tied to supporting tool turns and evidence
  units; TRACE and EnvTrustBench evaluate trajectories instead of only final
  answers; ARGUS and AuthGraph show why provenance/authorization must be tracked
  through tool parameters and untrusted context. RDLLM-L67 adapts those ideas to
  user-visible source rows and creator royalty obligations:
  https://arxiv.org/abs/2605.09934
  https://arxiv.org/abs/2510.02837
  https://arxiv.org/abs/2605.08828
  https://arxiv.org/abs/2605.03378
  https://arxiv.org/abs/2605.26497
- Deep-research citation audits show that links and cited source lists are not
  sufficient unless source accessibility, relevance, and factual support are
  checked. RDLLM-L67 therefore requires the tool observation that produced a
  source row to be replay-bound to the claim and footer:
  https://arxiv.org/abs/2605.06635
- ISO 20022 payment initiation and remittance-advice materials give RDLLM a
  practical shape for payment-file rows: an instruction should carry amount,
  currency, creditor identity/account reference, end-to-end ID, and remittance
  information for reconciliation. RDLLM-L44 uses that idea while keeping only
  payout-account hashes in the public artifact:
  https://www.iso20022.org/sites/default/files/2020-12/ISO20022_MDRPart2_PaymentsInitiation_2020_2021_v1_ForSEGReview.pdf
- W3C Verifiable Credentials 2.0 and W3C PROV reinforce the portability target:
  remittance claims and attribution chains should be independently verifiable
  statements, not rows trapped inside one provider database:
  https://www.w3.org/TR/vc-data-model/
  https://www.w3.org/TR/prov-dm/
- Recent 2026 data-attribution work continues to make the same point from the
  model side: attribution evidence is becoming more scalable, but market adoption
  requires standard artifacts that bind influence evidence, visible source
  footers, clearing, and remittance. Examples include RAG attribution surveys,
  zeroth-order influence approximation, uncertainty-based data attribution, and
  rescaled influence functions:
  https://arxiv.org/abs/2601.19927
  https://openreview.net/forum?id=KYaNRqJ7ho
  https://openreview.net/forum?id=IKB9uhMVH9
  https://openreview.net/forum?id=edD3qTmoea
- DataDignity (arXiv, May 2026) frames robust training-data attribution as
  pinpoint provenance under paraphrase, hard anti-documents, and transformed query
  conditions. RDLLM-L30 now adds a runtime semantic text attribution report with
  concept fingerprints, hard-decoy margins, source footer rows, accepted-owner
  payouts, and semantic-text escrow:
  https://arxiv.org/abs/2605.05687
- Cited but Not Verified (arXiv, May 2026), CiteAudit (arXiv, February/May 2026),
  and User-Centric Evidence Ranking (EACL 2026) reinforce that footer sources must
  resolve to evidence users can inspect rather than to plausible citation strings.
  RDLLM-L55 therefore binds footer rows to reachable or archived source snapshots,
  registered content hashes, and cited claim-span hashes, while RDLLM-L56 ranks
  candidate spans and requires the cited span to be the minimal sufficient support
  with a margin over decoys and RDLLM-L57 rejects unaddressed contradiction
  candidates rather than treating citations as presentation text. RDLLM-L58 then
  requires those three reports to be embedded and gate-bound before a provider that
  claims L57 can emit the response, RDLLM-L59 requires the final answer surface
  itself to be claim-covered before release, RDLLM-L60 requires those claims
  to be closed over pre-generation context commitments, RDLLM-L61 verifies
  that cited source packets were evidence-only data rather than instruction or
  control channels, and RDLLM-L62 exposes a hash-only influence graph for the
  final claim, footer, payout, and release decisions:
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2602.23452
  https://aclanthology.org/2026.eacl-long.340/
- Each event now includes a `rdllm-grounding-quality/v1` report, and the certification
  suite reaches RDLLM-L7 by proving source accessibility, citation integrity,
  evidence relevance, fact support, policy alignment, and payout alignment.
- The engine now emits `rdllm-claim-registry/v1` reports that detect duplicate and
  near-duplicate ownership claims across creators.
- Registry decisions are bound into ledger events, receipts, public receipts, and
  conformance checks.
- If registry enforcement is enabled and a matched work has an open ownership
  conflict, the creator pool routes to `registry_dispute_escrow` and the output
  verdict becomes `blocked_by_registry`.
- The certification suite now reaches RDLLM-L8 by proving duplicate-claim detection,
  registry-dispute escrow, and registry-report hash binding.
- The settlement layer now emits `rdllm-escrow-resolution/v1` reports that release
  registry-dispute escrow after resolution while preserving original event hashes.
- The certification suite now reaches RDLLM-L9 by proving settlement reports
  recompute from the ledger and resolution, drain registry-dispute escrow, and
  release the held value to the resolved owner.
- The interop layer now emits `rdllm-interop/v1` bundles: a VC-shaped receipt
  credential, a PROV-shaped answer graph, and optional VC-shaped escrow-settlement
  credential.
- The certification suite now reaches RDLLM-L10 by proving bundle hashes,
  credential proofs, graph hashes, receipt bindings, and settlement-report bindings
  are all reproducible and tamper-sensitive.
- Each event now includes a source-access trace for retrieval and text-match paths
  plus a `rdllm-attribution-gap/v1` report that reconciles accessed, cited, paid,
  policy-withheld, and registry-withheld sources.
- The certification suite now reaches RDLLM-L11 by proving closed attribution gaps
  for normal answers, detecting paid-but-hidden footer tampering, and treating
  rights-blocked or registry-blocked sources as accountable escrow rather than silent
  disappearance.
- Receipts now include `rdllm-selective-disclosure/v1` roots and private per-path
  salts. Public packages disclose model/event/source/claim-support facts while
  redacting source quotes, evidence text, source-access traces, economics, detailed
  rights decisions, and registry decision internals.
- RDLLM-L12 proves selective-disclosure
  packages verify standalone, verify against the private signed receipt, expose
  public claim support, redact private fields, and reject public receipt or leaf
  tampering.
- Receipts and interoperability bundles now include `rdllm-trace-exchange/v1`
  artifacts aligned with OpenTelemetry GenAI spans. Verification proves source
  access, footer citations, claim-support spans, and receipt telemetry hashes agree.
- The certification suite now reaches RDLLM-L13 by rejecting omitted provider
  source-access spans and citation relabeling, while proving trace summaries match
  the signed receipt.
- The statement layer now emits `rdllm-royalty-statement/v1` reports that aggregate
  many events into creator, escrow, work, source-usage, receipt, and trace
  commitments without disclosing private prompts, outputs, quotes, evidence text,
  or matched text.
- The RDLLM-L14 certification case proves aggregate payout
  conservation, receipt-root binding, trace-root binding, source-usage commitments,
  private-text redaction, and tamper rejection for creator statement drift.
- The challenge layer now emits `rdllm-attribution-challenge/v1` reports that let
  creators contest omitted or weak attribution while binding the original event,
  optional statement, challenged content hash, overlap evidence, and non-rewrite
  remedy.
- The certification suite now reaches RDLLM-L15 by proving accepted omitted-source
  correction, already-credited no-action, private-text redaction, and remedy tamper
  rejection.
- The provider-card layer now emits `rdllm-provider-attribution-card/v1` reports
  that disclose certification level, coverage, supported evidence channels, public
  surfaces, challenge policy, limitations, and evidence roots without private text.
- The RDLLM-L16 certification case proves provider-card binding to
  certification evidence and ledger coverage, private-text redaction, stale-level
  rejection, and coverage tamper rejection.
- The training-summary layer now emits `rdllm-training-content-summary/v1` reports
  aligned with EU GPAI training-content summaries, Croissant usage policies, SPDX
  AI/Dataset BOMs, and ODRL rights metadata.
- The certification suite now reaches RDLLM-L17 by proving training-rights coverage,
  license/use counts, policy roots, content-hash roots, training-value commitments,
  stale-certification rejection, and private-work-text redaction.
- The assurance layer now emits `rdllm-assurance-bundle/v1` reports that publish
  hash-only proof-pack entries, Merkle roots, inclusion proofs, and profile flags
  aligned with SCITT, Rekor, in-toto, and C2PA-style conformance assurance.
- The certification suite now reaches RDLLM-L18 by proving assurance bundles cover
  required artifacts, disclose no private payload text, verify inclusion proofs, and
  reject artifact-hash or proof tampering.
- The answer-card layer now emits `rdllm-answer-provenance-card/v1` reports that
  bind visible source footers, claim span hashes, receipt hashes, trace hashes,
  grounding verdicts, and attribution-gap verdicts without disclosing private text.
- The certification suite now reaches RDLLM-L19 by proving answer provenance cards
  verify against the ledger event, receipt, and trace, redact private prompt/source
  text, and reject card or footer tampering.
- The source-verification layer now emits `rdllm-source-verification-report/v1`
  reports that prove cited source hashes, quote hashes, claim evidence hashes,
  offsets, visible footer spans, and answer-card bindings materialize from the
  registered corpus without publishing private text.
- The certification suite now reaches RDLLM-L20 by rejecting fabricated source
  hashes, stale answer-card bindings, and claim evidence that cannot be reproduced
  from registered content.
- The response-envelope layer now emits `rdllm-response-envelope/v1` packages that
  carry the rendered answer, answer provenance card, source verification report,
  public receipt, provider card, and certification posture as one API-verifiable
  object.
- The certification suite now reaches RDLLM-L21 by rejecting rendered-output
  tampering and embedded-artifact tampering inside the response envelope.
- The integration-profile layer now emits `rdllm-integration-profile/v1` contracts
  that declare generation and verification endpoints, required headers, embedded
  artifact requirements, verifier commands, schemas, public surfaces, readiness
  checks, and proof hashes.
- The certification suite now reaches RDLLM-L22 by rejecting integration-profile
  tampering, provider-surface drift, certification regression, and response-envelope
  drift.
- The discovery-manifest layer now emits `rdllm-discovery-manifest/v1` reports for
  `/.well-known/rdllm.json`, cataloging public artifact paths, artifact hashes, API
  contract hashes, schemas, verifier commands, readiness checks, and bound proof
  hashes.
- The certification suite now reaches RDLLM-L23 by rejecting discovery-path
  tampering, artifact-hash drift, provider-surface regression, certification
  regression, and assurance bundles that omit integration-profile or
  response-envelope evidence.
- The lineage layer now emits `rdllm-lineage-report/v1` reports that bind source
  royalty shares to derivative-work edges, upstream content hashes, recursive
  pass-through obligations, and payout-conservation commitments.
- The lineage certification layer rejects missing upstream works, lineage cycles,
  declared upstream hash drift, payout drift, private-text leakage, and report
  tampering.
- The provenance-evaluation layer now emits `rdllm-provenance-evaluation/v1`
  reports that replay clean-source, paraphrase, hard-decoy, unattributed-escrow,
  and derivative-lineage cases with hashed benchmark inputs and ranked source
  evidence.
- The certification suite now reaches RDLLM-L25 by rejecting provenance-evaluation
  tampering, omitted cases, source-ranking drift, signature drift, and private
  benchmark/source-text leakage.
- The counterfactual layer now emits `rdllm-counterfactual-influence/v1` reports
  that remove each credited work, replay the same prompt and answer, and publish
  source-removal status, payout reallocation status, substitute-source pressure,
  and influence margins without private text.
- The public artifact pack now includes `examples/counterfactual_corpus.json` and
  `artifacts/counterfactual_ledger.json`, a decisive-source vector whose signed
  counterfactual report has a positive influence margin.
- The certification suite now reaches RDLLM-L26 by rejecting counterfactual-report
  tampering, ablation replay drift, signature drift, and private prompt, answer,
  source, quote, or claim-evidence leakage.
- The media layer now emits `rdllm-media-attribution/v1` reports for image, audio,
  video, 3D, and text-shaped signatures. Reports publish only hashes, score
  components, ranked candidates, payout shares, and escrow decisions, while private
  descriptors and perceptual hashes remain verifier-side inputs.
- The certification suite now reaches RDLLM-L27 by rejecting media-attribution
  tampering, replay drift, payout drift, signature drift, and raw media or
  descriptor leakage.
- The model-signal layer now emits `rdllm-model-signal-attribution/v1` reports that
  bind private provider telemetry to an explicit `rdllm-attribution-contract/v1`,
  scalar signal scores, accepted owner payouts, and model-signal escrow without
  disclosing raw hidden states, token logits, private prompts, private outputs, or
  chain-of-thought.
- The certification suite now reaches RDLLM-L28 by rejecting model-signal
  tampering, replay drift, payout drift, signature drift, unsupported attribution
  contracts, weak-score promotion, and private telemetry leakage.
- The rights-remediation layer now emits `rdllm-rights-remediation/v1` reports that
  compare previous and updated policy roots, preserve historical event hashes,
  prove denied future training, retrieval, generation, external-attribution,
  display, and quote use after revocation, and verify `rights_conflict_escrow`
  without leaking work text, prompts, outputs, matched text, or private ledger
  payloads.
- The certification suite now reaches RDLLM-L29 by rejecting remediation replay
  drift, historical-event rewrites, future-use enforcement drift, escrow drift,
  signature drift, and private text leakage.
- The semantic-text layer now emits `rdllm-semantic-text-attribution/v1` reports
  that rank paraphrased or external outputs against registered text using lexical,
  concept, source-distinctiveness, sequence, n-gram, and decoy-margin evidence,
  then publish source-footer commitments, accepted-owner payouts, and semantic
  escrow without exposing prompt, output, matched, or source text.
- The certification suite now reaches RDLLM-L30 by rejecting semantic attribution
  replay drift, hard-decoy payment, escrow drift, footer tampering, signature drift,
  and private text leakage.
- The cross-provider exchange layer now emits `rdllm-attribution-exchange/v1`
  manifests. This turns attribution from a provider-local proof into a relayable
  contract: downstream model providers can import provider cards, certification,
  integration profiles, discovery manifests, response envelopes, assurance bundles,
  and semantic-text reports by hash, preserve public source-footer rows, and keep
  ambiguous or unlicensed value in escrow.
- This addition responds to the recent citation-verification and provenance papers:
  DataDignity shows that robust attribution must survive paraphrase and hard
  decoys; Cited but Not Verified, CiteCheck, CiteAudit, PaperTrail, and SciTrue
  show that source claims need retrievable evidence and claim-level grounding; and
  LLM hallucination audits show that fabricated or misassigned citations are a
  credit-allocation problem as well as an accuracy problem. RDLLM-L31 therefore
  requires an importable exchange with explicit source-footers and hash-bound
  upstream proof, not merely inline citations in generated text.
- The certification suite now reaches RDLLM-L31 by rejecting exchange replay drift,
  missing imported artifacts, missing exchange schema or verifier, missing discovery
  path, weak upstream certification, source-footer relay failure, hash drift, and
  private text leakage.
- The conformance-vector layer now emits `rdllm-conformance-vector-pack/v1` reports
  with fixture hashes, expected public outcomes, verifier commands, and named
  negative mutations. This makes RDLLM testable as a public standard rather than a
  provider-specific promise.
- The certification suite now reaches RDLLM-L32 by rejecting vector-pack hash drift,
  missing L32 vectors, missing negative mutations, weak upstream certification,
  missing verifier commands, expected-outcome drift, and private text leakage.
- The federation-handshake layer now emits `rdllm-federation-handshake/v1` reports
  that bind requester/provider identity, negotiated RDLLM level, required artifact
  hashes, runtime headers, source-footer relay, escrow relay, and downgrade policy.
  This turns public proof publication into a runtime interop gate.
- The certification suite now reaches RDLLM-L33 by rejecting handshake hash drift,
  stale artifact bindings, missing federation schemas or verifier commands, missing
  discovery paths, missing conformance vectors, disabled relay obligations,
  disabled downgrade protection, and private prompt, output, matched, source, or
  hidden-state leakage.
- The portable-attribution-capsule layer now emits
  `rdllm-attribution-capsule/v1` reports that bind copied output markers,
  rendered-output hashes, delivered-body hashes, federation-handshake hashes, exchange hashes,
  conformance-vector hashes, provider proof hashes, C2PA-compatible assertion
  pointers, and SCITT-like statement subjects without exposing prompt, answer,
  matched, source, hidden-state, or private ledger payloads.
- The certification suite now reaches RDLLM-L34 by rejecting capsule hash drift,
  stale artifact bindings, missing capsule schema or verifier commands, missing
  discovery paths, missing copy markers, copied-body tampering, incomplete runtime
  headers, signature drift, and private text leakage.
- The response-release-gate layer now emits `rdllm-response-release-gate/v1`
  reports that make source attribution a serving-boundary decision. The gate binds
  the response envelope, answer provenance card, source verification report,
  attribution capsule, provider attribution card, and certification report, then
  emits only if footer labels, claim span prefixes, source materialization,
  capsule delivery contracts, provider public surfaces, and upstream `RDLLM-L34`
  certification all verify.
- The certification suite now reaches RDLLM-L35 by rejecting release-gate hash
  drift, failed gate checks, unsupported grounded claims, stale capsule binding,
  missing release-gate public surfaces, certification regression below L34, and
  private prompt, answer, matched, source, hidden-state, or ledger leakage. This is
  the direct implementation response to recent 2026 citation-verification papers:
  link validity, source relevance, and citation labels are useful, but source
  materialization and claim-level support must gate the answer before display.
- The proof-carrying-response layer now emits
  `rdllm-proof-carrying-response/v1` objects that make the L35 decision enforceable
  at the API boundary. A released object carries the answer, capsule marker, release
  gate, response envelope, provider card, and certification report together; a
  failed gate produces a held-response object that suppresses the original answer.
- The certification suite now reaches RDLLM-L36 by rejecting displayed-output
  tampering, missing capsule markers on released copied output, stale
  proof-response hashes, missing provider proof-carrying surfaces, certification
  regression below L35, blocked responses that leak the original answer, and
  private source/matched/hidden-state leakage.
- The serving-gateway layer now emits `rdllm-serving-gateway-report/v1` objects
  that bind a concrete API request route to the proof-carrying response delivered
  at egress. It hash-commits the private prompt and raw model output, verifies the
  embedded proof response, and rejects delivered-output hash drift.
- The certification suite now reaches RDLLM-L37 by rejecting gateway egress drift,
  missing provider gateway surfaces, certification regression below L36, embedded
  proof-response failures, and disclosure of private prompt/raw-output fields in
  the request context.
- The creator-license-contract layer now emits
  `rdllm-creator-license-contract/v1` objects that bind registered source works to
  allowed AI uses, attribution duties, compensation duties, minimum creator-pool
  terms, revocation state, content hashes, and hashed payout-account commitments
  before use. This is the rights-side companion to source footers: an answer footer
  can now be checked against materialized sources, claim span hashes, serving
  egress proof, and pre-use license terms.
- The certification suite now reaches RDLLM-L38 by rejecting license-scope drift,
  missing attribution or compensation duties, term-hash/signature drift,
  mismatched content hashes, and disclosure of private work text or raw payout
  accounts.
- The source-confidence layer now emits `rdllm-source-confidence-report/v1`
  objects that bind answer provenance cards, source verification reports, and
  creator license contracts into public footer rows, claim confidence rows, and a
  hallucination taxonomy for fabricated sources, metadata drift, hash mismatch,
  footer omission, attribution suppression, license gaps, unsupported claims, and
  evidence-span gaps.
- The certification suite now reaches RDLLM-L39 by rejecting source-confidence
  hash drift, stale answer-card or source-verification bindings, license-scope
  gaps, unsupported claim rows, failed footer rows, hallucination issue counts,
  and disclosure of private prompt, answer, source, evidence, or payout text.
- The citation-footer-contract layer now emits
  `rdllm-citation-footer-contract/v1` artifacts that bind exact source display
  rows, claim display anchors, confidence labels, license status, royalty status,
  display order, row hashes, and rendered footer hash to a response envelope.
- The certification suite now reaches RDLLM-L40 by rejecting citation-footer
  hash drift, source-row tampering, claim-anchor tampering, inactive license or
  royalty status, failed source-confidence rows, signature drift, and private
  prompt, answer, source, evidence, or payout-account leakage.
- The certification suite now reaches RDLLM-L41 by adding private audit challenge
  verification over redacted source-access, claim-evidence, rights, and payout
  paths; verifier tests reject replayed nonces and tampered opening hashes.
- The transitive-attribution layer now emits
  `rdllm-transitive-attribution-report/v1` artifacts that bind downstream reuse of
  copied RDLLM output to the upstream attribution capsule, response envelope,
  answer-card source rows, copied-input hash, and pass-through settlement
  obligations.
- The certification suite now reaches RDLLM-L42 by rejecting copied-output marker
  loss, copied-body hash drift, dropped upstream source rows, non-conserved
  transitive payout, and private copied-output or prompt leakage.
- The clearinghouse layer now emits `rdllm-clearinghouse-report/v1` artifacts that
  ingest `rdllm-royalty-statement/v1` and
  `rdllm-transitive-attribution-report/v1`, normalize each obligation into
  payable, escrow, or held rows, deduplicate repeated artifact submissions and
  repeated transitive obligations, and bind the result with input, obligation,
  payable, escrow, held, duplicate, and policy roots.
- The certification suite now reaches RDLLM-L43 by rejecting clearinghouse row
  tampering, duplicate payment, non-conserved payable/escrow totals, and private
  settlement text leakage.
- The remittance layer now emits `rdllm-remittance-report/v1` artifacts that
  convert clearinghouse payable and escrow rows into instruction-only payment
  rows with payout-account hashes, creator-license bindings, ISO 20022-compatible
  reconciliation fields, preserved held rows, and explicit no-bank-settlement
  claims.
- The certification suite now reaches RDLLM-L44 by rejecting remittance row
  tampering, missing payout-account hashes, inactive license terms, clearinghouse
  value drift, missing held rows, raw payout-account disclosure, and payment
  reports that imply executed settlement.
- The audit-attestation layer now emits
  `rdllm-third-party-audit-attestation/v1` artifacts over the provider card,
  certification report, certification attestation, integration profile, discovery
  manifest, assurance bundle, response envelope, source confidence report,
  citation footer contract, clearinghouse report, remittance report, revenue
  allocation report, and finance ledger attestation. Settlement artifacts remain
  outside the stable assurance bundle and are bound here to avoid cyclic proof
  dependencies.
- The certification suite now reaches RDLLM-L45 by rejecting provider
  self-attestation, missing audit surfaces, failed public verifier replay,
  proof-pack hash drift, remittance amount drift, stale artifacts, and private
  prompt, answer, source, evidence, or payout-account leakage.
- The revenue-allocation layer now emits `rdllm-revenue-allocation-report/v1`
  artifacts over hashed billing, advertising, subscription, API, enterprise, and
  marketplace revenue sources, allocation policy, event allocation rows, receipt
  rollups, and creator-pool commitments.
- The certification suite now reaches RDLLM-L46 by rejecting unsupported allocation
  modes, non-conserved source revenue, ledger gross-revenue drift, creator-pool
  drift, missing receipt bindings, duplicate event rows, raw billing field leakage,
  and allocation report tampering.
- The finance-ledger layer now emits `rdllm-finance-ledger-attestation/v1`
  artifacts over hash-only finance export rows, revenue-source rollups, allocation
  report bindings, and privacy checks. The certification suite now reaches
  RDLLM-L47 by rejecting missing finance hashes, source-total mismatches, orphaned
  finance records, unbacked allocation sources, raw customer field leakage, and
  attestation tampering.
- The proof-dependency layer now emits `rdllm-proof-dependency-graph/v1` artifacts
  over hash-only artifact nodes, replay dependency rows, publication commitment
  rows, and topological verifier steps. The certification suite now reaches
  RDLLM-L48 by rejecting replay cycles, unknown dependencies, stale replay orders,
  publication edges that are not backed by the assurance bundle's own artifact
  entries, private-field leakage in the graph, and graph tampering.
- The publication-monitor layer now emits `rdllm-publication-monitor/v1` artifacts
  over hash-only public proof-surface snapshots, Merkle inclusion proofs, append-only
  checkpoint history, artifact diffs, and certification-regression checks. The
  certification suite now reaches RDLLM-L49 by rejecting required-artifact removal,
  non-reproducible hashes, broken inclusion proofs, checkpoint-chain tampering,
  certification downgrade, private-field leakage, and monitor tampering.
- The receipt-transparency-consistency layer now emits
  `rdllm-receipt-transparency-consistency-report/v1` artifacts over observed
  usage receipt-log snapshots, append-only prefix rows, split-view conflict rows,
  required receipt inclusion proofs, and settlement escrow rows. The certification
  suite now reaches RDLLM-L73 by rejecting omitted usage receipts, inconsistent
  Merkle roots, forked same-size log views, receipt payload/envelope drift,
  private-field leakage, and consistency-report tampering.
- The watchtower-challenge-settlement layer now emits
  `rdllm-watchtower-challenge-settlement-report/v1` artifacts over the L73
  receipt-transparency subject, active watchtower trust-registry rows, watchtower
  attestations, public challenge rows, slashing evidence, bounty rows, and
  settlement escrow rows. The certification suite now reaches RDLLM-L74 by
  rejecting missing watchtower quorum, invalid watchtower signatures, open or
  accepted blocking challenges, private-field leakage, creator-pool drift, and
  watchtower-report tampering.
- The output-provenance-binding layer now emits
  `rdllm-output-provenance-binding-report/v1` artifacts over proof-carrying
  responses, serving-gateway output hashes, attribution capsules, L74
  watchtower-cleared settlement, C2PA-style content credential assertions,
  watermark commitments, fingerprint-registry commitments, and public verification
  rows. The certification suite now reaches RDLLM-L75 by rejecting missing
  copy-survival signals, content-credential drift, gateway-output drift,
  watchtower-settlement failure, private text leakage, and binding-report
  tampering.
- The post-release-discovery layer now emits
  `rdllm-post-release-discovery-report/v1` artifacts over the base discovery
  manifest, output provenance binding report, proof dependency graph,
  proof-carrying response, serving-gateway report, attribution capsule, watchtower
  settlement, provider card, integration profile, and certification report. The
  certification suite now reaches RDLLM-L76 by rejecting stale base manifests,
  missing late output artifacts, catalog tampering, output-binding replay failure,
  self-referential hash cycles, and private text leakage.
- The payment-execution layer now emits `rdllm-payment-execution-report/v1`
  artifacts over remittance reports and hash-only external payment or escrow
  processor records. The certification suite now reaches RDLLM-L77 by rejecting
  missing settlement records, duplicate or unmatched processor rows, amount or
  currency drift, wrong payout or escrow account hashes, non-settled processor
  statuses, remittance-hold leakage into paid rows, raw bank/customer/tax fields,
  and payment-execution tampering. This makes payout finality independently
  verifiable instead of treating a remittance file as proof that money moved.
- The payment-rail layer now emits `rdllm-payment-rail-attestation/v1` artifacts
  over payment-execution reports, trust registries, and signed processor batch
  attestations. The certification suite now reaches RDLLM-L78 by rejecting
  unregistered processors, unauthorized processor roles, invalid signatures,
  uncovered execution batches, amount/status drift, and raw private payment fields.
- The creator-payout-receipt layer now emits
  `rdllm-creator-payout-receipt-report/v1` artifacts over clearinghouse,
  remittance, payment-execution, and payment-rail reports. The certification suite
  now reaches RDLLM-L79 by rejecting creator-visible payout receipts that cannot be
  replayed from attribution and settlement evidence, that lack signed rail-batch
  coverage, that drift in paid/escrow/hold totals, or that leak private payment,
  prompt, output, source, customer, or tax fields.
- The rendered-attribution-audit layer now emits
  `rdllm-rendered-attribution-audit/v1` artifacts over response envelopes,
  citation footer contracts, source availability, evidence sufficiency,
  counterevidence, and answer claim coverage reports. The certification suite now
  reaches RDLLM-L80 by rejecting visible Markdown whose inline source markers,
  source footer rows, or claim-evidence span rows drift from signed grounding
  artifacts, or whose audit leaks raw prompt, answer, source, or claim text.
- The training-memory provenance layer now emits
  `rdllm-training-memory-provenance/v1` artifacts over response envelopes,
  rendered attribution audits, creator-license contracts, training-content
  summaries, and registered source snapshots. The certification suite now reaches
  RDLLM-L81 by rejecting hidden memorized source spans in the exact displayed
  answer, stale snapshot roots, unlicensed training/generation/display use, and
  public reports that leak raw answer, source, prompt, or matched text. This
  closes the OLMoTrace/DataDignity gap where a model can rely on training memory
  even when retrieval logs and visible footers appear clean.
- The evidence-locked generation layer now emits
  `rdllm-evidence-locked-generation/v1` artifacts over response envelopes,
  answer-claim coverage reports, generation-context closure reports, citation
  footer contracts, rendered attribution audits, and training-memory provenance
  reports. The L82 certification case rejects locks
  created after generation start, support-required answer units without satisfied
  source/context/footer/claim-evidence locks, footer rows without a matching lock,
  hidden training-memory spans, and public reports that leak raw answer, source,
  prompt, claim, or context text.
- The emission evidence enforcement layer now emits
  `rdllm-emission-evidence-enforcement/v1` artifacts over response envelopes,
  answer-claim coverage reports, evidence-locked generation reports,
  proof-carrying responses, serving-gateway reports, and streaming attribution
  manifests. The certification suite now reaches RDLLM-L83 by rejecting streaming
  that starts before the evidence-lock/generation window, proof/gateway/stream
  output-hash drift, support-required units without satisfied locks, non-replayable
  stream chunks, and public reports that leak raw answer, source, prompt, claim,
  context, or chunk text.
- The live emission witness layer now emits `rdllm-live-emission-witness/v1`
  artifacts over emission enforcement reports and streaming attribution manifests.
  The certification suite now reaches RDLLM-L84 by rejecting missing independent
  witness quorum, preflight attestations created after the first streamed chunk,
  final stream-chain or chunk-subject drift, witness disagreement, invalid witness
  signatures, and public reports that leak raw prompt, answer, source, claim,
  context, or chunk text.
- The live emission transparency layer now emits
  `rdllm-live-emission-transparency/v1` artifacts over live witness reports and
  witness attestation subjects. The certification suite now reaches RDLLM-L85 by
  rejecting missing witness-report or witness-attestation log inclusion,
  non-reproducible log roots, append-only prefix violations, same-size split-view
  roots, payload hash drift, entry-type drift, invalid inclusion proofs, and
  public reports that leak raw prompt, answer, source, claim, context, chunk, or
  credential fields. This turns SCITT/Sigstore-style transparency from publication
  metadata into an emission-time attribution control.
- The attested attribution runtime layer now emits
  `rdllm-attested-attribution-runtime/v1` artifacts over live transparency,
  proof-carrying response, serving-gateway, and evidence-lock reports. The
  certification gate is RDLLM-L86 and rejects runtime measurement drift,
  untrusted attestors, stale or invalid quotes, missing attribution-enforcement
  capabilities, subject-binding drift, and public reports that leak private prompt,
  answer, source, chunk, or secret fields. This turns transparent attribution proof
  from an after-the-fact log into a claim about the measured code path that served
  the answer.
- The claim-source attribution layer now emits
  `rdllm-claim-source-attribution/v1` artifacts that replay every visible answer
  claim against candidate sources, Q&A nugget commitments, topical anti-documents,
  optional visual-region commitments, and LOO-style source contribution before a
  footer row or payout row is accepted. This directly incorporates the recent
  DataDignity finding that robust provenance must separate true answer support
  from topical resemblance, Chain of Evidence's requirement for pixel/bounding-box
  anchors in visual document RAG, GaRAGe and Trust-Align's claim-level grounding,
  attribution, and refusal framing, GuarantRAG's separation of parametric answers
  from evidence-backed refer answers, and source-attribution work that treats RAG
  attribution as a per-document contribution problem. The certification suite now
  reaches RDLLM-L87 by rejecting anti-document wins, insufficient LOO margin,
  unsupported claims, missing visual anchors for credited visual evidence,
  non-conserved attribution credit, footer omissions, replay drift, and public
  reports that leak raw prompt, answer, source, claim, nugget, or visual text.
- The causal evidence-utility layer now emits
  `rdllm-causal-evidence-utility/v1` artifacts that bind credited footer rows to
  current-turn retrieval/tool traces and REMOVE, REPLACE, DUPLICATE, and
  multi-source removal trials. This incorporates CUE-R's intervention-based view
  of per-evidence-item utility, AgenticRAG and retrieval-as-reasoning work on
  multi-step retrieval traces, MuRGAt's finding that fact-level multimodal
  reasoning can be correct while citations are wrong, and the recent attribution,
  citation, and quotation survey's call for unified evidence granularity. The
  L88 certification gate rejects spurious cited sources,
  prior-context citation drift, duplicate credit inflation, missing intervention
  trials, unsupported causal-use claims, non-conserved payout credit, and public
  reports that leak raw prompt, answer, source, claim, query, or observation text.
- The parametric memory layer now emits
  `rdllm-parametric-memory-attribution/v1` artifacts for claims answered from
  learned weights rather than current retrieval. It combines DataDignity's
  training-data provenance framing, knowledge-attribution probes for distinguishing
  memory from context, probabilistic token attribution for model-agnostic token
  sensitivity, ProToken-style token/client attribution, and protocol-layer
  attribution proposals such as SCP. The certification suite now reaches
  RDLLM-L89 by rejecting current-context contamination, anti-document wins,
  training-summary drift, weak memory or influence probes, non-conserved payout
  credit, and public reports that leak raw prompt, answer, source, claim, or probe
  text.
- The style influence layer now emits
  `rdllm-style-influence-attribution/v1` artifacts for generated outputs that
  imitate registered creator styles, voices, or modality-specific signatures
  without verbatim copying. It treats style credit as a stricter rights-controlled
  channel: accepted rows need active style-generation permission, sufficient
  style similarity, declared style intent, anti-style decoy separation, low
  content-copy overlap, footer disclosure, and creator-pool conservation. The
  L90 certification gate rejects copy-like outputs from
  style payout, revoked licenses, ambiguous style-profile ties, anti-style decoy
  wins, tampering, and public reports that leak private style exemplars or output
  text.
- The model-lineage layer now emits
  `rdllm-model-lineage-attribution/v1` artifacts for downstream models trained,
  fine-tuned, or distilled from attributed outputs, synthetic datasets, or teacher
  traces. It incorporates recent post-training data-lineage work such as Tracing
  the Roots and distillation/provenance research by treating training inheritance
  as an auditable royalty obligation rather than a one-time dataset artifact. The
  RDLLM-L91 layer rejects hidden synthetic
  training, missing teacher-distribution or teacher-output evidence, duplicate
  artifact over-credit, non-conserved future usage pools, revoked training rights,
  tampering, and public reports that leak private training examples, prompts,
  source text, or student outputs.
- The black-box model-provenance layer now emits
  `rdllm-black-box-model-provenance/v1` artifacts for API-visible models that may
  have been trained, fine-tuned, distilled, merged, or watermarked from protected
  upstream models without disclosure. It builds candidate provenance sets from
  challenge hashes, candidate scores, baseline distributions, adjusted p-values,
  watermark/fingerprint support counts, footer rows, and payout or escrow
  obligations. The RDLLM-L92 gate rejects
  insufficient challenge sets, excluding unrelated candidates, enforcing
  multiple-testing controls, conserving the provenance challenge pool, rejecting
  tampering, and preventing private prompts, source text, and model outputs from
  leaking into public reports.
- The attribution dispute adjudication layer now emits
  `rdllm-attribution-dispute-adjudication-report/v1` artifacts for cases where
  attribution, model provenance, ownership, or payout is challenged after a proof
  report exists. It incorporates recent provenance-testing, watermarking,
  behavioral-fingerprint, and audit-trail work by treating attribution as a
  contestable public decision: disputed value is frozen, claimant and respondent
  positions are admitted as hash-committed evidence, conflicted votes are excluded
  from quorum, appeal windows block premature release, and the final report
  publishes release, freeze, slash, bounty, and adjudicated footer rows without
  exposing prompts, outputs, source text, or challenge transcripts. The
  RDLLM-L93 gate rejects missing notice, failed
  quorum, weak evidence commitments, appeal-bypassing release, unconserved escrow,
  settlement drift, tampering, and private-text leakage.
- The post-adjudication settlement adjustment layer now emits
  `rdllm-post-adjudication-settlement-adjustment-report/v1` artifacts for the
  correction step after a dispute changes payout. The design borrows the proven
  platform pattern of separately held disputed revenue from YouTube Content ID,
  but makes it provider-neutral and verifiable for AI: original payment execution
  and creator payout receipt hashes are preserved, corrected entitlement rows
  produce top-ups or capped future-netting recoupments, open appeals freeze all
  movements, and creators receive hash-bound adjustment receipts. The RDLLM-L94
  gate rejects historical payment rewrites, missing processor or receipt hashes,
  uncapped recoupment, appeal-bypassing release, unconserved corrections,
  tampering, and private payment/source-evidence leakage.
- The residual corpus royalty layer now emits
  `rdllm-residual-corpus-royalty-report/v1` artifacts for diffuse value learned
  from licensed training corpora when no visible answer source can be singled out
  with sufficient confidence. It incorporates recent DataDignity, DATE-LM,
  LLM-scale influence valuation, Concept Influence, RISE, LoRIF, and ZK-Value
  work by treating model-native valuation as evidence, not as an unchecked payout
  oracle: public reports bind training-content summary cohorts, creator-license
  terms, model-usage revenue rows, valuation evidence hashes, direct-attribution
  exclusions, creator-level caps, payable rows, escrow rows, and creator residual
  receipts. The RDLLM-L95 gate rejects unlicensed or low-confidence rows paid
  directly, double-counting of visible answer attribution, unconserved residual
  pools, creator-cap violations, missing residual receipts, tampering, and public
  leakage of prompt, output, source, training, customer, or payment text. The
  visible footer remains the answer-grounding surface; L95 only settles residual
  training value that survives rights and valuation checks.
- The valuation-method audit layer now emits `rdllm-valuation-method-audit/v1`
  artifacts before residual training value can be trusted for payout. It converts
  recent DATE-LM, DataDignity, RISE, LoRIF, Concept Influence, and ZK-Value
  directions into an executable audit: public method cards must cover every
  residual valuation method used, benchmark rows must cover known contributors,
  hard anti-documents, duplicate guards, confidence calibration, rights-denied
  escrow, and score stability, and privacy or zero-knowledge commitments must be
  present. The RDLLM-L96 gate rejects unaudited residual methods, benchmark drift,
  duplicate over-credit, unstable scores, missing privacy commitments, tampering,
  and public leakage of private benchmark, training, prompt, output, customer, or
  payment text.
- The evidence-region binding layer now emits
  `rdllm-evidence-region-binding/v1` artifacts after rendered attribution and
  claim-source attribution. It closes the remaining "right source, wrong passage"
  failure mode by binding every rendered claim span and footer span prefix to an
  exact source snapshot region, preserving page/line/character/bounding-box/timecode
  locators, and rejecting hard negative neighboring regions without publishing raw
  prompt, answer, source, customer, payment, or private evidence text. The RDLLM-L97
  gate is intentionally stricter than a citation footer: a footer row is accepted
  only when the cited region itself supports the rendered claim.
- The source access lease layer now emits `rdllm-source-access-lease/v1`
  artifacts after evidence-region binding. It closes the "right source, no
  licensed access" failure mode by requiring directly settled consumed source rows
  to prove creator-issued active leases, matching access logs, license-contract
  permission, minimum creator-pool-rate compliance, and region binding. Denied,
  revoked, expired, or unleased usage is allowed only as hash-bound escrow, and
  public reports suppress raw prompt, answer, source, customer, and payout data.
- The content-protocol ingestion layer now emits
  `rdllm-content-protocol-ingestion/v1` artifacts after source-access leases. It
  closes the "external rights signal lost in translation" failure mode by
  requiring RSL, CoMP, SCP, ODRL, Croissant, robots.txt, C2PA/TDM, or custom
  publisher terms to be hash-preserved and carried into creator contracts,
  source-access leases, and escrow routing. Direct settlement fails when a
  direct source lacks an external protocol record, when the protocol denies the
  use, when rate or attribution duties drift, or when raw notices or private text
  leak.
- The citation-reliance layer now emits `rdllm-citation-reliance-receipt/v1`
  artifacts after content-protocol ingestion. It closes the "correct citation,
  unfaithful reliance" failure mode identified by recent RAG attribution work:
  every visible footer source must have a satisfied pre-generation evidence lock,
  a rendered claim-evidence row, accepted claim-source replay, accepted causal
  utility evidence, current-turn trace membership, source-access coverage, and
  protocol permission. Missing locks, non-causal sources, hidden paid sources, or
  private-text leakage downgrade the receipt to `needs_review`.
- The license-transaction layer now emits `rdllm-license-transaction-receipt/v1`
  artifacts after citation-reliance receipts. It closes the dynamic authorization
  gap left by static rights signals: a directly settled source must have a signed
  license-server token, license-ledger inclusion proof, matching source-access
  nonce and metering hash, matching content-protocol terms, and a valid issued/
  accepted/expiry window before direct settlement can leave escrow.
- The grounded-source-footer layer now emits `rdllm-grounded-source-footer/v1`
  artifacts after license-transaction receipts. It closes the user-facing
  confidence gap by requiring visible source rows to replay to confidence,
  availability, exact evidence regions, citation reliance, license transactions,
  and public verifier handles while redacting prompt, answer, source, evidence,
  and payout text.
- The source-footer-delivery layer now emits `rdllm-source-footer-delivery/v1`
  artifacts after proof-carrying response and serving-gateway evidence. It closes
  the display gap by binding the grounded footer to the response envelope, copied
  output, gateway egress hash, source labels, claim span handles, and client-visible
  verifier metadata.
- The foundation API attribution profile layer now emits
  `rdllm-foundation-attribution-profile/v1` artifacts after discovery and L103
  delivery evidence. It closes the adoption gap by making the minimum attribution
  API surface explicit: response headers, embedded proof objects, well-known
  verifier paths, verifier commands, and fail-closed policy must be present before
  generic clients render an answer as attributed.
- The client attribution enforcement layer now emits
  `rdllm-client-attribution-enforcement/v1` receipts from the relying party. It
  closes the downstream stripping gap by proving the client observed the required
  L104 headers, replayed the embedded response envelope and source-footer-delivery
  receipt, matched source labels to delivered source rows, and blocked rendering
  when a required header or source label is missing.
- The persistent memory provenance layer now emits
  `rdllm-persistent-memory-provenance/v1` receipts after client attribution
  enforcement. It closes the cross-session memory gap: a stored assistant or
  agent memory cell must carry source labels, upstream proof hashes, license and
  retention policy, royalty carry-forward rows, and delete tombstones, and any
  later answer using that memory must display the carried labels in the verified
  footer. This follows recent persistent-memory agent work such as Memori and the
  broader MCP/tool ecosystem, where durable context can become an uninspected
  source of generated answers.
- The private reasoning attribution layer now emits
  `rdllm-private-reasoning-attribution/v1` receipts after persistent memory
  provenance. It closes the hidden-scratchpad and delegation gap: private reasoning
  steps, router handoffs, and memory-influenced synthesis must publish commitments,
  bind upstream proof hashes, preserve source labels and royalty rows, and prove
  those labels remain visible in the verified footer without exposing chain-of-thought.
- The post-training signal provenance layer now emits
  `rdllm-post-training-signal-provenance/v1` receipts after private reasoning
  attribution. It closes the RLHF/RLAIF/RLVR laundering gap: preference labels,
  reward scores, verifier outcomes, critiques, and alignment traces must bind to
  upstream L107 private-reasoning and L91 model-lineage hashes, carry source labels
  and royalties forward, disclose synthetic signal inputs, include annotator or
  verifier attestations, and avoid publishing raw feedback, prompt, answer, source,
  or reward-rationale text. This directly implements the post-training lineage
  lessons from RLVR Datasets and Where to Find Them, Tracing the Roots, and
  Provable Model Provenance Set: model behavior shaped by post-training signals is
  still a provenance-bearing use, not an attribution-free side channel.
- The attribution bill of materials layer now emits
  `rdllm-attribution-bom/v1` artifacts after L108 signal provenance. It closes the
  model-release supply-chain gap: source components, notice hashes, license-term
  hashes, proof artifact hashes, provider-card evidence, proof-dependency graph
  evidence, and post-training signal provenance must travel with the model or API
  release in a CycloneDX-aligned AI/ML BOM. This follows current AI bill of
  materials and ML-BOM standardization work and addresses permissive-washing
  findings that license notices and terms are easily lost unless the release
  artifact makes notice carry-forward replayable:
  https://cyclonedx.org/capabilities/mlbom/
  https://arxiv.org/abs/2605.19755
  https://arxiv.org/abs/2602.08816
- The creator attribution audit index layer now emits
  `rdllm-creator-attribution-audit-index/v1` artifacts after L109 ABOM
  publication. It closes the creator self-audit gap: a creator query must replay
  across model-release source components, grounded source footers, delivery
  receipts, post-training signals, source-access leases, license transactions,
  model lineage, training summaries, and payout receipts. This maps transparency
  policy pressure and content-provenance practice into a concrete verifier: a
  provider cannot merely publish aggregate transparency; it must answer a
  creator-specific query with namespaced source identities and private-text
  redaction.
  https://crfm.stanford.edu/fmti/
  https://c2pa.org/specifications/specifications/2.1/index.html
  https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202320240AB2013
- The creator attribution audit federation layer now emits
  `rdllm-creator-attribution-audit-federation/v1` artifacts after L110 provider
  indexes. It closes the cross-provider self-audit gap: the same creator query
  must replay across multiple provider-local indexes under one query hash, with
  provider-scoped source-label namespaces, bound exchange or federation artifacts,
  and explicit conflict rows for unresolved creator identity mismatches. This
  combines recent source-attribution RAG work with SCITT-style transparent
  statements, W3C proof-carrying credentials, and OpenID Federation-style trust
  chaining so source footers can become portable confidence evidence rather than
  plausible citation strings.
  https://arxiv.org/abs/2507.04480
  https://www.rfc-editor.org/rfc/rfc9943.html
  https://www.w3.org/TR/vc-data-model/
  https://openid.net/specs/openid-federation-1_0.html
- The creator audit federation transparency layer now emits
  `rdllm-creator-attribution-audit-federation-transparency/v1` artifacts after
  L111. It closes the equivocation gap: a provider cannot give one creator,
  customer, or regulator a clean federation answer and another party a different
  answer for the same query/provider set without creating a public split-view or
  same-query conflict row. This imports Certificate Transparency, SCITT, and
  transparency-witness practice into creator attribution rather than leaving
  federation answers as private API responses.
  https://www.rfc-editor.org/rfc/rfc9162.html
  https://www.rfc-editor.org/rfc/rfc9943.html
  https://github.com/transparency-dev/witness
- The creator audit transparency monitor now emits
  `rdllm-creator-audit-transparency-monitor/v1` artifacts after L112. This is the
  creator-side counterpart to transparency publication: a creator or auditor can
  scan append-only logs for a query commitment, prove inclusion for every matching
  federation or participant-index entry, report newly observed appearances since a
  prior monitor run, and fail closed on contradictory same-query answers. The
  design directly answers recent source-attribution findings that citations are
  confidence infrastructure only when they can be checked externally, not merely
  displayed in a footer.
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2508.00838
  https://www.rfc-editor.org/rfc/rfc9162.html
  https://www.rfc-editor.org/rfc/rfc9943.html
- The creator audit private watch layer now emits
  `rdllm-creator-audit-private-watch/v1` artifacts after L113. It closes the
  privacy gap created by public monitor query hashes: a creator can prove that a
  monitor found appearances and new observations through keyed watch tokens without
  exposing stable query hashes, provider-set hashes, subject hashes, provider IDs,
  prompt text, answer text, source text, license text, or payment data. The
  reference prototype uses deterministic HMAC watch tokens for offline replay; the
  production upgrade path is an RFC 9497 VOPRF/POPRF service or a PSI/PIR monitor
  backend so providers do not learn creator watchlists.
  https://www.rfc-editor.org/rfc/rfc9497.html
  https://www.rfc-editor.org/rfc/rfc9162.html
  https://arxiv.org/abs/2507.04480
- The deep research citation audit layer now emits
  `rdllm-deep-research-citation-audit/v1` artifacts after L114. It closes the
  long-form citation gap identified in recent deep-research-agent work: a source
  string or reachable link is not sufficient evidence that a cited source supports
  the attached claim. The artifact parses rendered text markers, resolves each
  marker to materialized source rows, binds cited claims to source and quote
  hashes, records relevance and factual-support scores, and fails closed on
  unresolved markers, unmaterialized links, weak support, or private replay text
  leakage.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2604.05467
- The source freshness audit layer now emits
  `rdllm-source-freshness-audit/v1` artifacts after L115. It maps recent
  temporal-RAG and freshness work into a deployable verifier: claims are typed as
  static/current/latest/recent/rapidly-changing/as-of; selected sources must have
  retrieved-at and effective-at metadata, source-version hashes, validity windows,
  policy-bound source-age limits, and retrieval-lag limits; and candidate rows
  prove that a fresher supported source was not ignored unless it is materially
  weaker. This addresses the gap between "the citation exists" and "the citation
  was temporally valid when the model answered."
  https://arxiv.org/abs/2603.16544
  https://arxiv.org/abs/2310.03214
  https://arxiv.org/abs/2603.18012
- The evidence-force calibration layer now emits
  `rdllm-evidence-force-calibration/v1` artifacts after L118. It maps the
  evidence-force warning in recent cited-RAG work into a deployable gate: a
  citation is not enough unless the claim's relation, modality, scope, temporal,
  and numeric strength are no stronger than the source warrants. Verified source
  footers and direct payout fail closed for over-warranted claims, and every
  visible verified footer claim must have a matching calibrated force row, even
  when the source is real, reachable, licensed, fresh, and relevant.
- The warranted source footer layer now emits
  `rdllm-warranted-source-footer/v1` artifacts after L119. It turns the private
  force-calibration replay into a public footer supplement: each visible claim
  exposes relation, modality, scope, temporal, and numeric warrant labels, claim
  hashes, and proof handles while withholding raw prompt, claim, evidence, and
  source text.
  https://arxiv.org/abs/2605.28044
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2507.04480
- The source-origin lineage layer now emits
  `rdllm-source-origin-lineage/v1` artifacts after L120. It closes the synthetic
  source laundering gap: a footer source is not directly payable merely because it
  is visible, relevant, reachable, and warranted. The report classifies each
  source row as human-original, synthetic-with-lineage, synthetic-unattributed, or
  unknown; synthetic-with-lineage rows split value to active upstream creators;
  unknown or unattributed synthetic rows route to origin-review escrow; and the
  user-facing footer can expose origin labels without revealing raw source text.
  https://arxiv.org/abs/2605.23684
  https://arxiv.org/abs/2605.28044
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2507.04480
- The evidence-locator layer now emits
  `rdllm-evidence-locator-manifest/v1` artifacts after L122. It closes the
  remaining reader-facing gap between "the footer showed a source preview" and
  "the user can inspect the exact passage": every preview row must carry a public
  locator URL, resolver status, source-URI match, preview-row hash, excerpt hash,
  and snapshot or text-fragment proof. Missing, unresolved, non-exact, source-URI
  mismatched, or private-text-leaking locators fail closed.
  https://arxiv.org/abs/2605.27700
  https://arxiv.org/abs/2605.23684
  https://arxiv.org/abs/2605.28044
- The citation URL-health layer now emits `rdllm-citation-url-health/v1`
  artifacts after L123. It closes the provider-neutral footer gap between "the
  locator points somewhere exact" and "the URL is not hallucinated": every
  locator must be live, content-addressed, DOI-resolved, or backed by archival
  snapshot evidence, with fabricated, never-seen, mismatched, unresolved, or
  unverified URLs failing closed before footer display or direct attribution.
  This is designed for composite adoption across foundation-model providers
  because it depends on replayable resolver receipts rather than a provider's
  internal model architecture.
  https://arxiv.org/abs/2605.27700
  https://arxiv.org/abs/2605.23684
- The composite foundation adapter layer now emits
  `rdllm-composite-foundation-adapter/v1` artifacts after L124. It closes the
  adoption gap between "RDLLM has a provider-neutral proof object" and "a real
  foundation-model API can carry it": native OpenAI Responses, Anthropic Messages,
  Google Gemini, Meta/Llama-style, Mistral, Cohere, xAI, Amazon Bedrock Converse,
  Azure OpenAI Responses, and OpenAI-compatible response rows must map their
  response IDs, model IDs, output hashes, attribution headers, embedded JSON
  fields, citation paths, tool paths, and final streaming hash events to the same
  RDLLM envelope, footer-delivery, and URL-health hashes.
  Missing provider-family coverage, native-output hash mismatch, missing proof
  headers, missing JSON proof fields, missing citation/tool paths, streaming
  drift, non-fail-closed policy, and private text disclosure fail closed.
  https://platform.openai.com/docs/api-reference/responses
  https://docs.anthropic.com/en/api/messages
  https://ai.google.dev/gemini-api/docs
  https://docs.mistral.ai/api/
  https://llama-stack.readthedocs.io/
- The foundation provider conformance layer now emits
  `rdllm-foundation-provider-conformance/v1` artifacts after L125. It converts
  "the adapter can map one native response" into "the provider family has public
  fixtures for all attribution-critical modes": sync responses, streaming,
  tool calling, citation or grounding metadata, URL-health binding, structured
  proof fields, claim-support footers, parametric-memory fallback, and fail-closed
  negative cases. This directly addresses recent citation-audit findings that
  plausible references can still fail source support, freshness, or origin checks.
  https://docs.cohere.com/reference/chat
  https://docs.x.ai/docs/api-reference
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
  https://learn.microsoft.com/azure/ai-services/openai/how-to/responses
- The universal foundation model contract layer now emits
  `rdllm-universal-foundation-model-contract/v1` artifacts after L131. It closes
  the remaining adoption gap between "each component has a proof" and "a
  foundation-model provider, broker, or enterprise gateway is required to use the
  same proof chain for every supported provider family": the contract binds
  provider card, integration profile, discovery manifest, proof dependency graph,
  composite adapter, provider conformance, runtime adapter, runtime router,
  deployment attestation, universal composition, universal settlement, selected
  route, source footer, creator-pool conservation, and published public surfaces.
  Missing provider-family coverage, route/deployment drift, missing public
  surfaces, unready settlement, footer-settlement mismatch, or private text
  leakage fail closed.

- The L133-L136 pass closes the last provider-neutral adoption gap. AEX frames
  the API boundary as a signed request-output relation, SEAR and GenAI telemetry
  show that gateway traces can be standardized, DataDignity and SourceTracker show
  that output-to-source provenance must survive paraphrase, hard decoys, and code
  reuse, and Cited but Not Verified shows that visible citations can still fail
  factual support. C2PA's Content Credentials and durable credential model provide
  an interoperable content-provenance surface, while recent C2PA security and
  provenance/watermarking papers show why metadata alone is insufficient for
  high-stakes trust. RDLLM-L136 therefore emits a
  `rdllm-universal-content-credential/v1` artifact that binds visible source rows,
  evidence previews, exact locators, URL-health rows, payout eligibility rows,
  output content-credential rows, durable watermark/fingerprint signals, public
  verifier surfaces, and the L135 universal invocation witness. Missing footer
  rows, unverifiable locators, missing payout rows, missing durable provenance
  signals, weak provider-call non-repudiation, or private text disclosure fail
  closed.
  https://arxiv.org/abs/2603.14283
  https://arxiv.org/abs/2603.26728
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2605.28510
  https://arxiv.org/abs/2605.06635
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification
  https://arxiv.org/abs/2604.24890
  https://arxiv.org/abs/2605.21002
- The L137 pass turns the component stack into one provider-neutral deployment
  passport. Recent evidence-based generation surveys show that attribution,
  citation, quotation, and evaluation terminology remain fragmented; source
  attribution in RAG shows that retrieved-document contribution can be measured
  but is expensive and approximation-sensitive; CiteGuard shows that faithful
  citation attribution benefits from retrieval-augmented validation rather than
  LLM-as-judge alone; DataDignity shows that training-data provenance needs hard
  anti-document controls instead of lexical similarity; and large-scale 2026
  citation audits show fabricated references are now a real production risk.
  RDLLM-L137 therefore emits a `rdllm-universal-rdllm-passport/v1` artifact that
  binds the L136 content credential to certification, certification attestation,
  provider card, training summary, integration profile, discovery manifest,
  assurance bundle, replay DAG, composite foundation adapter, provider-family
  conformance, runtime adapter/router, deployment attestation, universal
  composition, universal settlement, foundation-model contract, invocation guard,
  invocation coverage, invocation witness, public well-known surfaces, verifier
  commands, and explicit research-control rows. Missing provider-family coverage,
  missing public passport discovery, missing verifier commands, unready source
  footers/content credentials, unverifiable artifact hashes, weak research
  controls, or private prompt/output/source/payment leakage fail closed.
  https://arxiv.org/abs/2508.15396
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2510.17853
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2605.07723
  https://www.w3.org/TR/vc-data-integrity/
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://modelcontextprotocol.io/specification/2025-06-18

- The L138 pass turns the deployment passport into a universal adoption standard
  that a foundation-model provider, gateway, SDK, auditor, enterprise buyer,
  creator registry, or clearinghouse can implement without bespoke negotiation.
  Recent citation-attribution audits show that source-looking footers are not
  enough: citations must resolve to actual cited content and be checked against
  claim support, while large-scale hallucinated-citation measurements show that
  fabricated references are now observable at ecosystem scale. Official C2PA,
  W3C Data Integrity, OpenTelemetry GenAI, MCP, and SCITT work provide reusable
  surfaces for content credentials, signed proof objects, provider-call telemetry,
  tool/resource discovery, and transparency publication, but none of them by
  itself defines the royalty and attribution procurement gate. RDLLM-L138
  therefore emits `rdllm-universal-adoption-standard/v1`: a signed implementer
  contract binding the L137 passport, conformance vectors, integration profile,
  well-known discovery, provider attribution card, certification report,
  attribution exchange, federation handshake, trust registry, SDK surfaces,
  role obligations, procurement gates, standards mappings, verifier commands,
  public paths, and private-text leakage checks. Missing provider families,
  missing public standard surfaces, missing verifier commands, weak conformance
  vectors, failed procurement gates, or private prompt/output/source/payment
  leakage fail closed.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.07723
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification
  https://www.w3.org/TR/vc-data-integrity/
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://modelcontextprotocol.io/specification/2025-06-18
  https://datatracker.ietf.org/doc/draft-ietf-scitt-architecture

- The L139 pass turns the adoption standard into an executable interop test kit.
  Recent provider-neutral telemetry, source-attribution, provenance, and
  citation-verification work all point to the same operational risk: a provider
  can publish the right policy words while SDKs, gateways, renderers, CI jobs, or
  offline auditors accept responses with missing footers, missing proof objects,
  stale provider routes, invalid signatures, rights-denied sources, hallucinated
  citations, unguarded native calls, or private-text leaks. RDLLM-L139 therefore
  emits `rdllm-universal-interop-test-kit/v1`: a signed compatibility package
  binding the L138 standard to provider-family golden fixtures, SDK bindings,
  execution targets, negative mutation cases, public verifier commands, source
  footer delivery, response envelopes, invocation guards, and trust roots. A
  deployment cannot claim practical universal compatibility unless those fixtures
  replay and those negative cases block.
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.27700
  https://arxiv.org/abs/2605.05687
  https://www.w3.org/TR/vc-data-integrity/

- The L140 pass turns executable compatibility into runtime source provenance.
  Recent attributed-generation work shows that citations need generation-time
  planning and progress checks; source-attribution RAG shows that retrieved
  document contribution can be measured but must be made cheaper and replayable;
  multimodal attribution benchmarks show that evidence may be text, image, or
  region-level context; and large citation audits show that fabricated references
  are now an ecosystem-scale failure mode. At the same time, MCP makes external
  tools and data sources a first-class model context surface, while C2PA, W3C
  Data Integrity, PROV, and the EU GPAI transparency/copyright regime provide
  reusable credential and disclosure patterns. RDLLM-L140 therefore emits
  `rdllm-universal-context-provenance-bridge/v1`: a signed runtime bridge that
  requires every MCP/tool/retrieval/file/browser/vector/enterprise/license/media
  context event to be authorized, licensed, converted into source claims, projected
  into visible source footers, bound to agent steps, and reconciled to royalty
  projection before a context-influenced response can be released.
  https://aclanthology.org/2025.acl-long.490/
  https://arxiv.org/abs/2507.04480
  https://ojs.aaai.org/index.php/AAAI/article/view/40585
  https://arxiv.org/abs/2605.07723
  https://modelcontextprotocol.io/specification/2025-06-18
  https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html
  https://www.w3.org/TR/vc-data-integrity/
  https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai

- The L141 pass turns runtime provenance into user-verifiable citation grounding.
  Recent citation audits and RAG verification work show that a visible source row
  is not enough: the source must exist, the locator must resolve or have durable
  fallback evidence, the cited passage must support the claim, and confidence must
  be calibrated rather than implied by formatting. RDLLM-L141 therefore emits
  `rdllm-universal-citation-verification-contract/v1`, a signed contract that
  requires every displayed label to pass source identity, URL health, evidence
  locator, claim support, evidence-force, confidence, rendered-footer, L140
  context, authenticity, and royalty checks before the UI can call a citation
  verified grounding.
  https://arxiv.org/abs/2605.07723
  https://aclanthology.org/2025.acl-long.490/
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2605.28044
  https://arxiv.org/abs/2605.23684

- The L142 pass closes the production cache/reuse bypass. Recent semantic-cache
  work shows that production LLM deployments use static/dynamic caches to reduce
  latency and cost, but similarity-threshold reuse creates correctness and
  collision risks. Recent RAG attribution work also shows that evidence utility
  and source attribution must be measured at the retrieved-item level rather than
  inferred from final-answer quality. RDLLM-L142 therefore requires every cached
  or replayed answer to revalidate query equivalence, evidence overlap,
  source-version freshness, consent/license continuity, L141 citation continuity,
  cache-collision resistance, and a new royalty-metered reuse event before the
  cached answer can be served as grounded.
  https://machinelearning.apple.com/research/semantic-caching
  https://www.nature.com/articles/s41598-026-36721-w
  https://arxiv.org/abs/2601.23088
  https://arxiv.org/abs/2604.05467
  https://arxiv.org/abs/2508.15396

- The L143 pass closes the training-to-serving attribution bypass. Recent source
  attribution and citation-verification work shows that response grounding must
  expose which retrieved sources support the answer, while training-data,
  post-training, distillation, and synthetic-data lineage work shows that some
  obligations originate before retrieval-time context ever appears. RDLLM-L143
  therefore emits `rdllm-universal-training-serving-contract/v1`: a signed
  provider-neutral matrix binding pretraining, fine-tuning, adapters,
  RLHF/RLAIF/RLVR, distillation, synthetic-data ingestion, release snapshots, runtime
  routes, grounded reuse, citation footers, revocation propagation, residual
  royalties, valuation methods, and serving meters before a foundation-model
  answer can claim that source attribution and royalty obligations survived from
  training into serving.
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2508.15396
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2604.05467

- The L144 pass closes the private-evidence trust gap. Public source footers make
  answers inspectable, but foundation-model providers still need a way to prove
  training corpus membership, license/consent state, post-training signal lineage,
  distillation lineage, serving metering, citation replay, residual valuation, and
  revocation/unlearning without publishing proprietary corpora, reward data,
  prompts, customer logs, model weights, hidden states, or source text. RDLLM-L144
  therefore emits `rdllm-universal-confidential-attribution-audit/v1`: a signed
  provider-neutral matrix over 10 provider families and 10 audit domains, backed by
  confidential evidence-room commitments, ZK/TEE/selective-disclosure proof
  handles, encrypted evidence escrow, independent auditor quorum, creator challenge
  routes, regulator export support, differential privacy budget commitments, and
  fail-closed leakage fixtures.
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2508.15396
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2604.05467
  https://arxiv.org/abs/2605.14421

- The L145 pass closes the runtime-authority gap. Attribution and payout proofs
  can still fail in production if an agent, tool, memory store, retrieval
  connector, browser action, model route, or settlement gateway acts without a
  signed actor/intent/context authority chain. Recent work makes this gap
  explicit: Sovereign Context Protocol proposes attribution-aware access to
  creator-owned data; HDP signs multi-hop human delegation; PROV-AGENT binds
  agent interactions into workflow provenance; MCP production analysis identifies
  missing identity propagation and observability; and explicit-provenance work
  argues that agentic responsibility must be computable and interventionable.
  RDLLM-L145 therefore requires a 10-provider by 10-runtime authority matrix,
  public verifier commands, intervention logging, revocation checks, and
  fail-closed negative fixtures before an attributed answer, source footer, tool
  action, memory-influenced response, or settlement can be released.
  https://arxiv.org/abs/2603.27094
  https://arxiv.org/abs/2604.04522
  https://arxiv.org/abs/2508.02866
  https://arxiv.org/abs/2603.13417
  https://arxiv.org/abs/2605.17169

- The L146 pass closes the adoption-root gap. Payouts alone do not make users
  confident that an answer is grounded, and isolated source footers do not prove
  that the provider, runtime, training-to-serving continuity, confidential audit,
  public discovery, assurance bundle, and settlement authority all agree.
  RDLLM-L146 therefore emits `rdllm-universal-rdllm-root/v1`: one signed,
  provider-neutral root that binds certification, attestation, provider card,
  integration profile, discovery manifest, assurance bundle, proof graph,
  L143 training-to-serving continuity, L144 confidential auditability, L145
  runtime authority, source-footer delivery, provider-family coverage, negative
  fixtures, and settlement authorization. This maps recent explicit-provenance
  work, CUE-R evidence utility, CiteGuard citation-attribution alignment, AIBOM
  lifecycle assurance, SCITT/RFC 9943 transparency statements, W3C Data Integrity,
  C2PA content credentials, and recent creator data-sharing/compensation market
  design into one verifiable deployment object.
  https://arxiv.org/abs/2605.17169
  https://arxiv.org/abs/2604.05467
  https://arxiv.org/abs/2510.17853
  https://www.rfc-editor.org/rfc/rfc9943.html
  https://www.w3.org/TR/vc-data-integrity/
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
  https://ssrn.com/abstract=6761318

- The L147 pass closes the runtime-emission gap. A deployment root can tell a
  buyer which provider proof pack is trustworthy, but it does not by itself prove
  that a concrete answer actually passed through the root-bound release path.
  RDLLM-L147 therefore emits
  `rdllm-universal-emission-enforcement-gateway/v1`: one signed per-response
  artifact that binds the L146 root to the release gate, proof-carrying response,
  serving gateway, response envelope, delivered source footer, emission evidence,
  live witness, transparency log, invocation guard, invocation coverage,
  invocation witness, foundation runtime route, deployment attestation, trust
  registry, and client display enforcement. This maps recent work on deep
  research citation parsing and evaluation, argument-level provenance for agent
  enforcement, runtime protection controllers, verifiable training/release
  attestations, Warrant Certificate Authorities, runtime governance receipts, and
  dual attribution/verification into a fail-closed answer-emission mechanism.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.11039
  https://arxiv.org/abs/2604.17562
  https://arxiv.org/abs/2603.28988
  https://www.ietf.org/archive/id/draft-bondar-wca-00.html
  https://attestedintelligence.com/documents/verifiable-runtime-governance.pdf
  https://arxiv.org/abs/2604.21193
  https://opentelemetry.io/docs/specs/semconv/gen-ai/

- The L148 pass closes the provider-adoption completeness gap. A root and
  per-response gateway are still not enough for a market standard unless buyers,
  creators, auditors, and SDK implementers can verify that every provider family,
  native API route, source footer, client display surface, telemetry mapping,
  settlement route, and public proof receipt follows the same contract. RDLLM-L148
  therefore emits `rdllm-universal-composite-rdllm-profile/v1`: one signed
  adopter-facing profile that binds the universal passport, adoption standard,
  interop test kit, L146 root, L147 gateway, source-footer delivery, client
  attribution enforcement, foundation API/runtime adapters, invocation guard,
  invocation witness, trust registry, provider-family rows, API binding rows,
  expected API-to-provider-family mappings, standards mappings, and fail-closed
  fixtures. It explicitly covers OpenAI, Anthropic, Google, Meta, Mistral, Cohere,
  xAI, DeepSeek, AWS Bedrock, Azure OpenAI, OpenRouter-style aggregators, local
  open-weight deployments, and enterprise gateways. It maps the 2026 citation
  reliability result that citations must be checked for link validity, relevance,
  and factual support; RAG source-attribution work on document utility; mechanistic
  training-origin attribution; SCP-style creator access logs; SourceTracker-style
  code provenance; LLM-Rosetta's hub-and-spoke cross-provider API translation;
  OpenTelemetry GenAI; C2PA 2.4; SCITT/RFC 9943; W3C Data Integrity; WCA; MCP;
  ISO 20022; and RSL/TDM rights signals into one deployable contract.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2601.21996
  https://arxiv.org/abs/2603.27094
  https://arxiv.org/abs/2605.28510
  https://arxiv.org/abs/2604.09360
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html
  https://www.rfc-editor.org/rfc/rfc9943.html
  https://www.w3.org/TR/vc-data-integrity/
  https://www.ietf.org/archive/id/draft-bondar-wca-00.html
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
  https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses

- The L149 pass closes the deployment-runtime conformance gap. A universal
  provider profile is not sufficient unless live routes can prove that each
  answer was generated through guarded provider APIs, source-attribution modes,
  visible footer injection, client display enforcement, OpenTelemetry GenAI
  export, proof download, challenge routing, privacy filtering, and settlement
  metering. RDLLM-L149 therefore emits
  `rdllm-universal-runtime-conformance-receipt/v1`: one signed receipt binding
  sync generation, streaming generation, tool calls, agent actions, RAG answers,
  memory-influenced answers, batch generation, enterprise proxying, and client
  rendering to the L148 profile, L147 gateway, L146 root, citation identity,
  claim-source attribution, evidence-region binding, deep-research citation
  audits, source leases, invocation witnesses, finance ledgers, and trust
  registry. This maps DataDignity-style pinpoint provenance, CUE-R evidence-item
  utility, PaperTrail claim-evidence interfaces, source-attribution RAG findings,
  hallucinated-citation audits, mechanistic/influence attribution, LLM-Rosetta
  cross-provider API translation, OpenTelemetry GenAI, C2PA, MCP resources/tools,
  OpenAI Responses, Azure OpenAI Responses, AWS Bedrock Converse, and
  OpenRouter-style API routes into one runtime rule: no L149 receipt, no verified
  footer display and no creator settlement claim.
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2604.05467
  https://arxiv.org/abs/2602.21045
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2605.07723
  https://arxiv.org/abs/2601.21996
  https://arxiv.org/abs/2601.21929
  https://arxiv.org/abs/2604.09360
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://c2pa.wiki/specifications/
  https://modelcontextprotocol.io/specification/2025-06-18/basic/index
  https://platform.openai.com/docs/api-reference/responses
  https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses
  https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-bedrock-batch-inference-supports-converse-api-format/
  https://openrouter.ai/docs/api-reference/chat-completion
  https://openrouter.ai/docs/api-reference/chat-completion
  https://modelcontextprotocol.io/
  https://rslstandard.org/

- The L150 pass closes the post-hoc citation gap. A runtime receipt proves that a
  route was guarded, but it does not by itself prove that each generated claim was
  emitted with source support rather than decorated with plausible citations after
  the answer existed. RDLLM-L150 therefore emits
  `rdllm-universal-claim-provenance-envelope/v1`: one signed envelope that binds
  every displayed claim or sentence to a claim hash, response segment hash,
  generation-time provenance record, support relation, source proof, exact
  evidence region, citation identity, locator health, visible footer row, tool or
  memory trace, payout basis, and settlement meter. It covers quotation,
  compression, inference, retrieval, tool observation, conversation memory,
  parametric memory, and residual corpus value, and it requires API, Markdown,
  HTML, streaming, mobile, and export surfaces to preserve the verified footer
  and downloadable proof. This maps TRACER-style verifiable generative
  provenance, AgentSim verifiable trace simulation, PaperTrail claim-evidence
  interfaces, DataDignity pinpoint provenance, RAG source-attribution findings,
  and hallucinated-citation audits into one user-facing rule: no L150 envelope,
  no grounded display and no direct creator settlement.
  https://arxiv.org/abs/2605.09934
  https://arxiv.org/abs/2604.26653
  https://arxiv.org/abs/2602.21045
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2605.07723
- The L151 pass closes the provider-wire gap. AEX shows that LLM API users need
  request-output attestation, transform receipts, and streaming checkpoints at
  the API boundary, while SCP argues that creator-owned content access must be
  logged, licensed, and attributable by default. RDLLM-L151 turns those findings
  into one universal provider rule: OpenAI-style Responses routes, Anthropic
  Messages routes, Gemini generate-content routes, Bedrock Converse routes,
  OpenRouter/aggregator routes, local OpenAI-compatible routes, and enterprise
  proxies must preserve L150 envelope hashes, L149 runtime receipt hashes,
  footer metadata, telemetry spans, transform receipts, and settlement meters
  across headers, JSON bodies, streams, SDK metadata, batch callbacks, webhooks,
  and exported copies. If a provider, proxy, SDK, or export path strips the proof,
  the route cannot claim grounded display or direct creator settlement.
  https://arxiv.org/abs/2603.14283
  https://arxiv.org/abs/2603.27094
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://platform.openai.com/docs/api-reference/responses
  https://platform.claude.com/docs/en/api/messages
  https://ai.google.dev/gemini-api/docs/text-generation
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
  https://openrouter.ai/docs/api-reference/chat-completion

- The L152 pass closes the accountability-chain gap. Recent audit-trail work
  defines LLM audit records as chronological, tamper-evident lifecycle ledgers
  that connect technical provenance with approvals, waivers, and attestations.
  AttriGuard shows why agent tool invocations need causal attribution rather
  than raw transcripts. PROV-AGENT and the IETF SPICE inference-chain draft show
  how agent workflows and inference events can be exported as verifiable
  provenance chains. LDP delegation contracts and HDP human delegation provenance
  show that multi-agent authority needs explicit scopes, attested identity, and
  append-only delegation history. RDLLM-L152 turns those findings into one
  settlement rule: no append-only audit trail binding provider-wire calls,
  policy versions, actor authority, tool/memory actions, exports, challenges,
  and settlement meters, no grounded display or direct creator settlement.
  https://arxiv.org/abs/2601.20727
  https://arxiv.org/abs/2603.10749
  https://arxiv.org/abs/2508.02866
  https://datatracker.ietf.org/doc/html/draft-mw-spice-inference-chain-00
  https://arxiv.org/abs/2603.18043
  https://arxiv.org/abs/2604.04522

- The L153 pass closes the split-view accountability gap. Certificate
  Transparency/RFC 9162 defines signed tree heads, inclusion proofs, and
  consistency proofs; SCITT/RFC 9943 applies transparency receipts to signed
  supply-chain statements; Sigstore/Rekor shows practical artifact-signature
  transparency; C2SP checkpoint and witness work gives portable checkpoint and
  cosignature formats; transparency-dev's verifiable data-structure work and
  CoSi-style witness cosigning show how independent observers can prevent
  equivocation. RDLLM-L153 turns those mechanisms into an attribution rule: the
  L152 audit-trail checkpoint must be public-log included, consistency-proven,
  continuously monitored, and independently witnessed before users, creators,
  customers, auditors, or regulators can rely on source attribution or direct
  settlement.
  https://www.rfc-editor.org/rfc/rfc9162.html
  https://www.rfc-editor.org/rfc/rfc9943.html
  https://docs.sigstore.dev/logging/overview/
  https://github.com/C2SP/C2SP/
  https://transparency.dev/verifiable-data-structures/
  https://arxiv.org/abs/1503.08768

- The L154 pass closes the grounded-reliance gap. Recent attribution and
  citation work shows that a model can display a plausible source while the
  cited page does not actually support the generated claim; provenance metadata
  alone is not the same as user-safe reliance. DataDignity frames output
  attribution as a ranked source-support problem, Cited-But-Not-Verified and
  RefLens emphasize evidence-grounded citation verification, and ecosystem
  analyses of LLM search attribution show the economic cost of uncredited or
  weakly credited sources. C2PA content credentials, SCITT transparency
  receipts, NIST AI RMF traceability, W3C Data Integrity, and EU AI Act Article
  50-style transparency support the publication layer. RDLLM-L154 turns those
  pieces into a verifier rule: no verified source footer, support coverage,
  locator health, freshness, warrant calibration, client rendering, L153 witness
  root, and finance reconciliation, no user reliance or direct creator payout.
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2605.06635
  https://doi.org/10.1609/aaai.v40i48.42361
  https://doi.org/10.1017/dap.2026.10064
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
  https://www.rfc-editor.org/rfc/rfc9943.html
  https://www.nist.gov/itl/ai-risk-management-framework
  https://www.w3.org/TR/vc-data-integrity/
  https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50

- The L155 pass closes the post-release correction gap. April and May 2026
  citation studies show that citation URLs can be fabricated, stale, or
  non-resolving at scale, and that tool-assisted checking can reduce those
  failures only when correction is part of the serving workflow. FineRef shows
  that citation mismatch and irrelevance need fine-grained reflection and
  correction, while the W3C status-list, C2PA update-manifest/revocation,
  SCITT receipt, RFC 9162, and Rekor patterns show how public status changes can
  be published as verifiable records. RDLLM-L155 turns those findings into a
  post-release verifier rule: no live status row, correction broadcast, stale
  citation revalidation, copied-output status link, cache invalidation, creator
  notice, regulator export notice, and settlement hold or adjustment, no
  continuing reliance on the answer footer or payout claim.
  https://arxiv.org/abs/2604.03173
  https://arxiv.org/abs/2605.07723
  https://ojs.aaai.org/index.php/AAAI/article/view/40547
  https://www.w3.org/TR/vc-bitstring-status-list/
  https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html
  https://www.rfc-editor.org/rfc/rfc9943.html

- The L156 pass closes the cross-provider adoption gap. Recent citation-failure
  and provider-API work shows that source attribution must survive not only
  generation, but also transport through provider-specific response shapes,
  streaming events, SDK metadata, tool calls, gateway transforms, copied outputs,
  and client rendering. RDLLM-L156 turns that into a verifier rule: no
  provider-family adapter, response binding, text-attribution guarantee, client
  gate, source-status resolver, standard mapping, and negative fixture, no
  trusted source footer or direct creator settlement.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2604.03173
  https://modelcontextprotocol.io/specification/2025-11-25
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf

- The L157 pass closes the provider-native fixture gap. L156 says every provider
  route must expose the same attribution contract; L157 requires replay evidence
  that real provider-shaped outputs normalize into it across sync text,
  streaming text, tool calls, retrieval context, batch callbacks, webhooks, and
  copied-output exports. This directly reflects recent findings that citation
  labels can look plausible while unsupported, and that API translation layers,
  SDKs, gateways, streams, and copied outputs can drop provenance unless the
  normalized response fields are verified end to end.
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2605.07723
  https://platform.openai.com/docs/api-reference/responses
  https://docs.anthropic.com/en/api/messages
  https://ai.google.dev/gemini-api/docs/text-generation
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
  https://openrouter.ai/docs/api-reference/chat-completion
  https://cyclonedx.org/capabilities/mlbom/
  https://www.rfc-editor.org/rfc/rfc9162.html
  https://docs.sigstore.dev/logging/overview/

- The L158 pass closes the provider-drift gap. Recent source-attribution
  failures are not static: citation validity, source freshness, API response
  schemas, SDK event fields, model aliases, tool metadata, and streaming footer
  behavior can change after certification. RDLLM-L158 therefore requires
  pre-release, hourly, daily, weekly negative-rotation, and incident-triggered
  canaries over provider schemas, response shapes, citation locators,
  source-footer rendering, telemetry semantics, and settlement meters. A stale
  route loses grounded display and direct creator settlement until remediation
  is published.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.07723
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://modelcontextprotocol.io/specification/2025-06-18/basic/index

- The L159 pass closes the request-time negotiation gap. Provider compatibility
  cannot be inferred from a public profile alone because each call may select a
  different model route, source locator, citation format, privacy policy, copy
  policy, or settlement meter. RDLLM-L159 requires the client and provider route
  to negotiate the attribution contract before invocation; unnegotiated or stale
  requests fail before generation instead of becoming post-hoc citation claims.
  https://modelcontextprotocol.io/specification/2025-06-18/basic/index
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://arxiv.org/abs/2603.27094

- The L160 pass closes the runtime-bypass gap. Negotiation is useful only if the
  selected contract is carried by the actual API call, stream, SDK retry,
  gateway proxy, agent step, MCP tool call, retrieval context, batch callback,
  fallback route, or semantic-cache reuse. RDLLM-L160 makes every invocation
  emit privacy-preserving receipts, telemetry span hashes, response-envelope
  hashes, source-footer hashes, claim-provenance hashes, bypass guards, and
  settlement meters before output display or payout release.
  https://arxiv.org/abs/2603.14283
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://modelcontextprotocol.io/specification/2025-06-18/basic/index

- The L161 pass closes the untrusted-conformance gap. A provider-hosted
  certification page is not enough for source attribution because relying
  parties must know who certified the proof pack, whether the certifier was
  accredited, whether credentials or trust marks are revoked, and whether the
  statement was logged. RDLLM-L161 binds conformance claims to trust anchors,
  accredited certifiers, conformance labs, W3C Verifiable Credentials, C2PA
  conformance practice, SCITT-style transparency statements, revocation status,
  discovery, and relying-party policy.
  https://www.w3.org/standards/history/vc-data-model-2.0/
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
  https://queue.rfc-editor.org/final-review/rfc9943/

- The L162 pass closes the provider-adoption gap. Trust federation still leaves
  implementers asking what to ship. RDLLM-L162 packages the federated trust
  chain with provider-family adapters, standard exports, SDK/gateway contracts,
  OpenTelemetry GenAI mappings, MCP tool/resource contracts, C2PA assertions,
  W3C Verifiable Credential trust marks, SCITT transparency statements,
  creator-audit APIs, regulator exports, and guarded settlement release. No
  adoption pack means no grounded answer claim or direct creator settlement.
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://modelcontextprotocol.io/specification/2025-06-18/basic/index
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
  https://www.w3.org/standards/history/vc-data-model-2.0/
  https://queue.rfc-editor.org/final-review/rfc9943/

- The L163 pass closes the industry-root gap. The latest citation-verification
  papers show that a footer with valid links can still fail factual support, and
  standards work shows that provenance claims must be portable, signed, logged,
  and independently verifiable. RDLLM-L163 therefore binds the L162 adoption
  pack, current proof dependency graph, public verifier endpoints, adoption-role
  obligations, creator audit routes, regulator exports, copied-output status
  links, and fail-closed negative root fixtures into one acyclic public root.
  No verified root means no source-footer confidence signal, copied-output
  reliance, or direct creator settlement.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.07723
  https://arxiv.org/abs/2507.04480
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
  https://www.w3.org/standards/history/vc-data-model-2.0/
  https://queue.rfc-editor.org/final-review/rfc9943/

- The L164 pass closes the installability gap. Recent citation-attribution work
  such as VeriCite, CiteGuard, Source Attribution in RAG, and CUE-R shows that
  source footers need claim verification, retrieval-aware validation, and
  evidence-utility tests rather than link-only presentation. Recent training-data
  attribution work such as DATE-LM, Distributional Training Data Attribution,
  Mechanistic Data Attribution, and the EMNLP 2025 influence-functions critique
  also shows why RDLLM must keep runtime source proof, training influence, and
  payout evidence as separate replay channels. RDLLM-L164 therefore packages the
  L163 root into signed reproducible SDKs, gateway middleware, MCP adapters,
  OpenTelemetry GenAI mappings, OpenAPI contracts, C2PA assertions, W3C VC trust
  marks, SCITT statements, offline verifier containers, CI workflows,
  procurement policies, and SBOM/SLSA provenance. No signed reproducible
  distribution means no provider installation claim, no source-footer reliance,
  and no direct creator settlement release.
  https://arxiv.org/abs/2510.11394
  https://arxiv.org/abs/2510.17853
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2604.05467
  https://arxiv.org/abs/2507.09424
  https://openreview.net/forum?id=UBRFn7YKMe
  https://arxiv.org/abs/2601.21996
  https://aclanthology.org/2025.findings-emnlp.775/
  https://slsa.dev/spec/latest/
  https://in-toto.io/

- The L165 pass closes the live response-attribution gap. Recent work makes clear
  that a correct final answer is not enough: attribution can be wrong, suppressed,
  or merely decorative. Probing for Knowledge Attribution separates context-driven
  answers from parametric memory, CUE-R measures intervention-style evidence
  utility, factual-confidence prediction gates unsupported RAG answers, CiteGuard
  frames citation validation as attribution alignment, FalseCite supplies
  deceptive-citation negative controls, and Attribution Bias names suppression as
  a distinct failure mode. RDLLM-L165 therefore requires every response to bind
  visible footer rows to source identity, claim support, current-turn or memory
  path, causal utility, factual confidence, settlement participation, and
  negative fixtures before release or direct creator settlement.
  https://arxiv.org/abs/2602.22787
  https://arxiv.org/abs/2604.05467
  https://arxiv.org/abs/2605.05244
  https://arxiv.org/abs/2510.17853
  https://arxiv.org/abs/2602.11167
  https://arxiv.org/abs/2604.05224
  https://docs.sigstore.dev/logging/overview/
  https://spec.openapis.org/oas/latest.html
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://modelcontextprotocol.io/specification/2025-06-18/basic/index
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
  https://www.w3.org/TR/vc-data-model-2.0/
  https://scitt.io/

- The L166 pass closes the model-release claim gap. Current foundation-model
  governance and AI supply-chain practice is converging on model-level
  documentation, copyright/TDM transparency, downstream provider documentation,
  signed model provenance, software/model supply-chain attestations, content
  credentials, transparency statements, and runtime telemetry. RDLLM-L166 turns
  those signals into an executable passport for each named model version: no
  passport means no RDLLM model claim, provider invocation claim, source-footer
  reliance, or direct creator settlement for that model release.
  https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai
  https://www.nist.gov/itl/ai-risk-management-framework
  https://openssf.org/blog/2025/06/05/model-signing-is-here/
  https://slsa.dev/spec/latest/
  https://in-toto.io/
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
  https://scitt.io/
  https://opentelemetry.io/docs/specs/semconv/gen-ai/

- The L167 pass closes the fragmented-reliance gap. A provider can no longer
  claim RDLLM by showing a correct-looking footer, a model passport, or a
  settlement report in isolation. The composite contract binds OpenAPI-visible
  routes, MCP or agent-tool calls, OpenTelemetry GenAI spans, C2PA credentials,
  SCITT transparency statements, W3C credentials, SLSA/in-toto provenance,
  OpenSSF model-signing posture, EU GPAI transparency, and NIST AI RMF/GeneAI
  governance into one verifier decision for model claims, invocation, answer
  release, footer reliance, procurement reliance, and creator settlement.
  https://spec.openapis.org/oas/latest.html
  https://modelcontextprotocol.io/
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://spec.c2pa.org/specifications/specifications/2.2/specs/C2PA_Specification.html
  https://scitt.io/
  https://www.w3.org/TR/vc-data-model-2.0/
  https://slsa.dev/spec/latest/
  https://in-toto.io/
  https://openssf.org/blog/2025/06/05/model-signing-is-here/
  https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai
  https://www.nist.gov/itl/ai-risk-management-framework

- The L168 pass closes the named-provider binding gap. AI Transparency Atlas
  reports that model documentation is fragmented across platforms and provider
  docs, while Cited but Not Verified and PaperTrail show that visible citations
  still need source accessibility, relevance, factual support, and claim-evidence
  checks. RDLLM-L168 therefore requires each named provider family and route type
  to publish native API, streaming, tool/MCP, retrieval/citation, source-footer,
  live-proof, telemetry, revocation, copy/export, audit, and settlement mappings
  to the L167 contract before universal provider adoption can be claimed.
  https://arxiv.org/abs/2512.12443
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2602.21045
  https://academic.oup.com/grurint/article/75/3/224/8441974

- The L169 pass closes the executable-provider-evidence gap. Static route
  mappings do not prove that OpenAI-style, Anthropic-style, Google, cloud,
  router, local-runtime, RAG, or MCP/agent paths actually executed the required
  attribution and citation checks. RDLLM-L169 therefore requires an official
  signed runner receipt with fixture-suite rows, runner-stage rows,
  per-provider native transcript hashes, public result hashes, and negative
  canary rejection before provider onboarding, source-footer reliance,
  procurement reliance, or creator settlement can be claimed. Recent source
  attribution work motivates the claim-evidence and citation verification
  suites; OpenTelemetry GenAI motivates portable trace semantics; OpenAPI,
  Arazzo, and MCP motivate machine-readable API/tool replay surfaces; and
  SLSA, in-toto, and SCITT motivate signed runner/test-result attestations and
  transparency publication.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2602.21045
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://spec.openapis.org/oas/
  https://spec.openapis.org/arazzo/latest.html
  https://modelcontextprotocol.io/
  https://slsa.dev/spec/latest/
  https://in-toto.io/
  https://scitt.io/

- The L171 pass closes the final-answer/source-footer gap. A live invocation can
  be admitted while the final answer still carries fabricated citations,
  unsupported claims, unavailable links, wrong-source support, copied output with
  stripped footer rows, or settlement rows for hidden payable sources. RDLLM-L171
  therefore requires a source-grounded response receipt that binds L170
  admission and L165 live attribution to source rows, claim rows, response
  surfaces, citation metadata checks, copy/export preservation, and settlement
  rows before user reliance or creator payout. Cited but Not Verified and
  CiteCheck motivate source retrieval plus citation metadata verification;
  hallucinated-citation studies motivate fail-closed negative fixtures; C2PA
  Content Credentials motivate portable provenance claims for exported answers;
  and DataDignity-style pinpoint provenance motivates ranking and exposing the
  most likely source documents supporting response knowledge.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.27700
  https://arxiv.org/abs/2603.07287

- The L172 pass closes the distribution-survival gap. Even when a response is
  grounded at release time, the footer, source locator, content credential,
  status resolver, revocation snapshot, reuse meter, or settlement obligation can
  be dropped by copy/paste, PDF export, screenshot capture, web embeds, API
  relays, social shares, marketplace exports, or downstream RAG ingestion. The
  universal distribution reliance passport binds L171 and content-credential
  evidence to those surfaces and fails closed when the distributed copy cannot
  resolve current source status or carry settlement obligations forward. This
  extends the same motivation behind Content Credentials and citation-verifier
  work from original answer display to downstream reliance.
  https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html

- The L173 pass closes the adversarial-provenance gap. Recent work argues that
  C2PA-style credentials and watermarking need security analysis, trust-list
  handling, anti-replay controls, and coordination across independent
  verification layers; other work shows provenance/watermarking contradictions
  and RAG poisoning risks when provenance is valid but retrieval context is
  compromised. RDLLM-L173 therefore treats a single footer, manifest,
  credential, watermark, or resolver as insufficient. It requires independent
  provenance signals plus adversarial negative fixtures for manifest
  substitution, signature replay, footer spoofing, locator phishing, resolver
  split views, watermark removal, proxy rewrites, downstream RAG poisoning,
  credential time-shift, creator impersonation, settlement-meter forks, and
  private payload leaks before high-stakes reliance or creator settlement.
  https://arxiv.org/abs/2604.24890
  https://arxiv.org/abs/2603.02378
  https://arxiv.org/abs/2604.00387
  https://c2pa.org/specifications/specifications/2.0/security/Security_Considerations.html
  https://arxiv.org/abs/2605.07723
  https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html
  https://www.microsoft.com/en-us/research/publication/datadignity-training-data-attribution-for-large-language-models/

- The L174 pass closes the procurement and regulatory reliance gap. Recent
  provenance work pushes beyond decorative citations toward claim-evidence
  interfaces; recent training-data attribution work treats source support for
  generated output as a measurable ranking problem; recent legal/evidentiary
  provenance work maps content provenance, watermarking, and attestations to
  court-facing proof requirements; and current policy surfaces such as EU AI
  Act GPAI summaries and U.S. Copyright Office AI reports make training-content,
  copyright, disclosure, and responsibility obligations procurement-relevant.
  RDLLM-L174 therefore turns attribution from a provider self-claim into a
  signed reliance contract: marketplace listing, enterprise procurement,
  regulator export, creator challenge routing, footer survival, source-machine
  readability, correction SLAs, settlement holds, and jurisdiction mappings all
  have to bind to the L173 adversarial provenance quorum, with negative
  fixtures for provider terms overriding creator payment, router bypass,
  missing regulator export, marketplace listing without proof, and source
  footer removal.
  https://arxiv.org/abs/2602.21045
  https://arxiv.org/abs/2605.05687
  https://arxiv.org/abs/2605.21002
  https://digital-strategy.ec.europa.eu/en/factpages/general-purpose-ai-obligations-under-ai-act
  https://www.copyright.gov/ai/
  https://c2pa.org/specifications/specifications/2.0/security/Security_Considerations.html

- The L175 pass closes the provider onboarding and migration gap. Recent
  fabricated-citation audits show that source-looking footers cannot be trusted
  unless the generated citation is verified against real external records;
  PaperTrail and Source Attribution in RAG show that useful attribution must bind
  claim/evidence rows and source utility rather than decorate whole answers; AEX
  shows that provider and gateway APIs need request-output and streaming
  provenance at the boundary; and DataDignity shows that true answer support must
  be separated from lexical or topical resemblance. RDLLM-L175 therefore requires
  each foundation provider family, native API surface, SDK shim, gateway proxy,
  marketplace listing, regulator export, customer migration guide, rollout gate,
  rollback plan, and negative fixture to bind to the L174 reliance contract. A
  provider cannot claim adoption if legacy endpoints omit footers, SDKs strip
  source rows, streaming finals miss receipts, tool outputs are unattributed,
  model aliases drift, proxies bypass enforcement, or private payloads leak in
  migration logs.
  https://arxiv.org/abs/2605.07723
  https://arxiv.org/abs/2603.03299
  https://arxiv.org/abs/2602.21045
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2603.14283
  https://arxiv.org/abs/2605.05687

- The L170 pass closes the production-invocation-admission gap. A provider can
  have a current conformance receipt while an individual live call still bypasses
  the route, model alias, tenant scope, telemetry span, source-footer gate,
  revocation snapshot, tool authorization, or settlement meter. RDLLM-L170
  therefore requires a signed admission decision for each live invocation before
  response release, footer reliance, tool/MCP execution, retrieval reliance, or
  creator settlement. Cited but Not Verified motivates blocking unsupported
  source-footer reliance at response time; OpenTelemetry GenAI motivates
  per-call trace binding; MCP motivates explicit tool/resource authorization;
  OpenAPI and Arazzo motivate machine-readable request/workflow admission; and
  SLSA, in-toto, and SCITT motivate signed verifier artifacts and transparency
  publication for the resulting admission decisions.
  https://arxiv.org/abs/2605.06635
  https://opentelemetry.io/docs/specs/semconv/gen-ai/
  https://modelcontextprotocol.io/
  https://spec.openapis.org/oas/
  https://spec.openapis.org/arazzo/latest.html
  https://slsa.dev/spec/latest/
  https://in-toto.io/
  https://scitt.io/

- The L176 pass closes the dynamic model/provider registry gap. Provider
  onboarding does not cover the rate at which model catalogs, hosted
  open-weight services, marketplace aliases, local runtimes, regional catalogs,
  private deployments, and router/gateway routes change. Current catalog APIs
  expose model IDs, publishers, modalities, limits, and capability metadata, so
  RDLLM now treats each concrete route as a registered service object with
  lifecycle, adapter, source-footer, and settlement metadata. Unregistered
  routes, stale catalogs, silent router fallback, capability overclaims, and
  private payloads fail closed before RDLLM support or settlement is claimed.
  https://docs.github.com/en/rest/models/catalog

- The L177 pass closes the visible source-footer enforcement gap. Recent 2026
  work shows that citation-looking output is not enough: citation hallucinations
  are measurable at scale, deployment constraints can increase fabricated
  references, RAG source attribution needs document-level utility analysis, and
  nugget/evidence-pool RAG designs preserve provenance by carrying structured
  evidence through generation. RDLLM-L177 therefore binds every L176 route to
  source discovery, retrieval trace capture, claim decomposition, evidence-span
  binding, source identity resolution, citation metadata verification,
  counterevidence scanning, no-source abstention, visible and machine-readable
  footer rows, copy/export preservation, and settlement holds before answer
  release. This makes the footer a release gate, not decoration.
  https://arxiv.org/abs/2605.07723
  https://arxiv.org/abs/2603.07287
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2601.13222
  https://arxiv.org/abs/2604.14170

- The L178 pass closes the provider catalog coverage gap. Dynamic provider
  catalogs and model marketplaces can add, rename, deprecate, region-lock, or
  silently route models after a registry is published. RDLLM-L178 therefore
  requires provider endpoints, OpenAI-compatible model lists, cloud catalogs,
  marketplace listings, hosted open-weight registries, routers, private
  catalogs, local runtime manifests, regional catalogs, SDK metadata, billing
  meters, and lifecycle feeds to be exhaustively normalized. Every discovered
  model must either map to an L176 route with L177 footer enforcement or be
  explicitly blocked with settlement held. This turns "works with every model"
  into a replayable catalog-coverage claim rather than a stale hard-coded list.
  https://docs.github.com/en/rest/models/catalog

- The L179 pass closes the live route-binding gap. A provider catalog can be
  complete and still fail at runtime if an SDK, gateway, router, cache layer,
  stream final event, tool callback, or fallback path returns a different model
  than the preflight route. RDLLM-L179 therefore requires request model IDs,
  resolved model IDs, provider response model echoes, route IDs, telemetry spans,
  source-footer route hashes, and settlement-meter route hashes to remain bound
  to the same L178 catalog-covered route. Runtime alias drift, silent fallback,
  stale cache reuse, missing streaming model echoes, and source-footer or meter
  mismatches fail closed before release.

- The L180 pass closes the verified source-footer reliance gap. Recent 2026
  citation audits show that working links and plausible citation strings are
  insufficient: systems need source materialization, metadata fidelity, link
  health, relevance, factual support, claim-evidence matching, and explicit
  accounting for sources used but omitted. RDLLM-L180 therefore binds every
  visible footer row to the L179 runtime route, L177 footer enforcement, L171
  source-grounded response receipt, and L141 citation verification contract.
  A footer row cannot support user confidence, copy/export, or creator
  settlement unless the source resolves or is archived, matches its metadata,
  factually supports the claim, is relevant to the claim, has claim/evidence
  hashes, survives copied output, and passes negative fixtures for fabricated
  citations, wrong-source claims, post-hoc footer insertion, and omitted used
  sources.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.07723
  https://arxiv.org/abs/2605.27700
  https://arxiv.org/abs/2604.03173
  https://arxiv.org/abs/2602.21045
  https://arxiv.org/abs/2604.05467
  https://arxiv.org/abs/2507.04480

- The L181 pass closes the model-capability coverage gap. A route can be
  catalog-covered, runtime-bound, and source-footer verified for text chat while
  other declared surfaces still bypass attribution. RDLLM-L181 therefore requires
  fixture-backed coverage for capabilities, modality pairs, operation surfaces,
  catalog-covered routes, source-footer-or-abstention behavior, settlement-meter
  binding, and negative fail-closed cases before provider capability claims are
  treated as attribution-safe.

- The L182 pass closes the live provider-capability discovery gap. Capability
  support can drift through model renames, endpoint changes, lifecycle retirement,
  region restrictions, pricing/rate-limit changes, and tool or multimodal feature
  changes after L181 fixtures were written. RDLLM-L182 therefore requires fresh
  official or attested provider-source rows, discovery-channel rows, capability
  discovery rows, route discovery rows, and negative live-discovery fixtures
  before source footers, answer release, or creator settlement can rely on a
  provider capability claim.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.07723
  https://arxiv.org/abs/2605.08583
  https://arxiv.org/abs/2605.27700
  https://www.microsoft.com/en-us/research/publication/datadignity-training-data-attribution-for-large-language-models/
  https://platform.openai.com/docs/api-reference/responses
  https://platform.claude.com/docs/en/build-with-claude/citations
  https://ai.google.dev/gemini-api/docs/models
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html

- The L183 pass closes the native source-annotation normalization gap. Even when
  a provider has current capability evidence, its response may encode sources as
  URL annotations, file annotations, document citations, grounding chunks/supports,
  streaming citation deltas, router annotations, RAG contexts, local manifest
  source maps, or media source metadata. RDLLM-L183 therefore requires parser
  fixtures for every native annotation format, normalized footer-field rows,
  route annotation rows, verified footer bindings, and fail-closed negative
  fixtures before the answer can present source footers or release settlement.
  https://platform.openai.com/docs/api-reference/responses/create
  https://platform.openai.com/docs/guides/tools-web-search
  https://platform.openai.com/docs/guides/tools-file-search
  https://platform.claude.com/docs/en/build-with-claude/citations
  https://ai.google.dev/gemini-api/docs/google-search
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html

- The L184 pass closes the claim-evidence footer verification gap identified by
  the newest citation-failure literature. Cited but Not Verified shows that
  working links and relevance can coexist with poor factual support; Verified
  Misguidance / CITETRACE reports structurally misleading citations where real
  accessible sources still fail intent-purpose, source-suitability, or
  answer-source-fidelity checks; PaperTrail argues for claim/evidence mappings
  rather than coarse citations; CiteAudit and the large-scale hallucinated
  citation audit show why fabricated or unsupported references need automated
  verification before they enter scholarly or user-facing outputs. RDLLM-L184
  therefore requires structured citation parsing, materialized cited content,
  claim hashes, evidence spans, source suitability, intent-purpose alignment,
  answer-source fidelity, factual-support verdicts, and fail-closed negative
  fixtures for correct-answer/wrong-source, inaccessible-source, post-hoc
  citation, and private-source-text leakage cases before source-footers can be
  relied on or settlement released.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.28565
  https://arxiv.org/abs/2602.21045
  https://arxiv.org/abs/2602.23452
  https://arxiv.org/abs/2605.07723

- The L185 pass closes the provider-meter normalization gap that appears once
  source-grounded answers have to run across multiple model providers, routers,
  tools, media endpoints, and cache/batch surfaces. Recent attribution work
  reinforces that systems must separate true answer support from topical
  resemblance and citation appearance: CiteCheck verifies citation existence and
  metadata fidelity, DataDignity evaluates whether a source document actually
  supports expressed response knowledge, Source Attribution in RAG studies
  per-source contribution accounting, and CUE-R measures per-evidence utility
  beyond final-answer quality. L185 therefore normalizes provider-native usage
  fields into RDLLM settlement meters for input/output tokens, cached input,
  reasoning or thinking tokens, tool/search units, media units, batch/asynchronous
  units, embeddings/rerank/fine-tune units, hosted-runtime units, pricing
  snapshots, quota/rate-limit surfaces, and provider invoice rows. The official
  provider docs currently expose these meter shapes through OpenAI Responses
  `usage` fields, Anthropic Messages `usage` and prompt-cache counters, Gemini
  `usageMetadata`, Bedrock Converse `usage`, Mistral cached prompt usage, Cohere
  `billed_units`, xAI OpenAI-compatible usage and cached-token details, and
  OpenRouter pass-through usage/cost accounting.
  https://arxiv.org/abs/2605.27700
  https://www.microsoft.com/en-us/research/publication/datadignity-training-data-attribution-for-large-language-models/
  https://arxiv.org/abs/2507.04480
  https://arxiv.org/abs/2604.05467
  https://platform.openai.com/docs/api-reference/responses
  https://docs.anthropic.com/en/api/messages
  https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
  https://ai.google.dev/api/generate-content
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
  https://docs.mistral.ai/studio-api/conversations/advanced/prompt-caching
  https://docs.cohere.com/docs/how-does-cohere-pricing-work
  https://docs.x.ai/developers/advanced-api-usage/prompt-caching/usage-and-pricing
  https://openrouter.ai/docs/cookbook/administration/usage-accounting

- The L186 pass closes the provider response-state gap between a cited answer and
  a reliable cited answer. Recent work supports treating citations as
  claim/evidence objects, not decorative footnotes: Citation-Closure Retrieval
  and Per-Rule Attribution requires source-bound rule attribution, PaperTrail
  decomposes answers and evidence into discrete claims to expose unsupported
  assertions, Cited but Not Verified reports that link validity can remain high
  while factual support is much lower, and SourceCheckup finds many cited medical
  answers are not fully source-supported. L186 therefore requires provider-native
  terminal states to be normalized before the answer footer can imply grounded
  reliance: OpenAI `status`, `incomplete_details`, refusals, and
  `finish_reason`; Anthropic `stop_reason` and streaming refusals; Gemini
  `promptFeedback`, `blockReason`, and `safetyRatings`; Bedrock `stopReason` and
  guardrail traces; Azure OpenAI content-filter results; Mistral guardrails;
  Cohere finish reasons and safety errors; xAI/OpenAI-compatible refusal and
  finish states; OpenRouter `finish_reason`/`native_finish_reason`; router
  errors; local runtime exits; and streaming final events. Blocked, refused,
  filtered, truncated, tool-only, errored, or unknown terminal states must hold
  answer release, footer reliance, and creator settlement until the response is
  either regenerated with support or publicly labeled as an abstention/refusal.
  https://arxiv.org/abs/2605.29742
  https://arxiv.org/abs/2602.21045
  https://arxiv.org/abs/2605.06635
  https://www.nature.com/articles/s41467-025-58551-6
  https://arxiv.org/abs/2504.01032
  https://platform.openai.com/docs/api-reference/responses
  https://platform.openai.com/docs/api-reference/chat/object
  https://docs.anthropic.com/en/api/messages
  https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/handle-refusals
  https://ai.google.dev/api/generate-content
  https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
  https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-converse-api.html
  https://learn.microsoft.com/azure/ai-foundry/openai/how-to/content-filters
  https://docs.mistral.ai/api/
  https://docs.cohere.com/reference/chat
  https://docs.x.ai/docs/api-reference
  https://openrouter.ai/docs/api-reference/chat-completion

- The July 2026 runtime pass applies the same citation-faithfulness lesson to the
  default engine path. External attribution now discovers sources from the
  generated output body rather than from prompt intent alone, so a topical prompt
  cannot cause unrelated retrieved works to appear in the user footer. Footer
  rows are emitted only for output-supported sources, carry visible claim counts,
  support scores, payout amounts, content hashes, and confidence labels, and each
  claim-evidence row exposes a claim hash plus exact evidence-span hash. This
  implements the practical lesson from recent source-attribution work: users need
  a footer that says which work supports which answer claim, not a decorative list
  of plausible citations or a hidden payout ledger.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2601.05866
  https://arxiv.org/abs/2510.17853
  https://arxiv.org/abs/2605.27700
  https://www.cambridge.org/core/journals/data-and-policy/article/attribution-crisis-in-llm-search-results-estimating-ecosystem-exploitation/170DD0B88E5F5AEA8F69F2E9AF1328E3
  https://aclanthology.org/2025.findings-acl.1087/

- The July 2026 public-surface privacy pass separates answer grounding from
  private payload publication. Cited but Not Verified shows that end-user trust
  depends on retrievable, fact-checked citations; CiteCheck and CiteAudit show
  that citation identity and metadata fidelity must be externally verified; and
  A Human-Centric Framework for Data Attribution in LLMs argues that creator,
  user, platform, and intermediary goals must be negotiated rather than collapsed
  into a single payout metric. RDLLM therefore treats public source footers as
  selective-disclosure artifacts: they show source labels, titles, URIs, support
  scores, claim counts, hashes, verifier handles, and settlement commitments,
  while hosted public artifacts are audited to exclude prompts, raw source text,
  private reasoning, secrets, customer records, payment details, and payout
  account data.
  https://arxiv.org/abs/2605.06635
  https://arxiv.org/abs/2605.27700
  https://arxiv.org/abs/2602.23452
  https://arxiv.org/abs/2602.10995

- The July 2026 attribution-metric pass adds a release rule for evaluation
  claims: no single automatic attribution scorer should be treated as a
  universal grounding proxy. Do LLM Attribution Metrics Transfer? reports that
  scorer rankings invert across generated-answer attribution datasets and that
  metric choice must be validated against the target construct and domain.
  RDLLM therefore treats claim support, source materialization, footer
  rendering, confidence calibration, and payout attribution as separately
  verified channels rather than collapsing them into one score.
  https://arxiv.org/abs/2606.23915

- The July 2026 influence-attribution pass keeps user-facing source footers
  separate from model/training influence evidence. TokenTrace shows that
  generated media can require multi-concept influence attribution through
  watermark recovery, while RDLLM's answer footer is a runtime claim/evidence
  and settlement surface. Implementations should not use footer rows as a
  substitute for training-data influence receipts, and should not use influence
  signals alone to imply that a displayed answer claim is source-grounded.
  https://arxiv.org/abs/2602.19019
