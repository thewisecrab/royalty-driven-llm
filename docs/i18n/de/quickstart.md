# RDLLM Schnellstart

RDLLM ist eine Open-Source-Schicht fuer Attribution und Royalties in
KI-Antworten. Sie zeigt, welche sources eine Antwort stuetzen, wie stark visible
source usage zum Output beigetragen hat und ob die Antwort als grounded angezeigt
werden darf.

## Lokale Demo

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

Achten Sie auf `Sources`, `Claim Evidence`, `support`, `text_match`, `payout`
und `disagreement=passed`.

## Service

```bash
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

Rufen Sie danach `/v1/attribute` mit curl oder den
[API examples](../../../examples/api_clients/README.md) auf.

## Verifikation

Vor dem public display `service_response_verify.py` und `source_footer_verify.py`
ausfuehren. Nur als grounded anzeigen, wenn `production_display_ready` true ist
und `source_grounding_acceptance` passed ist.

Mehr: [explainer](explainer.md).

