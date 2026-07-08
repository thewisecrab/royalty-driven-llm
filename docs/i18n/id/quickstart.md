# Mulai Cepat RDLLM

RDLLM adalah layer open source untuk atribusi dan royalti jawaban AI. RDLLM
menunjukkan sumber mana yang mendukung jawaban, seberapa besar kontribusi source
usage yang terlihat, dan apakah jawaban aman ditampilkan sebagai grounded.

## Demo lokal

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

Cari `Sources`, `Claim Evidence`, `support`, `text_match`, `payout`, dan
`disagreement=passed`.

## Service

```bash
PYTHONPATH=src python3 -m rdllm.service --config examples/service_config.json
```

Lalu panggil `/v1/attribute` dengan curl atau
[contoh API](../../../examples/api_clients/README.md).

## Verifikasi

Sebelum public display, jalankan `service_response_verify.py` dan
`source_footer_verify.py`. Tampilkan sebagai grounded hanya jika
`production_display_ready` true dan `source_grounding_acceptance` passed.

Baca juga: [explainer](explainer.md).

