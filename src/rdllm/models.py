"""Serializable data models for the Royalty Driven LLM prototype."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

DEFAULT_ALLOWED_USES = (
    "training",
    "retrieval",
    "generation",
    "display",
    "quote",
    "external_attribution",
)
DEFAULT_JURISDICTIONS = ("GLOBAL",)


def _tuple_field(data: dict[str, Any], key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = data.get(key, default)
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _lineage_field(data: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    value = data.get("derived_from", data.get("lineage_sources", ()))
    if value is None:
        return ()
    if isinstance(value, (str, dict)):
        value = (value,)
    entries: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, str):
            entries.append(
                {
                    "work_id": item,
                    "weight": 1.0,
                    "relation": "derived_from",
                    "source_uri": "",
                    "content_hash": "",
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        work_id = str(item.get("work_id", item.get("source_work_id", "")))
        if not work_id:
            continue
        entries.append(
            {
                "work_id": work_id,
                "weight": float(item.get("weight", item.get("share", 1.0))),
                "relation": str(item.get("relation", "derived_from")),
                "source_uri": str(item.get("source_uri", "")),
                "content_hash": str(item.get("content_hash", "")),
            }
        )
    return tuple(entries)


@dataclass(frozen=True)
class Creator:
    creator_id: str
    name: str
    payout_account: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Creator":
        return cls(
            creator_id=data["creator_id"],
            name=data["name"],
            payout_account=data["payout_account"],
        )


@dataclass(frozen=True)
class Work:
    work_id: str
    creator_id: str
    title: str
    content: str
    license: str = "royalty-bearing"
    data_value_prior: float = 1.0
    source_uri: str = ""
    policy_id: str = ""
    license_uri: str = ""
    allowed_uses: tuple[str, ...] = DEFAULT_ALLOWED_USES
    prohibited_uses: tuple[str, ...] = ()
    jurisdictions: tuple[str, ...] = DEFAULT_JURISDICTIONS
    requires_attribution: bool = True
    requires_royalty: bool = True
    minimum_creator_pool_rate: float = 0.0
    revoked: bool = False
    revoked_at: str = ""
    derived_from: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Work":
        work_id = data["work_id"]
        prohibited_data = {
            "prohibited_uses": data.get("prohibited_uses", data.get("denied_uses", ()))
        }
        return cls(
            work_id=work_id,
            creator_id=data["creator_id"],
            title=data["title"],
            content=data["content"],
            license=data.get("license", "royalty-bearing"),
            data_value_prior=float(data.get("data_value_prior", 1.0)),
            source_uri=data.get("source_uri", ""),
            policy_id=data.get("policy_id", f"policy:{work_id}"),
            license_uri=data.get("license_uri", ""),
            allowed_uses=_tuple_field(data, "allowed_uses", DEFAULT_ALLOWED_USES),
            prohibited_uses=_tuple_field(prohibited_data, "prohibited_uses", ()),
            jurisdictions=_tuple_field(data, "jurisdictions", DEFAULT_JURISDICTIONS),
            requires_attribution=bool(data.get("requires_attribution", True)),
            requires_royalty=bool(data.get("requires_royalty", True)),
            minimum_creator_pool_rate=float(data.get("minimum_creator_pool_rate", 0.0)),
            revoked=bool(data.get("revoked", False)),
            revoked_at=data.get("revoked_at", ""),
            derived_from=_lineage_field(data),
        )


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    work_id: str
    creator_id: str
    title: str
    text: str
    content_hash: str
    license: str
    data_value_prior: float = 1.0
    source_uri: str = ""
    policy_id: str = ""
    license_uri: str = ""
    allowed_uses: tuple[str, ...] = DEFAULT_ALLOWED_USES
    prohibited_uses: tuple[str, ...] = ()
    jurisdictions: tuple[str, ...] = DEFAULT_JURISDICTIONS
    requires_attribution: bool = True
    requires_royalty: bool = True
    minimum_creator_pool_rate: float = 0.0
    revoked: bool = False
    revoked_at: str = ""


@dataclass(frozen=True)
class RetrievalHit:
    chunk: Chunk
    score: float
    rank: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "work_id": self.chunk.work_id,
            "creator_id": self.chunk.creator_id,
            "title": self.chunk.title,
            "score": round(self.score, 8),
            "rank": self.rank,
            "content_hash": self.chunk.content_hash,
        }


@dataclass(frozen=True)
class TextMatch:
    chunk: Chunk
    score: float
    rank: int
    exact_score: float
    ngram_score: float
    longest_sequence_tokens: int
    matched_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "work_id": self.chunk.work_id,
            "creator_id": self.chunk.creator_id,
            "title": self.chunk.title,
            "score": round(self.score, 8),
            "rank": self.rank,
            "exact_score": round(self.exact_score, 8),
            "ngram_score": round(self.ngram_score, 8),
            "longest_sequence_tokens": self.longest_sequence_tokens,
            "matched_text": self.matched_text,
            "content_hash": self.chunk.content_hash,
        }


@dataclass(frozen=True)
class SourceAccess:
    access_id: str
    access_type: str
    use: str
    chunk_id: str
    work_id: str
    creator_id: str
    title: str
    source_uri: str
    content_hash: str
    score: float
    rank: int
    policy_allowed: bool = True
    registry_allowed: bool = True
    decision_status: str = "allowed"
    matched_text_hash: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceAccess":
        return cls(
            access_id=data["access_id"],
            access_type=data["access_type"],
            use=data.get("use", ""),
            chunk_id=data["chunk_id"],
            work_id=data["work_id"],
            creator_id=data["creator_id"],
            title=data.get("title", ""),
            source_uri=data.get("source_uri", ""),
            content_hash=data["content_hash"],
            score=float(data.get("score", 0.0)),
            rank=int(data.get("rank", 0)),
            policy_allowed=bool(data.get("policy_allowed", True)),
            registry_allowed=bool(data.get("registry_allowed", True)),
            decision_status=data.get("decision_status", "allowed"),
            matched_text_hash=data.get("matched_text_hash", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_id": self.access_id,
            "access_type": self.access_type,
            "use": self.use,
            "chunk_id": self.chunk_id,
            "work_id": self.work_id,
            "creator_id": self.creator_id,
            "title": self.title,
            "source_uri": self.source_uri,
            "content_hash": self.content_hash,
            "score": round(self.score, 8),
            "rank": self.rank,
            "policy_allowed": self.policy_allowed,
            "registry_allowed": self.registry_allowed,
            "decision_status": self.decision_status,
            "matched_text_hash": self.matched_text_hash,
        }


@dataclass(frozen=True)
class SourceReference:
    label: str
    creator_id: str
    creator_name: str
    work_id: str
    chunk_id: str
    title: str
    source_uri: str
    license: str
    quote: str
    content_hash: str
    policy_id: str = ""
    policy_use: str = ""
    jurisdiction: str = "GLOBAL"
    license_uri: str = ""
    retrieval_score: float = 0.0
    text_match_score: float = 0.0
    output_support: float = 0.0
    citation_score: float = 0.0
    contribution_weight: Decimal = Decimal("0")
    payout: Decimal = Decimal("0")
    evidence_span_hashes: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceReference":
        return cls(
            label=data["label"],
            creator_id=data["creator_id"],
            creator_name=data["creator_name"],
            work_id=data["work_id"],
            chunk_id=data["chunk_id"],
            title=data["title"],
            source_uri=data["source_uri"],
            license=data["license"],
            policy_id=data.get("policy_id", ""),
            policy_use=data.get("policy_use", ""),
            jurisdiction=data.get("jurisdiction", "GLOBAL"),
            license_uri=data.get("license_uri", ""),
            quote=data["quote"],
            content_hash=data["content_hash"],
            retrieval_score=float(data.get("retrieval_score", 0.0)),
            text_match_score=float(data.get("text_match_score", 0.0)),
            output_support=float(data.get("output_support", 0.0)),
            citation_score=float(data.get("citation_score", 0.0)),
            contribution_weight=Decimal(str(data.get("contribution_weight", "0"))),
            payout=Decimal(str(data.get("payout", "0"))),
            evidence_span_hashes=_tuple_field(data, "evidence_span_hashes", ()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "creator_id": self.creator_id,
            "creator_name": self.creator_name,
            "work_id": self.work_id,
            "chunk_id": self.chunk_id,
            "title": self.title,
            "source_uri": self.source_uri,
            "license": self.license,
            "policy_id": self.policy_id,
            "policy_use": self.policy_use,
            "jurisdiction": self.jurisdiction,
            "license_uri": self.license_uri,
            "quote": self.quote,
            "content_hash": self.content_hash,
            "retrieval_score": round(self.retrieval_score, 8),
            "text_match_score": round(self.text_match_score, 8),
            "output_support": round(self.output_support, 8),
            "citation_score": round(self.citation_score, 8),
            "contribution_weight": str(self.contribution_weight),
            "payout": str(self.payout),
            "evidence_span_hashes": list(self.evidence_span_hashes),
        }


@dataclass(frozen=True)
class ClaimSupport:
    claim: str
    source_label: str
    support_score: float
    supported: bool
    work_id: str = ""
    chunk_id: str = ""
    evidence_text: str = ""
    evidence_span_hash: str = ""
    evidence_start_char: int = -1
    evidence_end_char: int = -1

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClaimSupport":
        return cls(
            claim=data["claim"],
            source_label=data.get("source_label", ""),
            support_score=float(data.get("support_score", 0.0)),
            supported=bool(data.get("supported", False)),
            work_id=data.get("work_id", ""),
            chunk_id=data.get("chunk_id", ""),
            evidence_text=data.get("evidence_text", ""),
            evidence_span_hash=data.get("evidence_span_hash", ""),
            evidence_start_char=int(data.get("evidence_start_char", -1)),
            evidence_end_char=int(data.get("evidence_end_char", -1)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "source_label": self.source_label,
            "support_score": round(self.support_score, 8),
            "supported": self.supported,
            "work_id": self.work_id,
            "chunk_id": self.chunk_id,
            "evidence_text": self.evidence_text,
            "evidence_span_hash": self.evidence_span_hash,
            "evidence_start_char": self.evidence_start_char,
            "evidence_end_char": self.evidence_end_char,
        }


@dataclass(frozen=True)
class RoyaltyShare:
    creator_id: str
    work_id: str
    chunk_id: str
    contribution_weight: Decimal
    payout: Decimal
    query_relevance: float
    output_support: float
    data_value_prior: float
    content_hash: str
    retrieval_score: float = 0.0
    text_match_score: float = 0.0
    citation_score: float = 0.0
    training_value_score: float = 1.0
    attribution_basis: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoyaltyShare":
        return cls(
            creator_id=data["creator_id"],
            work_id=data["work_id"],
            chunk_id=data["chunk_id"],
            contribution_weight=Decimal(str(data["contribution_weight"])),
            payout=Decimal(str(data["payout"])),
            query_relevance=float(data["query_relevance"]),
            output_support=float(data["output_support"]),
            data_value_prior=float(data["data_value_prior"]),
            content_hash=data["content_hash"],
            retrieval_score=float(data.get("retrieval_score", 0.0)),
            text_match_score=float(data.get("text_match_score", 0.0)),
            citation_score=float(data.get("citation_score", 0.0)),
            training_value_score=float(data.get("training_value_score", 1.0)),
            attribution_basis={
                key: float(value)
                for key, value in data.get("attribution_basis", {}).items()
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "creator_id": self.creator_id,
            "work_id": self.work_id,
            "chunk_id": self.chunk_id,
            "contribution_weight": str(self.contribution_weight),
            "payout": str(self.payout),
            "query_relevance": round(self.query_relevance, 8),
            "output_support": round(self.output_support, 8),
            "data_value_prior": round(self.data_value_prior, 8),
            "content_hash": self.content_hash,
            "retrieval_score": round(self.retrieval_score, 8),
            "text_match_score": round(self.text_match_score, 8),
            "citation_score": round(self.citation_score, 8),
            "training_value_score": round(self.training_value_score, 8),
            "attribution_basis": {
                key: round(value, 8) for key, value in self.attribution_basis.items()
            },
        }


@dataclass
class UsageEvent:
    event_id: str
    event_hash: str
    prompt: str
    output: str
    gross_revenue: Decimal
    creator_pool_rate: Decimal
    creator_pool: Decimal
    retrieval_hits: list[RetrievalHit] = field(default_factory=list)
    text_matches: list[TextMatch] = field(default_factory=list)
    royalty_shares: list[RoyaltyShare] = field(default_factory=list)
    answer_text: str = ""
    source_accesses: list[SourceAccess] = field(default_factory=list)
    source_references: list[SourceReference] = field(default_factory=list)
    claim_support: list[ClaimSupport] = field(default_factory=list)
    grounding_report: dict[str, Any] = field(default_factory=dict)
    grounding_quality: dict[str, Any] = field(default_factory=dict)
    attribution_gap: dict[str, Any] = field(default_factory=dict)
    generation_evidence: dict[str, Any] = field(default_factory=dict)
    settlement_decision: dict[str, Any] = field(default_factory=dict)
    policy_decisions: list[dict[str, Any]] = field(default_factory=list)
    registry_decisions: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UsageEvent":
        return cls(
            event_id=data["event_id"],
            event_hash=data["event_hash"],
            prompt=data["prompt"],
            output=data["output"],
            gross_revenue=Decimal(str(data["gross_revenue"])),
            creator_pool_rate=Decimal(str(data["creator_pool_rate"])),
            creator_pool=Decimal(str(data["creator_pool"])),
            retrieval_hits=[],
            text_matches=[],
            royalty_shares=[
                RoyaltyShare.from_dict(item) for item in data.get("royalty_shares", [])
            ],
            answer_text=data.get("answer_text", data["output"]),
            source_accesses=[
                SourceAccess.from_dict(item)
                for item in data.get("source_accesses", [])
            ],
            source_references=[
                SourceReference.from_dict(item)
                for item in data.get("source_references", [])
            ],
            claim_support=[
                ClaimSupport.from_dict(item) for item in data.get("claim_support", [])
            ],
            grounding_report=data.get("grounding_report", {}),
            grounding_quality=data.get("grounding_quality", {}),
            attribution_gap=data.get("attribution_gap", {}),
            generation_evidence=data.get("generation_evidence", {}),
            settlement_decision=data.get("settlement_decision", {}),
            policy_decisions=data.get("policy_decisions", []),
            registry_decisions=data.get("registry_decisions", []),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_hash": self.event_hash,
            "prompt": self.prompt,
            "output": self.output,
            "gross_revenue": str(self.gross_revenue),
            "creator_pool_rate": str(self.creator_pool_rate),
            "creator_pool": str(self.creator_pool),
            "retrieval_hits": [hit.to_dict() for hit in self.retrieval_hits],
            "text_matches": [match.to_dict() for match in self.text_matches],
            "royalty_shares": [share.to_dict() for share in self.royalty_shares],
            "answer_text": self.answer_text,
            "source_accesses": [access.to_dict() for access in self.source_accesses],
            "source_references": [
                reference.to_dict() for reference in self.source_references
            ],
            "claim_support": [support.to_dict() for support in self.claim_support],
            "grounding_report": self.grounding_report,
            "grounding_quality": self.grounding_quality,
            "attribution_gap": self.attribution_gap,
            "generation_evidence": self.generation_evidence,
            "settlement_decision": self.settlement_decision,
            "policy_decisions": self.policy_decisions,
            "registry_decisions": self.registry_decisions,
        }


def dataclass_to_dict(value: Any) -> dict[str, Any]:
    return asdict(value)
