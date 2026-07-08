# RDLLM 说明

## ELI5

把 AI 答案想成一份学校报告。RDLLM 让 AI 说明它用了哪些书，哪句话由哪
个来源支持，以及这些来源的创作者是否应该得到署名或付款。如果证明不够，
答案就不应该假装自己已经有可靠来源。

## Simple

RDLLM 是一个给 AI 产品使用的开源层。它为答案添加可见的来源 footer，
检查来源是否真的支持答案里的 claim，并记录 source usage 如何对应到
payout 或 escrow。

如果你在做 chatbot、RAG app、搜索助手、agent、model API、marketplace
或 creator platform，并希望用户知道答案来自哪里，可以使用它。

## Non-Technical

RDLLM 帮助三类人：

- 用户可以看到 sources、Claim Evidence 和 confidence signals，而不是只
  看到一段 AI 答案。
- 创作者和 publisher 可以获得 attribution evidence 和 settlement records。
- operator 可以在展示 grounded 或 royalty-bearing 答案前运行验证 gate。

系统不会声称能读取模型隐藏的想法。它报告的是可观察证据：可见 source
support、答案和来源的 overlap、Claim Evidence、source-disagreement check
和 payout allocation。

## Technical

在 runtime，RDLLM 接收 answer、source references 和 revenue context。它
生成 source footer，其中包含 source rows 和 Claim Evidence rows。每个
claim row 包含 claim hash、support score、evidence span hash、character
offsets、evidence preview、warrant status、source-disagreement status 和
source label。

展示前，verifier 会重新计算 display hash、footer hash、row hashes、
source usage metrics、Claim Evidence、citation markers、answer links、
claim-source closure、model-reliance wording、attribution-gap closure 和
source disagreement。只有当 `production_display_ready` 为 true 且
`source_grounding_acceptance` 为 passed 时，答案才适合 public-facing 展示。

实现时从这里开始：

- [Quickstart](quickstart.md)
- [GitHub Start Here](../../github_start_here.md)
- [Live use cases](../../../examples/live_use_cases/README.md)
- [API client examples](../../../examples/api_clients/README.md)

