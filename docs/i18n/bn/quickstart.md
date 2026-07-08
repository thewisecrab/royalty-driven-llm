# RDLLM দ্রুত শুরু

RDLLM হল AI উত্তরের জন্য open source attribution এবং royalty layer। এটি দেখায়
কোন sources উত্তরকে support করে, visible source usage কতটা output-এ অবদান রাখে,
এবং উত্তরটি grounded হিসেবে দেখানো যাবে কি না।

## Local demo

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

দেখুন: `Sources`, `Claim Evidence`, `support`, `text_match`, `payout`,
`disagreement=passed`।

## Service

```bash
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

এরপর curl বা [API examples](../../../examples/api_clients/README.md) দিয়ে
`/v1/attribute` call করুন।

## Verify

Public display-এর আগে `service_response_verify.py` এবং `source_footer_verify.py`
চালান। `production_display_ready` true এবং `source_grounding_acceptance` passed
হলে তবেই grounded হিসেবে দেখান।

আরও পড়ুন: [explainer](explainer.md)।

