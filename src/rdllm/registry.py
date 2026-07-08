"""Ownership claim registry checks for RDLLM settlement."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from rdllm.models import Work
from rdllm.text import jaccard_similarity, stable_hash, tokenize

REGISTRY_REPORT_VERSION = "rdllm-claim-registry/v1"
DEFAULT_DUPLICATE_THRESHOLD = 0.92


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class OwnershipAttestation:
    """Portable ownership or administration claim over a registered work."""

    attestation_id: str
    work_id: str
    creator_id: str
    claim_type: str
    issuer: str
    issued_at: str
    evidence_uri: str = ""
    evidence_hash: str = ""
    signature: str = ""
    status: str = "active"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OwnershipAttestation":
        return cls(
            attestation_id=data["attestation_id"],
            work_id=data["work_id"],
            creator_id=data["creator_id"],
            claim_type=data.get("claim_type", "self_asserted"),
            issuer=data.get("issuer", ""),
            issued_at=data.get("issued_at", ""),
            evidence_uri=data.get("evidence_uri", ""),
            evidence_hash=data.get("evidence_hash", ""),
            signature=data.get("signature", ""),
            status=data.get("status", "active"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "attestation_id": self.attestation_id,
            "work_id": self.work_id,
            "creator_id": self.creator_id,
            "claim_type": self.claim_type,
            "issuer": self.issuer,
            "issued_at": self.issued_at,
            "evidence_uri": self.evidence_uri,
            "evidence_hash": self.evidence_hash,
            "signature": self.signature,
            "status": self.status,
        }


@dataclass(frozen=True)
class RegistryConflict:
    """A conflict that prevents direct creator settlement."""

    conflict_id: str
    work_ids: tuple[str, ...]
    creator_ids: tuple[str, ...]
    conflict_type: str
    score: float
    content_hashes: tuple[str, ...]
    status: str = "open"
    resolution: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "work_ids": list(self.work_ids),
            "creator_ids": list(self.creator_ids),
            "conflict_type": self.conflict_type,
            "score": round(self.score, 8),
            "content_hashes": list(self.content_hashes),
            "status": self.status,
            "resolution": self.resolution,
        }


def load_attestations(path: str | Path | None) -> list[OwnershipAttestation]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("attestations", data if isinstance(data, list) else [])
    return [OwnershipAttestation.from_dict(item) for item in items]


def registry_report_for_works(
    works: Iterable[Work],
    *,
    attestations: Iterable[OwnershipAttestation] | None = None,
    duplicate_threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
) -> dict[str, Any]:
    """Detect duplicate or near-duplicate ownership claims before settlement."""

    work_list = sorted(list(works), key=lambda work: work.work_id)
    attestation_list = sorted(
        list(attestations or []), key=lambda item: item.attestation_id
    )
    conflicts: list[RegistryConflict] = []

    for left_index, left in enumerate(work_list):
        for right in work_list[left_index + 1 :]:
            if left.creator_id == right.creator_id:
                continue
            score = _work_similarity(left, right)
            if score < duplicate_threshold:
                continue
            conflict_type = (
                "duplicate_content" if score == 1.0 else "near_duplicate_content"
            )
            work_ids = tuple(sorted((left.work_id, right.work_id)))
            creator_ids = tuple(sorted((left.creator_id, right.creator_id)))
            content_hashes = tuple(
                sorted((stable_hash(left.content), stable_hash(right.content)))
            )
            conflict_seed = canonical_json(
                {
                    "work_ids": work_ids,
                    "creator_ids": creator_ids,
                    "conflict_type": conflict_type,
                    "score": round(score, 8),
                    "content_hashes": content_hashes,
                }
            )
            conflicts.append(
                RegistryConflict(
                    conflict_id=f"conf_{stable_hash(conflict_seed)[:16]}",
                    work_ids=work_ids,
                    creator_ids=creator_ids,
                    conflict_type=conflict_type,
                    score=score,
                    content_hashes=content_hashes,
                )
            )

    payload: dict[str, Any] = {
        "registry_report_version": REGISTRY_REPORT_VERSION,
        "summary": {
            "work_count": len(work_list),
            "attestation_count": len(attestation_list),
            "duplicate_threshold": round(duplicate_threshold, 8),
            "open_conflict_count": sum(
                1 for conflict in conflicts if conflict.status == "open"
            ),
            "conflicted_work_count": len(conflicted_work_ids_from_conflicts(conflicts)),
        },
        "attestations": [attestation.to_dict() for attestation in attestation_list],
        "conflicts": [conflict.to_dict() for conflict in conflicts],
    }
    payload["report_hash"] = stable_hash(canonical_json(payload))
    return payload


def conflicted_work_ids(report: dict[str, Any]) -> set[str]:
    conflicts = report.get("conflicts", [])
    ids: set[str] = set()
    for conflict in conflicts:
        if conflict.get("status", "open") != "open":
            continue
        if conflict.get("conflict_type") not in {
            "duplicate_content",
            "near_duplicate_content",
        }:
            continue
        ids.update(str(work_id) for work_id in conflict.get("work_ids", []))
    return ids


def conflicts_by_work_id(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for conflict in report.get("conflicts", []):
        if conflict.get("status", "open") != "open":
            continue
        for work_id in conflict.get("work_ids", []):
            index.setdefault(str(work_id), []).append(conflict)
    return index


def conflicted_work_ids_from_conflicts(conflicts: Iterable[RegistryConflict]) -> set[str]:
    ids: set[str] = set()
    for conflict in conflicts:
        if conflict.status == "open":
            ids.update(conflict.work_ids)
    return ids


def _work_similarity(left: Work, right: Work) -> float:
    if stable_hash(left.content) == stable_hash(right.content):
        return 1.0
    left_tokens = tokenize(left.content)
    right_tokens = tokenize(right.content)
    return jaccard_similarity(left_tokens, right_tokens)
