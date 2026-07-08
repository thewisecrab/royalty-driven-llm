# Inicio rapido de RDLLM

RDLLM es una capa open source de atribucion y royalties para respuestas de IA.
Muestra que fuentes respaldan una respuesta, cuanto contribuyo cada fuente
visible al resultado y si la respuesta puede mostrarse como fundamentada.

## Ejecutar una demo local

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

Busca estos campos:

- `Sources`
- `Claim Evidence`
- `support`
- `text_match`
- `payout`
- `disagreement=passed`

## Ejecutar el servicio

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

Despues llama a `/v1/attribute` con curl o con los
[ejemplos de clientes API](../../../examples/api_clients/README.md).

## Verificar antes de mostrar

Guarda el JSON de respuesta y el texto copiado que vera el usuario. Despues
ejecuta:

```bash
PYTHONPATH=src python3 tools/service_response_verify.py --response /tmp/rdllm-response.json --display-text /tmp/rdllm-display.txt
PYTHONPATH=src python3 tools/source_footer_verify.py --footer /tmp/rdllm-footer.json --display-text /tmp/rdllm-display.txt
```

Muestra la respuesta como fundamentada solo cuando `production_display_ready` es
true y `source_grounding_acceptance` esta passed.

Mas informacion: [explainer](explainer.md),
[guia de inicio en GitHub](../../github_start_here.md) y
[README](../../../README.md).
