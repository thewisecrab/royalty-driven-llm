"""Audit ledger for royalty-bearing generation events."""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from rdllm.models import UsageEvent


class RoyaltyLedger:
    def __init__(self) -> None:
        self.events: list[UsageEvent] = []

    def record(self, event: UsageEvent) -> None:
        self.events.append(event)

    def balances(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = defaultdict(Decimal)
        for event in self.events:
            for share in event.royalty_shares:
                totals[share.creator_id] += share.payout
        return dict(sorted(totals.items()))

    def to_dict(self) -> dict[str, object]:
        return {
            "events": [event.to_dict() for event in self.events],
            "balances": {key: str(value) for key, value in self.balances().items()},
        }

    def write_json(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
