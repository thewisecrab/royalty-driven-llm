# Demarrage rapide RDLLM

RDLLM est une couche open source d'attribution et de royalties pour les reponses
d'IA. Elle montre quelles sources soutiennent une reponse, comment l'usage des
sources contribue au resultat, et si la reponse peut etre affichee comme
grounded.

## Demo locale

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

Verifiez `Sources`, `Claim Evidence`, `support`, `text_match`, `payout` et
`disagreement=passed`.

## Service

```bash
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

Appelez ensuite `/v1/attribute` avec curl ou les
[exemples API](../../../examples/api_clients/README.md).

## Verification

Avant l'affichage public, executez `service_response_verify.py` et
`source_footer_verify.py`. Affichez la reponse comme grounded seulement si
`production_display_ready` est true et `source_grounding_acceptance` est passed.

Lire aussi: [explainer](explainer.md).

