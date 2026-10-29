"""Parsers for machine-readable licensing and opt-out signals.

The content-protocol layer used to copy pre-labelled ``allowed_uses`` fields.
This module reads the documents those labels are supposed to come from:

- RSL 1.0 XML (namespace ``https://rslstandard.org/rsl``, Recommendation 2025-12-10).
  ``<permits type="usage">`` and ``<prohibits type="usage">`` tokens, with
  prohibits winning on conflict. Payment ``type`` is copied when present.
- IETF draft-ietf-aipref-vocab-08 Content-Usage dictionaries:
  ``train-ai``, ``ai-use``, and ``search`` with token values ``y`` or ``n``.
  Unknown keys are ignored. A disallow wins over an allow when statements are merged.
- robots.txt records, W3C TDM Reservation (``tdm-reservation: 1``), and
  ``Content-Usage`` lines inside robots.txt.

The RDLLM use names below are an interpretation for the existing policy checker.
They are not a legal opinion and they do not fetch remote licenses.
"""

from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree

RSL_NAMESPACE = "https://rslstandard.org/rsl"
AIPREF_VOCAB = "draft-ietf-aipref-vocab-08"
AIPREF_CATEGORIES = ("train-ai", "ai-use", "search")

# Common AI crawler tokens. A Disallow of the whole site for one of these, or
# for User-agent: *, is recorded as a training opt-out. It is not a claim that
# every crawler on the internet was enumerated.
_AI_AGENTS = {
    "*",
    "gptbot",
    "google-extended",
    "ccbot",
    "claudebot",
    "anthropic-ai",
    "bytespider",
    "applebot-extended",
    "cohere-ai",
    "facebookbot",
    "meta-externalagent",
    "perplexitybot",
    "amazonbot",
    "diffbot",
}

_RSL_USE_MAP = {
    "all": "all",
    "ai-all": "ai_use",
    "ai-train": "training",
    "ai-input": "retrieval_inference",
    "ai-index": "retrieval",
    "search": "retrieval",
}
_AIPREF_USE_MAP = {
    "train-ai": "training",
    "ai-use": "retrieval_inference",
    "search": "retrieval",
}
_ROYALTY_PAYMENT_TYPES = {
    "royalty",
    "subscription",
    "purchase",
    "crawl",
    "inference",
    "contribution",
    "paid",
}
_USAGE_RE = re.compile(r"(?:^|[\s,]+)([A-Za-z0-9_-]+)")


def _empty_result(kind: str = "") -> dict[str, Any]:
    return {
        "recognized": False,
        "kind": kind,
        "protocol": "",
        "vocabulary": "",
        "allowed_uses": [],
        "prohibited_uses": [],
        "payment_type": "",
        "attribution_required": None,
        "royalty_required": None,
        "minimum_creator_pool_rate": None,
        "preferences": {},
        "opt_out_agents": [],
        "tdm_reservation": None,
        "notes": [],
    }


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _usage_tokens(text: str) -> list[str]:
    return [match.group(1).lower() for match in _USAGE_RE.finditer(text or "")]


def _map_rsl_uses(tokens: list[str]) -> list[str]:
    mapped: list[str] = []
    for token in tokens:
        name = _RSL_USE_MAP.get(token)
        if name and name not in mapped:
            mapped.append(name)
    return mapped


def parse_rsl(text: str) -> dict[str, Any]:
    """Parse an RSL 1.0 document or an RSL fragment embedded in RSS."""

    result = _empty_result("rsl")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        result["notes"].append(f"xml parse error: {exc}")
        return result
    licenses = [element for element in root.iter() if _local(element.tag) == "license"]
    if not licenses and _local(root.tag) != "rsl":
        result["notes"].append("no RSL license element")
        return result
    allowed: list[str] = []
    prohibited: list[str] = []
    payment_type = ""
    for license_element in licenses or ([root] if _local(root.tag) == "license" else []):
        for child in list(license_element):
            name = _local(child.tag)
            if name in {"permits", "prohibits"} and (child.attrib.get("type") or "usage") == "usage":
                mapped = _map_rsl_uses(_usage_tokens(child.text or ""))
                target = allowed if name == "permits" else prohibited
                for item in mapped:
                    if item not in target:
                        target.append(item)
            elif name == "payment" and not payment_type:
                payment_type = str(child.attrib.get("type", "")).strip().lower()
    for item in prohibited:
        if item in allowed:
            allowed.remove(item)
    if not allowed and not prohibited and not payment_type:
        result["notes"].append("RSL document had no usage or payment terms")
        return result
    result.update(
        {
            "recognized": True,
            "protocol": "rsl",
            "vocabulary": RSL_NAMESPACE,
            "allowed_uses": allowed,
            "prohibited_uses": prohibited,
            "payment_type": payment_type,
            "attribution_required": payment_type == "attribution" or None,
            "royalty_required": payment_type in _ROYALTY_PAYMENT_TYPES,
        }
    )
    return result


