# RDLLM 빠른 시작

RDLLM은 AI 답변을 위한 open source attribution 및 royalty layer입니다. 어떤
sources가 답변을 지원하는지, visible source usage가 output에 얼마나 기여했는지,
답변을 grounded로 표시할 수 있는지 보여줍니다.

## Local demo

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

`Sources`, `Claim Evidence`, `support`, `text_match`, `payout`,
`disagreement=passed`를 확인하세요.

## Service

```bash
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

그 다음 curl 또는 [API examples](../../../examples/api_clients/README.md)로
`/v1/attribute`를 호출하세요.

## Verify

Public display 전에 `service_response_verify.py`와 `source_footer_verify.py`를
실행하세요. `production_display_ready`가 true이고
`source_grounding_acceptance`가 passed일 때만 grounded로 표시하세요.

더 보기: [explainer](explainer.md).

