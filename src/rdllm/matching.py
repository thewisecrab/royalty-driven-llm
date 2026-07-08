"""Content-ID-style text attribution for generated outputs."""

from __future__ import annotations

from rdllm.models import Chunk, TextMatch
from rdllm.text import (
    longest_common_token_sequence,
    ngram_containment,
    tokenize,
)


class TextAttributor:
    """Find registered text that appears in or strongly supports an output."""

    def __init__(
        self,
        chunks: list[Chunk],
        min_score: float = 0.08,
        ngram_size: int = 5,
    ) -> None:
        self.chunks = chunks
        self.min_score = min_score
        self.ngram_size = ngram_size

    def match(self, output: str, limit: int | None = None) -> list[TextMatch]:
        output_tokens = tokenize(output)
        matches: list[TextMatch] = []

        for chunk in self.chunks:
            source_tokens = tokenize(chunk.text)
            if not source_tokens or not output_tokens:
                continue

            longest_length, longest_tokens = longest_common_token_sequence(
                source_tokens, output_tokens
            )
            exact_score = longest_length / len(source_tokens)
            ngram_score = ngram_containment(
                source_tokens,
                output_tokens,
                size=min(self.ngram_size, max(1, len(source_tokens))),
            )
            sequence_score = min(1.0, longest_length / 30)
            score = max(exact_score, ngram_score, sequence_score)

            if score >= self.min_score:
                matches.append(
                    TextMatch(
                        chunk=chunk,
                        score=score,
                        rank=0,
                        exact_score=exact_score,
                        ngram_score=ngram_score,
                        longest_sequence_tokens=longest_length,
                        matched_text=" ".join(longest_tokens),
                    )
                )

        matches.sort(key=lambda match: match.score, reverse=True)
        if limit is not None:
            matches = matches[:limit]
        return [
            TextMatch(
                chunk=match.chunk,
                score=match.score,
                rank=index + 1,
                exact_score=match.exact_score,
                ngram_score=match.ngram_score,
                longest_sequence_tokens=match.longest_sequence_tokens,
                matched_text=match.matched_text,
            )
            for index, match in enumerate(matches)
        ]
