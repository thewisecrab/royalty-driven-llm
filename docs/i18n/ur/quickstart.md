# RDLLM فوری آغاز

RDLLM AI جوابات کے لیے open source attribution اور royalty layer ہے۔ یہ دکھاتا
ہے کہ کون سے sources جواب کو support کرتے ہیں، visible source usage نے output
میں کتنا حصہ ڈالا، اور جواب grounded کے طور پر دکھایا جا سکتا ہے یا نہیں۔

## Local demo

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

یہ fields دیکھیں: `Sources`, `Claim Evidence`, `support`, `text_match`,
`payout`, `disagreement=passed`۔

## Service

```bash
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

پھر curl یا [API examples](../../../examples/api_clients/README.md) سے
`/v1/attribute` call کریں۔

## Verify

Public display سے پہلے `service_response_verify.py` اور `source_footer_verify.py`
چلائیں۔ Answer کو grounded صرف تب دکھائیں جب `production_display_ready` true ہو
اور `source_grounding_acceptance` passed ہو۔

مزید پڑھیں: [explainer](explainer.md)۔

