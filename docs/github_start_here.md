# RDLLM GitHub Start Here

RDLLM is an open-source source-attribution and creator-royalty layer for AI
answers. It helps an AI product show which sources support an answer, how much
each visible source contributed to the output, whether the answer is safe to
display as grounded, and whether value should be paid to creators or held in
escrow.

Use this page when you are new to the repository and want the shortest working
path from clone to a verified source footer.

## If You Only Do One Thing

```bash
python -m pip install .
rdllm-first-run
```

Expected first line:

```text
rdllm_first_run status: passed
```

For a slower copy/paste walkthrough, use [First 5 Minutes](first_5_minutes.md).

## Choose Your Explanation Depth

Start with the [public explainer](public_explainer.md) if you want RDLLM in four
layers: ELI5, Simple, Non-Technical, and Technical. It is available in 15
languages.

Use the [project attribution map](project_attribution.md) if you want to audit
what RDLLM was built from: papers, standards, source code, runtime examples,
schemas, proof artifacts, and verification commands.

Use the [white paper](../paper/rdllm_white_paper.md) if you want the full
state-of-the-art concept paper: attribution problem, current research evidence,
runtime architecture, allocation mechanism, threat model, and public-readiness
requirements.

## Who This Is For

- AI app builders adding source footers to chat, search, RAG, agent, or creative
  tools.
- Model providers and API platforms that need a provider-neutral attribution
  receipt.
- Creator platforms, marketplaces, and publishers that need source usage,
  payout, or escrow evidence.
- Beginners and vibe coders who want copyable commands before reading the full
  mechanism spec.

## Start In 3 Commands

```bash
python -m pip install .
rdllm-first-run
rdllm-operator-doctor
```

Then try the live CLI example or bootstrap an operator directory:

```bash
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
rdllm-operator-bootstrap --output-dir .rdllm/operator --operator-template company --operator-name "Local RDLLM" --security-contact security@example.com --include-sample-corpus --include-reference-artifacts
```

The answer prints inline source labels such as `[S1]`, visible source rows, and
Claim Evidence rows with support scores, evidence span hashes, source
disagreement status, and payout allocation.

## Live Use Cases

- [Runtime use cases](../examples/live_use_cases/README.md) show 15 copyable
  commands plus live screenshots for first run, CLI source footers, service
  verification, provider smoke, package smoke, and public release gates.
- [API client examples](../examples/api_clients/README.md) show standard-library
  implementations in JavaScript, Python, TypeScript, Java, and C#.
- [Adopter quickstart](adopter_quickstart.md) shows the rootless production path
  for individuals, companies, institutions, governments, and public-sector
  operators.
- [Service API](service_api.md) documents `/readyz`, `/v1/attribute`,
  `/v1/provider/attribute`, metrics, audit logs, and display verification.

## Multilingual Quickstarts

These concise quickstarts cover 15 public documentation entry points for the
repository. The first set follows 2026 total-speaker rankings; the expanded set
adds widely used developer and regional languages.

- [English](i18n/en/quickstart.md)
- [Simplified Chinese](i18n/zh-Hans/quickstart.md)
- [Hindi](i18n/hi/quickstart.md)
- [Spanish](i18n/es/quickstart.md)
- [Arabic](i18n/ar/quickstart.md)
- [French](i18n/fr/quickstart.md)
- [Bengali](i18n/bn/quickstart.md)
- [Portuguese](i18n/pt-BR/quickstart.md)
- [Indonesian](i18n/id/quickstart.md)
- [Urdu](i18n/ur/quickstart.md)
- [Russian](i18n/ru/quickstart.md)
- [German](i18n/de/quickstart.md)
- [Japanese](i18n/ja/quickstart.md)
- [Korean](i18n/ko/quickstart.md)
- [Vietnamese](i18n/vi/quickstart.md)

Each language also has a matching explainer:
[English](i18n/en/explainer.md),
[Simplified Chinese](i18n/zh-Hans/explainer.md),
[Hindi](i18n/hi/explainer.md),
[Spanish](i18n/es/explainer.md), and
[Arabic](i18n/ar/explainer.md),
[French](i18n/fr/explainer.md),
[Bengali](i18n/bn/explainer.md),
[Portuguese](i18n/pt-BR/explainer.md),
[Indonesian](i18n/id/explainer.md),
[Urdu](i18n/ur/explainer.md),
[Russian](i18n/ru/explainer.md),
[German](i18n/de/explainer.md),
[Japanese](i18n/ja/explainer.md),
[Korean](i18n/ko/explainer.md), and
[Vietnamese](i18n/vi/explainer.md).

## Implementation Languages

The API examples prioritize common implementation languages for AI products:
JavaScript, Python, TypeScript, Java, and C#. Stack Overflow's 2025 Developer
Survey reports JavaScript, Python, TypeScript, Java, and C# among the most-used
general-purpose programming languages for professional developers after removing
markup-only, query-only, and shell-only entries from the broader
programming/scripting/markup table.

## What The User Sees

A grounded answer is not just a paragraph with a citation. The display surface
includes:

- source labels in the answer, such as `[S1]`;
- source rows with title, creator, URI, support, text match, payout, and content
  hash prefix;
- Claim Evidence rows with claim hash, support score, evidence span, warrant
  status, source-disagreement status, and visible evidence preview;
- verifier handles and hashes that survive copy/export.

Short runtime excerpt:

```text
Claim Evidence
[C1] S1; claim_hash=399e7ff82b80; support=0.900; span=399e7ff82b80; chars=0-64. disagreement=passed; agreements=S1; conflicts=none; disagreement_profile=rdllm-visible-source-disagreement/v1. Evidence: Every royalty bearing AI answer should have a provenance record.
```

## What The Verifier Proves

The verifier checks that:

- `source_grounding_acceptance` is passed before production display;
- the answer text is bound to the source footer;
- source rows match event source references;
- every supported claim has a matching Claim Evidence row;
- citation-shaped answer markers resolve to verified footer rows;
- answer links resolve to verified source URIs;
- source usage metrics are visible and use the declared metric profile;
- model-reliance claims are limited to observable support/allocation data unless
  provider telemetry is separately verified;
- visible source disagreement fails production display through
  `claim_source_disagreement_status`.

## SEO And GEO Notes

For search engines, this repository keeps the first page crawlable and
descriptive: direct headings, local links, a static `docs/index.html`, release
metadata, license files, and copyable commands. For generative engines, the docs
use citation-friendly source rows, short summaries, and explicit field
definitions so answer systems can quote the project accurately instead of
guessing from code names.

The GEO-specific rule for this project is the same as the product rule: do not
optimize for being cited by overstating what RDLLM proves. The public docs say
RDLLM reports observable source support and settlement allocation; hidden
model-internal reliance is claimed only when provider telemetry is separately
verified.

Primary references:

- Stack Overflow Developer Survey 2025: https://survey.stackoverflow.co/2025/technology
- Google Search Central SEO Starter Guide: https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- GEO paper: https://arxiv.org/abs/2311.09735
- Language-speaker basis: https://en.wikipedia.org/wiki/List_of_languages_by_total_number_of_speakers

## Next Docs

- [README](../README.md)
- [First 5 Minutes](first_5_minutes.md)
- [Public explainer](public_explainer.md)
- [Project attribution map](project_attribution.md)
- [White paper](../paper/rdllm_white_paper.md)
- [Mechanism](mechanism.md)
- [Recent research](recent_research.md)
- [Operator runbook](operator_runbook.md)
- [Release checklist](release_checklist.md)
