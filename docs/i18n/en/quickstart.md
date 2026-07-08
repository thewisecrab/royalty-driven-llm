# RDLLM Quickstart

RDLLM is an open-source attribution and royalty layer for AI answers. It shows
which sources support an answer, how much visible source usage contributed to
the output, and whether the answer can be displayed as grounded.

## Run A Local Demo

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

Look for:

- `Sources`
- `Claim Evidence`
- `support`
- `text_match`
- `payout`
- `disagreement=passed`

## Run The Service

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

Then call `/v1/attribute` from curl or from the
[API client examples](../../../examples/api_clients/README.md).

## Verify Before Display

Save the response JSON and copied answer text, then run:

```bash
PYTHONPATH=src python3 tools/service_response_verify.py --response /tmp/rdllm-response.json --display-text /tmp/rdllm-display.txt
PYTHONPATH=src python3 tools/source_footer_verify.py --footer /tmp/rdllm-footer.json --display-text /tmp/rdllm-display.txt
```

Only display the answer as grounded when `production_display_ready` is true and
`source_grounding_acceptance` is passed.

More: [explainer](explainer.md),
[GitHub start guide](../../github_start_here.md), and
[README](../../../README.md).
