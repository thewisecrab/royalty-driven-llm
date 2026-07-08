# RDLLM समझाया गया

## ELI5

AI answer को school report की तरह सोचें। RDLLM AI से दिखवाता है कि उसने कौन सी
books या sources इस्तेमाल किए, कौन सा sentence किस source से support हुआ, और
उन sources के creators को credit या payment मिलना चाहिए या नहीं। अगर proof
missing है, तो answer को fully sourced नहीं दिखाना चाहिए।

## Simple

RDLLM AI products के लिए एक open-source layer है। यह answer में visible source
footer जोड़ता है, check करता है कि sources सच में claims को support करते हैं,
और source usage को payout या escrow से जोड़ता है।

इसे chatbot, RAG app, search assistant, agent, model API, marketplace या
creator platform में इस्तेमाल करें, जब users को यह दिखाना हो कि answer कहां से
आया।

## Non-Technical

RDLLM तीन groups की मदद करता है:

- Users को bare AI answer के बजाय sources, Claim Evidence और confidence signals
  मिलते हैं।
- Creators और publishers को attribution evidence और settlement records मिलते
  हैं।
- Operators answer को grounded या royalty-bearing दिखाने से पहले verification
  gates चला सकते हैं।

System यह claim नहीं करता कि वह model के hidden thoughts पढ़ सकता है। यह
observable evidence report करता है: visible source support, answer-source
overlap, Claim Evidence, source-disagreement checks और payout allocation।

## Technical

Runtime पर RDLLM answer, source references और revenue context लेता है। यह source
footer बनाता है जिसमें source rows और Claim Evidence rows होती हैं। हर claim
row में claim hash, support score, evidence span hash, character offsets,
evidence preview, warrant status, source-disagreement status और source label
होता है।

Display से पहले verifiers display hash, footer hash, row hashes, source usage
metrics, Claim Evidence, citation markers, answer links, claim-source closure,
model-reliance wording, attribution-gap closure और source disagreement फिर से
compute करते हैं। Answer public-facing तभी है जब `production_display_ready`
true हो और `source_grounding_acceptance` passed हो।

Implementation के लिए यहां से शुरू करें:

- [Quickstart](quickstart.md)
- [GitHub Start Here](../../github_start_here.md)
- [Live use cases](../../../examples/live_use_cases/README.md)
- [API client examples](../../../examples/api_clients/README.md)

