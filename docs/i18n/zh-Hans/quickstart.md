# RDLLM 快速开始

RDLLM 是一个开源的 AI 答案归因和创作者收益层。它说明哪些来源支持答案、
每个可见来源对输出贡献了多少，以及答案是否可以作为有依据的答案展示。

## 运行本地演示

```bash
python -m pip install .
rdllm-operator-doctor
PYTHONPATH=src python3 -m rdllm.cli answer "How should AI prove attribution?"
```

检查这些字段：

- `Sources`
- `Claim Evidence`
- `support`
- `text_match`
- `payout`
- `disagreement=passed`

## 运行服务

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

然后用 curl 或
[API 客户端示例](../../../examples/api_clients/README.md)
调用 `/v1/attribute`。

## 展示前先验证

保存响应 JSON 和复制后的用户可见文本，然后运行：

```bash
PYTHONPATH=src python3 tools/service_response_verify.py --response /tmp/rdllm-response.json --display-text /tmp/rdllm-display.txt
PYTHONPATH=src python3 tools/source_footer_verify.py --footer /tmp/rdllm-footer.json --display-text /tmp/rdllm-display.txt
```

只有当 `production_display_ready` 为 true 且
`source_grounding_acceptance` 为 passed 时，才把答案展示为有依据。

更多信息：
[explainer](explainer.md),
[GitHub 入门指南](../../github_start_here.md) 和
[README](../../../README.md)。
