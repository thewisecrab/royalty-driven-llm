# RDLLM explicado

## ELI5

Imagina que una respuesta de IA es un trabajo escolar. RDLLM hace que la IA
muestre que libros uso, que frase viene de que fuente, y si las personas que
crearon esas fuentes deben recibir credito o pago. Si falta la prueba, la
respuesta no debe fingir que esta bien fundamentada.

## Simple

RDLLM es una capa open source para productos de IA. Agrega un pie de fuentes
visible, comprueba que las fuentes realmente apoyen las afirmaciones, y registra
como el uso de fuentes se conecta con pago o escrow.

Usalo si construyes un chatbot, app RAG, buscador, agente, API de modelo,
marketplace o plataforma de creadores y quieres que los usuarios vean de donde
viene una respuesta.

## Non-Technical

RDLLM ayuda a tres grupos:

- Los usuarios ven fuentes, evidencia de afirmaciones y senales de confianza.
- Creadores y publishers reciben evidencia de atribucion y registros de
  settlement.
- Operadores tienen verificaciones antes de mostrar una respuesta como grounded
  o royalty-bearing.

El sistema no dice que puede leer los pensamientos ocultos del modelo. Reporta
evidencia observable: soporte visible de fuentes, overlap entre respuesta y
fuente, Claim Evidence, desacuerdo entre fuentes y asignacion de payout.

## Technical

En runtime, RDLLM toma una respuesta, referencias de fuentes y contexto de
ingresos. Construye un source footer con filas de fuentes y filas de Claim
Evidence. Cada fila de claim incluye claim hash, support score, evidence span
hash, character offsets, evidence preview, warrant status,
source-disagreement status y source label.

Antes del display, los verifiers recalculan display hash, footer hash, row
hashes, metricas de uso de fuente, Claim Evidence, marcadores de cita, links en
la respuesta, claim-source closure, wording sobre model reliance,
attribution-gap closure y source disagreement. La respuesta es public-facing
solo cuando `production_display_ready` es true y
`source_grounding_acceptance` esta passed.

Para implementar, empieza aqui:

- [Quickstart](quickstart.md)
- [GitHub Start Here](../../github_start_here.md)
- [Live use cases](../../../examples/live_use_cases/README.md)
- [API client examples](../../../examples/api_clients/README.md)

