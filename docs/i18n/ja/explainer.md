# RDLLM の説明

## ELI5

AI の回答を学校のレポートだと考えてください。RDLLM は、どの sources を
使ったか、どの文がどの source に支えられているか、誰に credit や
payment が必要かを示します。

## Simple

RDLLM は AI answer に見える source footer を追加します。Sources が claims
を本当に支えているか確認し、visible source usage を payout または escrow
につなげます。

## Non-Technical

Users は sources と Claim Evidence を見られます。Creators は attribution
evidence を得ます。Operators は grounded または royalty-bearing として
表示する前に verification gates を実行できます。

## Technical

RDLLM は source rows と Claim Evidence rows を作成します。各 row には
claim hash, support score, evidence span hash, warrant status,
source-disagreement status, payout allocation が含まれます。Verifiers は
hashes, citations, links, metrics, attribution-gap closure,
`source_grounding_acceptance` を再計算します。

