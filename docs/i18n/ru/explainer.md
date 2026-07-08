# RDLLM простыми словами

## ELI5

Представьте AI-ответ как школьный доклад. RDLLM заставляет показать, какие
источники использованы, какая фраза чем подтверждена, и кто должен получить
credit или payment.

## Simple

RDLLM добавляет видимый source footer к AI-ответам. Он проверяет, что sources
поддерживают claims, и связывает видимое использование источников с payout или
escrow.

## Non-Technical

Users видят sources и Claim Evidence. Creators получают attribution evidence.
Operators получают gates перед публикацией ответа как grounded или
royalty-bearing.

## Technical

RDLLM создает source rows и Claim Evidence rows с claim hash, support score,
evidence span hash, warrant status, source-disagreement status и payout
allocation. Verifiers пересчитывают hashes, citations, links, metrics,
attribution-gap closure и `source_grounding_acceptance`.

