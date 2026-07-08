# RDLLM त्वरित शुरुआत

RDLLM AI उत्तरों के लिए एक open-source attribution और royalty layer है। यह
दिखाता है कि कौन से sources उत्तर को support करते हैं, visible source usage ने
output में कितना योगदान दिया, और उत्तर grounded रूप में दिखाने योग्य है या नहीं।

## Local demo चलाएं

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

इन fields को देखें:

- `Sources`
- `Claim Evidence`
- `support`
- `text_match`
- `payout`
- `disagreement=passed`

## Service चलाएं

```bash
export RDLLM_SERVICE_TOKEN="${RDLLM_SERVICE_TOKEN:-rdllm-local-dev-token}"
export RDLLM_SERVICE_TOKEN_SHA256="$(python - <<'PY'
import hashlib
import os
print(hashlib.sha256(os.environ["RDLLM_SERVICE_TOKEN"].encode()).hexdigest())
PY
)"
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

इसके बाद curl या
[API client examples](../../../examples/api_clients/README.md)
से `/v1/attribute` call करें।

## Display से पहले verify करें

Response JSON और copied user-visible text save करें, फिर चलाएं:

```bash
PYTHONPATH=src python3 tools/service_response_verify.py --response /tmp/rdllm-response.json --display-text /tmp/rdllm-display.txt
PYTHONPATH=src python3 tools/source_footer_verify.py --footer /tmp/rdllm-footer.json --display-text /tmp/rdllm-display.txt
```

Answer को grounded तभी दिखाएं जब `production_display_ready` true हो और
`source_grounding_acceptance` passed हो।

और पढ़ें:
[explainer](explainer.md),
[GitHub start guide](../../github_start_here.md) और
[README](../../../README.md)।