def parse_aipref_dictionary(text: str) -> dict[str, str]:
    """Parse one Content-Usage dictionary. Last occurrence of a key wins.

    Values other than the tokens ``y`` and ``n`` leave the category unknown.
    Parameters after ``;`` are ignored, matching draft-ietf-aipref-vocab-08 §6.
    """

    body = text.strip()
    if body.lower().startswith("content-usage:"):
        body = body.split(":", 1)[1].strip()
    preferences = {category: "unknown" for category in AIPREF_CATEGORIES}
    if not body:
        return preferences
    for part in body.split(","):
        item = part.strip()
        if not item:
            continue
        item = item.split(";", 1)[0].strip()
        if "=" not in item:
            continue
        key, value = (piece.strip() for piece in item.split("=", 1))
        if key not in preferences:
            continue
        token = value.strip()
        preferences[key] = token if token in {"y", "n"} else "unknown"
    return preferences


def _uses_from_preferences(preferences: dict[str, str]) -> tuple[list[str], list[str]]:
    allowed: list[str] = []
    prohibited: list[str] = []
    for category, preference in preferences.items():
        use = _AIPREF_USE_MAP.get(category)
        if not use or preference not in {"y", "n"}:
            continue
        target = allowed if preference == "y" else prohibited
        if use not in target:
            target.append(use)
    for item in prohibited:
        if item in allowed:
            allowed.remove(item)
    return allowed, prohibited


def parse_aipref(text: str) -> dict[str, Any]:
    """Parse a Content-Usage preference line or header value."""

    preferences = parse_aipref_dictionary(text)
    allowed, prohibited = _uses_from_preferences(preferences)
    result = _empty_result("aipref")
    if all(value == "unknown" for value in preferences.values()):
        result["preferences"] = preferences
        result["notes"].append("no explicit y/n preference")
        return result
    result.update(
        {
            "recognized": True,
            "protocol": "aipref",
            "vocabulary": AIPREF_VOCAB,
            "allowed_uses": allowed,
            "prohibited_uses": prohibited,
            "preferences": preferences,
        }
    )
    return result


def _merge_restrictive(base: dict[str, Any], extra_prohibited: list[str]) -> None:
    prohibited = list(base["prohibited_uses"])
    allowed = list(base["allowed_uses"])
    for item in extra_prohibited:
        if item not in prohibited:
            prohibited.append(item)
        if item in allowed:
            allowed.remove(item)
    base["prohibited_uses"] = prohibited
    base["allowed_uses"] = allowed


def parse_robots_and_tdm(text: str) -> dict[str, Any]:
    """Parse robots.txt groups, TDM reservation, and embedded Content-Usage."""

    result = _empty_result("robots_txt")
    result["protocol"] = "robots_txt"
    agents: list[str] = []
    current_agents: list[str] = []
    blocked_agents: list[str] = []
    preferences = {category: "unknown" for category in AIPREF_CATEGORIES}
    saw_directive = False
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        key = field.lower()
        if key == "user-agent":
            current_agents = [value.lower()]
            agents.extend(current_agents)
            saw_directive = True
            continue
        if key == "disallow":
            saw_directive = True
            path = value.strip()
            blocks_site = path == "/" or path == "/*"
            if blocks_site and any(agent in _AI_AGENTS for agent in current_agents):
                for agent in current_agents:
                    if agent not in blocked_agents:
                        blocked_agents.append(agent)
            continue
        if key == "tdm-reservation":
            saw_directive = True
            result["tdm_reservation"] = value.strip()
            if value.strip() == "1":
                _merge_restrictive(result, ["training"])
            continue
        if key == "content-usage":
            saw_directive = True
            parsed = parse_aipref_dictionary(value)
            for category, preference in parsed.items():
                if preference == "n":
                    preferences[category] = "n"
                elif preference == "y" and preferences[category] != "n":
                    preferences[category] = "y"
    allowed, prohibited = _uses_from_preferences(preferences)
    for item in allowed:
        if item not in result["allowed_uses"] and item not in result["prohibited_uses"]:
            result["allowed_uses"].append(item)
    _merge_restrictive(result, prohibited)
    if blocked_agents:
        _merge_restrictive(result, ["training"])
        result["opt_out_agents"] = blocked_agents
    result["preferences"] = preferences
    if saw_directive and (
        result["allowed_uses"]
        or result["prohibited_uses"]
        or result["tdm_reservation"] is not None
        or blocked_agents
    ):
        result["recognized"] = True
        result["vocabulary"] = "robots.txt + " + AIPREF_VOCAB
    else:
        result["notes"].append("no robots, TDM, or Content-Usage directive recognized")
    return result


def _looks_like_rsl(text: str) -> bool:
    lowered = text.lower()
    return "<rsl" in lowered or "rslstandard.org/rsl" in lowered or "<license" in lowered and "<permits" in lowered


def _looks_like_robots(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in ("user-agent:", "disallow:", "tdm-reservation:", "content-usage:")
    )


def parse_licensing_signal(text: str) -> dict[str, Any]:
    """Detect and parse one RSL, aipref, or robots/TDM document."""

    document = str(text or "").strip()
    if not document:
        result = _empty_result()
        result["notes"].append("empty document")
        return result
    if _looks_like_rsl(document):
        return parse_rsl(document)
    if _looks_like_robots(document):
        return parse_robots_and_tdm(document)
    if any(label in document for label in ("train-ai=", "ai-use=", "search=")):
        return parse_aipref(document)
    result = _empty_result()
    result["notes"].append("document was not RSL, aipref Content-Usage, or robots/TDM")
    return result
