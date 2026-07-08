# RDLLM ব্যাখ্যা

## ELI5

AI answer-কে স্কুলের রিপোর্ট ভাবুন। RDLLM দেখায় কোন বই বা source ব্যবহার হয়েছে,
কোন বাক্য কোন source দিয়ে support হয়েছে, এবং creator credit বা payment পাবে কি
না।

## Simple

RDLLM AI product-এর জন্য source footer যোগ করে। এটি claims যাচাই করে এবং
visible source usage-কে payout বা escrow-এর সাথে যুক্ত করে।

## Non-Technical

Users sources ও Claim Evidence দেখে। Creators attribution evidence পায়।
Operators grounded বা royalty-bearing answer publish করার আগে verification gate
চালায়।

## Technical

Runtime-এ RDLLM source rows এবং Claim Evidence rows তৈরি করে: claim hash,
support score, evidence span hash, warrant status, source-disagreement status
এবং payout allocation। Verifier hashes, citations, links, metrics,
attribution-gap closure এবং `source_grounding_acceptance` recompute করে।

