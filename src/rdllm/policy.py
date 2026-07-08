"""Rights-policy evaluation for registered works and chunks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from rdllm.models import Chunk, Creator, Work
from rdllm.text import stable_hash

RIGHTS_MANIFEST_VERSION = "rdllm-rights-manifest/v1"


@dataclass(frozen=True)
class PolicyDecision:
    """A deterministic allow/deny result for one source asset and use."""

    target_type: str
    target_id: str
    work_id: str
    chunk_id: str
    policy_id: str
    use: str
    jurisdiction: str
    allowed: bool
    reasons: tuple[str, ...]
    license: str
    license_uri: str
    source_uri: str
    content_hash: str
    minimum_creator_pool_rate: float
    actual_creator_pool_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_type": self.target_type,
            "target_id": self.target_id,
            "work_id": self.work_id,
            "chunk_id": self.chunk_id,
            "policy_id": self.policy_id,
            "use": self.use,
            "jurisdiction": self.jurisdiction,
            "allowed": self.allowed,
            "reasons": list(self.reasons),
            "license": self.license,
            "license_uri": self.license_uri,
            "source_uri": self.source_uri,
            "content_hash": self.content_hash,
            "minimum_creator_pool_rate": round(self.minimum_creator_pool_rate, 8),
            "actual_creator_pool_rate": round(self.actual_creator_pool_rate, 8),
        }


class RightsPolicyEngine:
    """Evaluate machine-readable consent, license, and revocation metadata."""

    def __init__(self, default_jurisdiction: str = "GLOBAL") -> None:
        self.default_jurisdiction = default_jurisdiction

    def evaluate_chunk(
        self,
        chunk: Chunk,
        use: str,
        *,
        jurisdiction: str | None = None,
        creator_pool_rate: Decimal | str | float = Decimal("0"),
    ) -> PolicyDecision:
        reasons = self._reasons(
            allowed_uses=chunk.allowed_uses,
            prohibited_uses=chunk.prohibited_uses,
            jurisdictions=chunk.jurisdictions,
            revoked=chunk.revoked,
            revoked_at=chunk.revoked_at,
            requires_royalty=chunk.requires_royalty,
            minimum_creator_pool_rate=chunk.minimum_creator_pool_rate,
            use=use,
            jurisdiction=jurisdiction or self.default_jurisdiction,
            creator_pool_rate=creator_pool_rate,
        )
        allowed = not any(reason.startswith("deny:") for reason in reasons)
        return PolicyDecision(
            target_type="chunk",
            target_id=chunk.chunk_id,
            work_id=chunk.work_id,
            chunk_id=chunk.chunk_id,
            policy_id=chunk.policy_id,
            use=use,
            jurisdiction=jurisdiction or self.default_jurisdiction,
            allowed=allowed,
            reasons=tuple(reasons),
            license=chunk.license,
            license_uri=chunk.license_uri,
            source_uri=chunk.source_uri,
            content_hash=chunk.content_hash,
            minimum_creator_pool_rate=chunk.minimum_creator_pool_rate,
            actual_creator_pool_rate=float(Decimal(str(creator_pool_rate))),
        )

    def evaluate_work(
        self,
        work: Work,
        use: str,
        *,
        jurisdiction: str | None = None,
        creator_pool_rate: Decimal | str | float = Decimal("0"),
    ) -> PolicyDecision:
        work_hash = stable_hash(work.content)
        reasons = self._reasons(
            allowed_uses=work.allowed_uses,
            prohibited_uses=work.prohibited_uses,
            jurisdictions=work.jurisdictions,
            revoked=work.revoked,
            revoked_at=work.revoked_at,
            requires_royalty=work.requires_royalty,
            minimum_creator_pool_rate=work.minimum_creator_pool_rate,
            use=use,
            jurisdiction=jurisdiction or self.default_jurisdiction,
            creator_pool_rate=creator_pool_rate,
        )
        allowed = not any(reason.startswith("deny:") for reason in reasons)
        return PolicyDecision(
            target_type="work",
            target_id=work.work_id,
            work_id=work.work_id,
            chunk_id="",
            policy_id=work.policy_id or f"policy:{work.work_id}",
            use=use,
            jurisdiction=jurisdiction or self.default_jurisdiction,
            allowed=allowed,
            reasons=tuple(reasons),
            license=work.license,
            license_uri=work.license_uri,
            source_uri=work.source_uri or f"registered://works/{work.work_id}",
            content_hash=work_hash,
            minimum_creator_pool_rate=work.minimum_creator_pool_rate,
            actual_creator_pool_rate=float(Decimal(str(creator_pool_rate))),
        )

    def allowed_chunks(
        self,
        chunks: Iterable[Chunk],
        use: str,
        *,
        jurisdiction: str | None = None,
        creator_pool_rate: Decimal | str | float = Decimal("0"),
    ) -> list[Chunk]:
        return [
            chunk
            for chunk in chunks
            if self.evaluate_chunk(
                chunk,
                use,
                jurisdiction=jurisdiction,
                creator_pool_rate=creator_pool_rate,
            ).allowed
        ]

    def rights_manifest(
        self,
        *,
        creators: dict[str, Creator],
        works: dict[str, Work],
        chunks: list[Chunk],
    ) -> dict[str, Any]:
        """Return an auditable manifest aligned with ODRL, Croissant, and SPDX concepts."""

        chunks_by_work: dict[str, list[Chunk]] = {}
        for chunk in chunks:
            chunks_by_work.setdefault(chunk.work_id, []).append(chunk)

        work_entries = []
        for work_id, work in sorted(works.items()):
            content_hash = stable_hash(work.content)
            work_entries.append(
                {
                    "work_id": work.work_id,
                    "creator_id": work.creator_id,
                    "creator_name": creators[work.creator_id].name,
                    "title": work.title,
                    "source_uri": work.source_uri
                    or f"registered://works/{work.work_id}",
                    "content_hash": content_hash,
                    "license": work.license,
                    "license_uri": work.license_uri,
                    "policy": self._policy_dict(work),
                    "odrl": {
                        "asset": work.source_uri or f"registered://works/{work.work_id}",
                        "permission": [
                            {"action": use} for use in sorted(work.allowed_uses)
                        ],
                        "prohibition": [
                            {"action": use} for use in sorted(work.prohibited_uses)
                        ],
                        "duty": self._odrl_duties(work),
                    },
                    "croissant": {
                        "sc:license": work.license_uri or work.license,
                        "prov:wasAttributedTo": work.creator_id,
                        "prov:wasDerivedFrom": work.source_uri
                        or f"registered://works/{work.work_id}",
                        "rdllm:derivedFromWorks": list(work.derived_from),
                        "usageRestrictions": {
                            "allowedUses": list(work.allowed_uses),
                            "prohibitedUses": list(work.prohibited_uses),
                            "jurisdictions": list(work.jurisdictions),
                        },
                    },
                    "spdx": {
                        "name": work.title,
                        "externalRef": work.source_uri
                        or f"registered://works/{work.work_id}",
                        "verifiedUsing": [
                            {"algorithm": "SHA256", "hashValue": content_hash}
                        ],
                        "intendedUse": list(work.allowed_uses),
                        "lineage": list(work.derived_from),
                    },
                    "lineage": {
                        "derived_from": list(work.derived_from),
                        "has_upstream_lineage": bool(work.derived_from),
                    },
                    "chunks": [chunk.chunk_id for chunk in chunks_by_work.get(work_id, [])],
                }
            )

        chunk_entries = [
            {
                "chunk_id": chunk.chunk_id,
                "work_id": chunk.work_id,
                "creator_id": chunk.creator_id,
                "title": chunk.title,
                "source_uri": chunk.source_uri,
                "content_hash": chunk.content_hash,
                "policy_id": chunk.policy_id,
            }
            for chunk in sorted(chunks, key=lambda item: item.chunk_id)
        ]
        manifest = {
            "manifest_version": RIGHTS_MANIFEST_VERSION,
            "profiles": {
                "odrl": "http://www.w3.org/ns/odrl/2/",
                "croissant": "https://mlcommons.org/croissant/",
                "spdx": "https://spdx.org/rdf/3.0.1/terms/",
                "prov": "http://www.w3.org/ns/prov#",
            },
            "summary": {
                "creator_count": len(creators),
                "work_count": len(works),
                "chunk_count": len(chunks),
            },
            "creators": [
                {
                    "creator_id": creator.creator_id,
                    "name": creator.name,
                    "payout_account": creator.payout_account,
                }
                for creator in sorted(creators.values(), key=lambda item: item.creator_id)
            ],
            "works": work_entries,
            "chunks": chunk_entries,
        }
        manifest["manifest_hash"] = stable_hash(json.dumps(manifest, sort_keys=True))
        return manifest

    def _reasons(
        self,
        *,
        allowed_uses: tuple[str, ...],
        prohibited_uses: tuple[str, ...],
        jurisdictions: tuple[str, ...],
        revoked: bool,
        revoked_at: str,
        requires_royalty: bool,
        minimum_creator_pool_rate: float,
        use: str,
        jurisdiction: str,
        creator_pool_rate: Decimal | str | float,
    ) -> list[str]:
        reasons: list[str] = []
        if revoked:
            suffix = f":{revoked_at}" if revoked_at else ""
            reasons.append(f"deny:revoked{suffix}")
        if use in prohibited_uses:
            reasons.append(f"deny:prohibited_use:{use}")
        if allowed_uses and use not in allowed_uses:
            reasons.append(f"deny:not_permitted_use:{use}")
        if jurisdictions and "GLOBAL" not in jurisdictions and jurisdiction not in jurisdictions:
            reasons.append(f"deny:jurisdiction:{jurisdiction}")
        actual_rate = Decimal(str(creator_pool_rate))
        minimum_rate = Decimal(str(minimum_creator_pool_rate))
        if requires_royalty and actual_rate < minimum_rate:
            reasons.append(f"deny:creator_pool_rate_below_minimum:{minimum_rate}")
        if not reasons:
            reasons.append(f"permit:{use}")
        return reasons

    def _policy_dict(self, work: Work) -> dict[str, Any]:
        return {
            "policy_id": work.policy_id or f"policy:{work.work_id}",
            "allowed_uses": list(work.allowed_uses),
            "prohibited_uses": list(work.prohibited_uses),
            "jurisdictions": list(work.jurisdictions),
            "requires_attribution": work.requires_attribution,
            "requires_royalty": work.requires_royalty,
            "minimum_creator_pool_rate": work.minimum_creator_pool_rate,
            "revoked": work.revoked,
            "revoked_at": work.revoked_at,
        }

    def _odrl_duties(self, work: Work) -> list[dict[str, Any]]:
        duties: list[dict[str, Any]] = []
        if work.requires_attribution:
            duties.append({"action": "attribute"})
        if work.requires_royalty:
            duty: dict[str, Any] = {"action": "compensate"}
            if work.minimum_creator_pool_rate:
                duty["constraint"] = {
                    "leftOperand": "creator_pool_rate",
                    "operator": "gteq",
                    "rightOperand": work.minimum_creator_pool_rate,
                }
            duties.append(duty)
        return duties
