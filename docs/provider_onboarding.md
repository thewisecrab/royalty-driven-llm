# Provider Onboarding

RDLLM is provider-neutral by design. A provider does not need a bespoke payout
formula; it needs an adapter that maps native provider behavior into the public
RDLLM contracts and fails closed when the mapping is incomplete.

See `docs/provider_compatibility_matrix.md` for the current provider-family
coverage, required native capabilities, meter surfaces, and response-state
surfaces.

Provider-family names must resolve through the canonical taxonomy in
`rdllm.provider_family_registry`. Current provider-facing contracts use canonical
families such as `openai_responses`, `google_gemini_generate_content`,
`google_vertex_ai`, `aws_bedrock`, `openrouter_compatible`,
`local_open_weight_runtime`, `rag_native_provider`, and
`mcp_agent_tool_runtime`. Legacy labels are allowed only when
`tools/provider_family_audit.py` maps them to a canonical family without gaps.

## Required Provider Evidence

Every provider route must publish or bind:

- model/provider identity and alias resolution
- native request and response mapping
- streaming event mapping
- tool call and MCP mapping, if supported
- source annotation or explicit abstention mapping
- claim-evidence footer verification
- response-state normalization
- usage, cache, tool, media, batch, invoice, quota, and price meter mapping
- telemetry and audit trail mapping
- revocation, refusal, and safety state mapping
- creator settlement gate mapping

## Minimum Contract Path

For a new provider family or model route, implement the following path:

1. Add the provider family to the composite adapter and binding matrix when it is
   not already represented by an OpenAI-compatible, cloud, router, local-runtime,
   RAG, or MCP/agent family.
2. Map native citations and grounding metadata into
   `rdllm-universal-native-source-annotation-contract/v1`.
3. Verify every rendered source row with
   `rdllm-universal-claim-evidence-footer-verification-contract/v1`.
4. Map native usage and billing units into
   `rdllm-universal-provider-meter-normalization-contract/v1`.
5. Map native terminal states into
   `rdllm-universal-provider-response-state-normalization-contract/v1`.
6. Run provider conformance fixtures and drift sentinels.
7. Publish the provider card, discovery manifest, integration profile, assurance
   bundle, proof dependency graph, and certification report.

## Service Route Path

For OpenAI-compatible chat-completions providers, the runtime service can call
the provider directly through `POST /v1/provider/attribute`. Add a `providers[]`
entry to the service config with:

- `provider_id`
- `family: openai_compatible_chat`
- `base_url`
- `model`
- `api_key_env`
- timeout and maximum response bytes

The service refuses provider-backed attribution when the route is not allowlisted
or the configured API-key environment variable is missing. Provider responses are
hash-bound before RDLLM attribution, and content-filter or tool-call terminal
states fail closed before source-footer reliance or creator settlement.
Runtime readiness also blocks provider routes that still use packaged
placeholders such as `replace-with-provider-model` or reserved `.example` base
URLs, even when an API-key environment variable is present.

Run the live mock-provider smoke before binding a real provider key:

```bash
PYTHONPATH=src python tools/provider_live_smoke.py
```

## Response-State Rule

A response can be displayed as grounded only when the normalized response state is
`complete_supported`. All other states must either block answer release or be
publicly labeled as an abstention/refusal without source-footer reliance or
creator settlement release.

Examples of states that fail closed:

- safety block rendered as an answer
- hidden refusal
- content-filter finish ignored
- max-token truncation treated as complete
- tool-call finish rendered as natural-language answer
- incomplete stream committed
- provider error treated as model answer
- guardrail intervention hidden
- unknown finish reason allowed
- fallback response without state reset

## Meter Rule

Settlement cannot release from provider usage alone. Native meters must normalize
into RDLLM settlement rows that bind route, model, request, usage category,
pricing snapshot, invoice evidence, and creator-settlement gates.

## Source-Footer Rule

A visible source footer is not evidence by itself. A footer row must bind to
materialized source content, claim-level evidence, source suitability, answer
fidelity, factual support, link health, native annotation mapping, response-state
eligibility, and settlement policy.

## Adding a New Provider

Use existing artifacts as templates:

- `artifacts/composite_foundation_adapter_input.json`
- `artifacts/foundation_provider_conformance_input.json`
- `artifacts/foundation_runtime_adapter_input.json`
- `artifacts/universal_foundation_provider_binding_matrix_input.json`
- `artifacts/universal_provider_meter_normalization_contract_input.json`
- `artifacts/universal_provider_response_state_normalization_contract_input.json`

Then run:

```bash
PYTHONPATH=src python tools/provider_family_audit.py
PYTHONPATH=src python tools/regenerate_reference_artifacts.py
PYTHONPATH=src python tools/ship_check.py
```

Do not claim universal support for a provider route until the route passes the
adapter, conformance, meter, response-state, footer, discovery, and certification
checks.
