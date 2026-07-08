# RDLLM erklaert

## ELI5

Stellen Sie sich eine KI-Antwort wie einen Schulbericht vor. RDLLM zeigt, welche
Quellen genutzt wurden, welcher Satz von welcher Quelle gestuetzt wird und wer
credit oder payment erhalten sollte.

## Simple

RDLLM fuegt KI-Antworten einen sichtbaren source footer hinzu. Es prueft, ob die
sources die claims stuetzen, und verbindet sichtbare Nutzung mit payout oder
escrow.

## Non-Technical

Users sehen sources und Claim Evidence. Creators erhalten attribution evidence.
Operators bekommen gates, bevor eine Antwort als grounded oder royalty-bearing
veroeffentlicht wird.

## Technical

RDLLM erzeugt source rows und Claim Evidence rows mit claim hash, support score,
evidence span hash, warrant status, source-disagreement status und payout
allocation. Verifiers berechnen hashes, citations, links, metrics,
attribution-gap closure und `source_grounding_acceptance` neu.

