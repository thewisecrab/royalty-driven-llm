# البدء السريع في RDLLM

RDLLM طبقة open source لإسناد مصادر إجابات الذكاء الاصطناعي وحساب حقوق
المبدعين. توضح أي مصادر تدعم الإجابة، ومقدار مساهمة كل مصدر ظاهر في الناتج،
وهل يمكن عرض الإجابة على أنها grounded.

## تشغيل عرض محلي

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

ابحث عن هذه الحقول:

- `Sources`
- `Claim Evidence`
- `support`
- `text_match`
- `payout`
- `disagreement=passed`

## تشغيل الخدمة

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

بعد ذلك استدع `/v1/attribute` باستخدام curl أو
[أمثلة عملاء API](../../../examples/api_clients/README.md).

## التحقق قبل العرض

احفظ JSON الخاص بالاستجابة والنص المنسوخ الذي سيراه المستخدم، ثم شغل:

```bash
PYTHONPATH=src python3 tools/service_response_verify.py --response /tmp/rdllm-response.json --display-text /tmp/rdllm-display.txt
PYTHONPATH=src python3 tools/source_footer_verify.py --footer /tmp/rdllm-footer.json --display-text /tmp/rdllm-display.txt
```

اعرض الإجابة على أنها grounded فقط عندما تكون `production_display_ready` true
وتكون `source_grounding_acceptance` passed.

المزيد:
[explainer](explainer.md),
[دليل البداية على GitHub](../../github_start_here.md) و
[README](../../../README.md).
