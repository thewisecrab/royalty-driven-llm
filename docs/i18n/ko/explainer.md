# RDLLM 설명

## ELI5

AI 답변을 학교 보고서라고 생각하세요. RDLLM은 어떤 sources를 사용했는지,
어떤 문장이 어떤 source로 support되는지, 누가 credit 또는 payment를 받아야
하는지 보여줍니다.

## Simple

RDLLM은 AI answer에 보이는 source footer를 추가합니다. Sources가 claims를
실제로 지원하는지 확인하고 visible source usage를 payout 또는 escrow와
연결합니다.

## Non-Technical

Users는 sources와 Claim Evidence를 봅니다. Creators는 attribution evidence를
받습니다. Operators는 grounded 또는 royalty-bearing으로 표시하기 전에
verification gates를 실행합니다.

## Technical

RDLLM은 source rows와 Claim Evidence rows를 생성합니다. 여기에는 claim hash,
support score, evidence span hash, warrant status, source-disagreement status,
payout allocation이 포함됩니다. Verifiers는 hashes, citations, links,
metrics, attribution-gap closure, `source_grounding_acceptance`를 재계산합니다.

