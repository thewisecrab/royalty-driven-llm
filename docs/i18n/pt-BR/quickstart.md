# Inicio rapido do RDLLM

RDLLM e uma camada open source de atribuicao e royalties para respostas de IA.
Ela mostra quais fontes sustentam a resposta, quanto o uso visivel de fontes
contribuiu para o resultado e se a resposta pode ser exibida como grounded.

## Demo local

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

Procure `Sources`, `Claim Evidence`, `support`, `text_match`, `payout` e
`disagreement=passed`.

## Servico

```bash
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

Depois chame `/v1/attribute` com curl ou com os
[exemplos de API](../../../examples/api_clients/README.md).

## Verificacao

Antes do display publico, rode `service_response_verify.py` e
`source_footer_verify.py`. Mostre como grounded apenas quando
`production_display_ready` for true e `source_grounding_acceptance` for passed.

Leia tambem: [explainer](explainer.md).

