# Быстрый старт RDLLM

RDLLM - open source слой атрибуции и роялти для AI-ответов. Он показывает, какие
sources поддерживают ответ, какой вклад внесло visible source usage, и можно ли
показывать ответ как grounded.

## Локальная демо

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

Проверьте `Sources`, `Claim Evidence`, `support`, `text_match`, `payout` и
`disagreement=passed`.

## Service

```bash
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

Затем вызовите `/v1/attribute` через curl или
[API examples](../../../examples/api_clients/README.md).

## Проверка

Перед public display запустите `service_response_verify.py` и
`source_footer_verify.py`. Показывайте ответ как grounded только если
`production_display_ready` true и `source_grounding_acceptance` passed.

Подробнее: [explainer](explainer.md).

