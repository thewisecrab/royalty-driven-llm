"""Append-only transparency log with Merkle inclusion proofs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdllm.receipts import canonical_json, hash_payload
from rdllm.text import stable_hash


def _parent(left: str, right: str) -> str:
    return stable_hash(f"node:{left}:{right}")


def merkle_root(leaves: list[str]) -> str:
    if not leaves:
        return stable_hash("empty")
    level = leaves[:]
    while len(level) > 1:
        next_level: list[str] = []
        for index in range(0, len(level), 2):
            left = level[index]
            right = level[index + 1] if index + 1 < len(level) else left
            next_level.append(_parent(left, right))
        level = next_level
    return level[0]


def inclusion_proof(leaves: list[str], leaf_index: int) -> dict[str, Any]:
    if leaf_index < 0 or leaf_index >= len(leaves):
        raise IndexError("leaf_index out of range")

    proof: list[dict[str, str]] = []
    index = leaf_index
    level = leaves[:]
    while len(level) > 1:
        if index % 2 == 0:
            sibling_index = index + 1 if index + 1 < len(level) else index
            proof.append({"side": "right", "hash": level[sibling_index]})
        else:
            sibling_index = index - 1
            proof.append({"side": "left", "hash": level[sibling_index]})

        next_level: list[str] = []
        for pair_index in range(0, len(level), 2):
            left = level[pair_index]
            right = level[pair_index + 1] if pair_index + 1 < len(level) else left
            next_level.append(_parent(left, right))
        index //= 2
        level = next_level

    return {
        "leaf_index": leaf_index,
        "leaf_hash": leaves[leaf_index],
        "tree_size": len(leaves),
        "root": merkle_root(leaves),
        "path": proof,
    }


def verify_inclusion(proof: dict[str, Any]) -> bool:
    value = proof["leaf_hash"]
    for step in proof["path"]:
        if step["side"] == "right":
            value = _parent(value, step["hash"])
        elif step["side"] == "left":
            value = _parent(step["hash"], value)
        else:
            return False
    return value == proof["root"]


class TransparencyLog:
    def __init__(self, entries: list[dict[str, Any]] | None = None) -> None:
        self.entries = entries or []

    @classmethod
    def read_json(cls, path: str | Path) -> "TransparencyLog":
        source = Path(path)
        if not source.exists():
            return cls()
        data = json.loads(source.read_text(encoding="utf-8"))
        return cls(entries=data.get("entries", []))

    def append(self, receipt: dict[str, Any]) -> dict[str, Any]:
        entry = {
            "index": len(self.entries),
            "receipt_hash": receipt["receipt_hash"],
            "payload_hash": hash_payload(receipt["payload"]),
            "receipt_envelope_hash": stable_hash(canonical_json(receipt)),
        }
        self.entries.append(entry)
        return entry

    def root(self) -> str:
        return merkle_root([entry["receipt_hash"] for entry in self.entries])

    def proof_for(self, receipt_hash: str) -> dict[str, Any]:
        leaves = [entry["receipt_hash"] for entry in self.entries]
        return inclusion_proof(leaves, leaves.index(receipt_hash))

    def to_dict(self) -> dict[str, Any]:
        return {
            "log_version": "rdllm-transparency-log/v1",
            "tree_size": len(self.entries),
            "root": self.root(),
            "entries": self.entries,
        }

    def write_json(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
