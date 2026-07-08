# RDLLM کی وضاحت

## ELI5

AI answer کو school report سمجھیں۔ RDLLM دکھاتا ہے کہ کون سی sources استعمال
ہوئیں، کون سا sentence کس source سے support ہوا، اور creators کو credit یا
payment ملنی چاہیے یا نہیں۔

## Simple

RDLLM AI products میں visible source footer شامل کرتا ہے۔ یہ claims verify کرتا
ہے اور source usage کو payout یا escrow سے جوڑتا ہے۔

## Non-Technical

Users sources اور Claim Evidence دیکھتے ہیں۔ Creators attribution evidence حاصل
کرتے ہیں۔ Operators answer کو grounded یا royalty-bearing دکھانے سے پہلے
verification gates چلاتے ہیں۔

## Technical

RDLLM source rows اور Claim Evidence rows بناتا ہے جن میں claim hash, support
score, evidence span hash, warrant status, source-disagreement status اور payout
allocation شامل ہیں۔ Verifiers hashes, citations, links, metrics,
attribution-gap closure اور `source_grounding_acceptance` recompute کرتے ہیں۔

