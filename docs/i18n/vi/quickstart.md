# Bat dau nhanh RDLLM

RDLLM la layer open source cho attribution va royalty cua cau tra loi AI. No cho
biet sources nao support cau tra loi, visible source usage dong gop bao nhieu
vao output, va cau tra loi co the hien thi nhu grounded hay khong.

## Local demo

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

Kiem tra `Sources`, `Claim Evidence`, `support`, `text_match`, `payout`,
`disagreement=passed`.

## Service

```bash
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

Sau do goi `/v1/attribute` bang curl hoac
[API examples](../../../examples/api_clients/README.md).

## Verify

Truoc public display, chay `service_response_verify.py` va
`source_footer_verify.py`. Chi hien thi nhu grounded khi `production_display_ready`
la true va `source_grounding_acceptance` la passed.

Doc tiep: [explainer](explainer.md).

