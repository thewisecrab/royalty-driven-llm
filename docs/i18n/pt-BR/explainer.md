# RDLLM explicado

## ELI5

Pense numa resposta de IA como um trabalho de escola. RDLLM faz a IA mostrar
quais fontes usou, qual frase cada fonte sustenta e quem deve receber credito ou
pagamento.

## Simple

RDLLM adiciona um footer de fontes visivel a respostas de IA. Ele verifica se as
fontes sustentam os claims e liga o uso visivel a payout ou escrow.

## Non-Technical

Usuarios veem fontes e Claim Evidence. Criadores recebem evidencia de atribuicao.
Operadores ganham gates antes de publicar uma resposta como grounded ou
royalty-bearing.

## Technical

RDLLM gera source rows e Claim Evidence rows com claim hash, support score,
evidence span hash, warrant status, source-disagreement status e payout
allocation. Os verifiers recalculam hashes, citacoes, links, metrics,
attribution-gap closure e `source_grounding_acceptance`.

