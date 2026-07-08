# RDLLM explique

## ELI5

Une reponse d'IA ressemble a un devoir. RDLLM fait montrer les sources utilisees,
les phrases soutenues par ces sources, et qui doit recevoir credit ou paiement.

## Simple

RDLLM ajoute un footer de sources visible aux reponses d'IA. Il verifie que les
sources soutiennent les claims et relie l'usage visible aux payouts ou a l'escrow.

## Non-Technical

Les utilisateurs voient les sources et la Claim Evidence. Les createurs voient
l'attribution. Les operateurs ont des gates avant de publier une reponse comme
grounded ou royalty-bearing.

## Technical

RDLLM construit des source rows et Claim Evidence rows avec claim hash, support
score, evidence span hash, warrant status, source-disagreement status et payout
allocation. Les verifiers recalculent les hashes, les citations, les liens, les
metrics, l'attribution gap et `source_grounding_acceptance` avant l'affichage.

