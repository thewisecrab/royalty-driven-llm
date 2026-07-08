# RDLLM クイックスタート

RDLLM は AI の回答に source attribution と royalty を追加する open source
layer です。どの sources が回答を支えるか、visible source usage がどれ
だけ output に貢献したか、回答を grounded として表示できるかを示します。

## Local demo

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

`Sources`, `Claim Evidence`, `support`, `text_match`, `payout`,
`disagreement=passed` を確認します。

## Service

```bash
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

その後 curl または [API examples](../../../examples/api_clients/README.md)
で `/v1/attribute` を呼び出します。

## Verify

Public display の前に `service_response_verify.py` と
`source_footer_verify.py` を実行します。`production_display_ready` が true
で `source_grounding_acceptance` が passed の場合だけ grounded として表示
します。

詳細: [explainer](explainer.md)。

