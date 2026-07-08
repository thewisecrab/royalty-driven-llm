"""Machine-readable creator license contracts for RDLLM source use."""

from __future__ import annotations

from typing import Any

from rdllm.models import Creator, Work
from rdllm.receipts import DEFAULT_ISSUER, canonical_json, hash_payload, now_iso, sign_payload
from rdllm.text import stable_hash

LICENSE_CONTRACT_VERSION = "rdllm-creator-license-contract/v1"
LICENSE_CONTRACT_SCHEMA = "docs/schemas/creator_license_contract.schema.json"


def _hashable_contract(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in contract.items()
        if key not in {"contract_hash", "signature"}
    }


def _creator_commitment(creator: Creator) -> dict[str, Any]:
    return {
        "creator_id": creator.creator_id,
        "creator_name": creator.name,
        "payout_account_hash": stable_hash(creator.payout_account),
        "payout_account_disclosed": False,
    }


def _odrl_policy(work: Work) -> dict[str, Any]:
    duties: list[dict[str, Any]] = []
    if work.requires_attribution:
        duties.append({"action": "attribute", "target": work.source_uri or work.work_id})
    if work.requires_royalty:
        duty: dict[str, Any] = {"action": "compensate"}
        if work.minimum_creator_pool_rate:
            duty["constraint"] = {
                "leftOperand": "rdllm:creatorPoolRate",
                "operator": "gteq",
                "rightOperand": work.minimum_creator_pool_rate,
            }
        duties.append(duty)
    duties.append({"action": "audit", "target": "rdllm:proofPack"})
    return {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "uid": work.policy_id or f"policy:{work.work_id}",
        "type": "Offer",
        "profile": "rdllm-creator-license-contract",
        "asset": work.source_uri or f"registered://works/{work.work_id}",
        "permission": [{"action": use} for use in sorted(work.allowed_uses)],
        "prohibition": [{"action": use} for use in sorted(work.prohibited_uses)],
        "duty": duties,
        "constraint": [
            {
                "leftOperand": "spatial",
                "operator": "isAnyOf",
                "rightOperand": list(work.jurisdictions),
            }
        ],
    }


def _work_terms(work: Work, creator: Creator) -> dict[str, Any]:
    content_hash = stable_hash(work.content)
    policy_id = work.policy_id or f"policy:{work.work_id}"
    terms = {
        "term_id": f"term:{work.work_id}:{policy_id}",
        "work_id": work.work_id,
        "creator_id": work.creator_id,
        "creator_name": creator.name,
        "title": work.title,
        "title_hash": stable_hash(work.title),
        "content_hash": content_hash,
        "source_uri": work.source_uri or f"registered://works/{work.work_id}",
        "license": work.license,
        "license_uri": work.license_uri,
        "policy_id": policy_id,
        "allowed_uses": sorted(work.allowed_uses),
        "prohibited_uses": sorted(work.prohibited_uses),
        "jurisdictions": sorted(work.jurisdictions),
        "requires_attribution": work.requires_attribution,
        "requires_royalty": work.requires_royalty,
        "minimum_creator_pool_rate": work.minimum_creator_pool_rate,
        "revoked": work.revoked,
        "revoked_at": work.revoked_at,
        "consent_status": "revoked" if work.revoked else "active",
        "payout_account_hash": stable_hash(creator.payout_account),
        "work_text_disclosed": False,
        "payout_account_disclosed": False,
        "duties": {
            "attribution_required": work.requires_attribution,
            "royalty_required": work.requires_royalty,
            "proof_pack_required": True,
            "audit_trail_required": True,
            "challenge_process_required": True,
            "revocation_must_affect_future_use": True,
        },
        "standards": {
            "odrl_policy": _odrl_policy(work),
            "croissant_usage_policy": {
                "allowedUses": sorted(work.allowed_uses),
                "prohibitedUses": sorted(work.prohibited_uses),
                "jurisdictions": sorted(work.jurisdictions),
                "license": work.license_uri or work.license,
                "copyrightHolder": work.creator_id,
            },
            "spdx_external_ref": {
                "name": work.title,
                "verifiedUsing": [{"algorithm": "SHA256", "hashValue": content_hash}],
                "intendedUse": sorted(work.allowed_uses),
            },
        },
    }
    terms["term_hash"] = hash_payload(terms)
    return terms


def _contract_terms(
    creators: dict[str, Creator],
    works: dict[str, Work],
) -> list[dict[str, Any]]:
    terms = []
    for work in sorted(works.values(), key=lambda item: item.work_id):
        creator = creators[work.creator_id]
        terms.append(_work_terms(work, creator))
    return terms


def make_creator_license_contract(
    *,
    creators: dict[str, Creator],
    works: dict[str, Work],
    issuer: str = DEFAULT_ISSUER,
    provider: str = "provider:unspecified",
    effective_at: str | None = None,
    created_at: str | None = None,
    signing_secret: str | None = None,
) -> dict[str, Any]:
    """Create a signed, hash-bound creator license contract for registered works."""

    terms = _contract_terms(creators, works)
    creator_commitments = [
        _creator_commitment(creator)
        for creator in sorted(creators.values(), key=lambda item: item.creator_id)
    ]
    active_terms = [term for term in terms if term["consent_status"] == "active"]
    revoked_terms = [term for term in terms if term["consent_status"] == "revoked"]
    contract = {
        "contract_version": LICENSE_CONTRACT_VERSION,
        "issuer": issuer,
        "created_at": created_at or now_iso(),
        "effective_at": effective_at or created_at or now_iso(),
        "provider": provider,
        "profile": {
            "profile_id": "rdllm-creator-license-contract-profile/v1",
            "rights_standard": "ODRL",
            "dataset_metadata_standard": "MLCommons Croissant",
            "bom_standard": "SPDX 3",
            "provenance_standard": "W3C PROV",
        },
        "creator_commitments": creator_commitments,
        "terms": terms,
        "commitments": {
            "creator_root": hash_payload(creator_commitments),
            "term_root": hash_payload(terms),
            "content_hash_root": hash_payload(
                [term["content_hash"] for term in terms]
            ),
            "policy_root": hash_payload(
                [
                    {
                        "work_id": term["work_id"],
                        "policy_id": term["policy_id"],
                        "allowed_uses": term["allowed_uses"],
                        "prohibited_uses": term["prohibited_uses"],
                        "jurisdictions": term["jurisdictions"],
                        "revoked": term["revoked"],
                        "minimum_creator_pool_rate": term[
                            "minimum_creator_pool_rate"
                        ],
                    }
                    for term in terms
                ]
            ),
        },
        "enforcement": {
            "license_terms_must_precede_use": True,
            "policy_engine_must_enforce_allowed_uses": True,
            "minimum_creator_pool_rate_must_be_met": True,
            "revoked_works_denied_for_future_use": True,
            "unlicensed_traced_use_routes_to_rights_conflict_escrow": True,
            "proof_pack_required_for_public_answers": True,
        },
        "schemas": {
            "creator_license_contract": LICENSE_CONTRACT_SCHEMA,
        },
        "summary": {
            "status": "ready",
            "target_certification_level": "RDLLM-L38",
            "creator_count": len(creators),
            "work_count": len(works),
            "term_count": len(terms),
            "active_term_count": len(active_terms),
            "revoked_term_count": len(revoked_terms),
            "minimum_creator_pool_rate_max": max(
                [term["minimum_creator_pool_rate"] for term in terms] or [0.0]
            ),
            "offline_verification_supported": True,
        },
        "privacy": {
            "work_text_disclosed": False,
            "payout_account_disclosed": False,
            "contract_uses_content_hashes": True,
            "contract_uses_payout_account_hashes": True,
        },
    }
    contract["contract_hash"] = hash_payload(_hashable_contract(contract))
    contract["signature"] = {
        "algorithm": "HMAC-SHA256" if signing_secret else "UNSIGNED",
        "issuer": issuer,
        "value": (
            sign_payload(_hashable_contract(contract), signing_secret)
            if signing_secret
            else ""
        ),
    }
    return contract


def validate_creator_license_contract_shape(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "contract_version",
        "issuer",
        "created_at",
        "effective_at",
        "provider",
        "profile",
        "creator_commitments",
        "terms",
        "commitments",
        "enforcement",
        "schemas",
        "summary",
        "privacy",
        "contract_hash",
        "signature",
    )
    for key in required:
        if key not in contract:
            errors.append(f"missing creator license contract field: {key}")
    if contract.get("contract_version") != LICENSE_CONTRACT_VERSION:
        errors.append("creator license contract version is unsupported")
    if "creator_license_contract" not in contract.get("schemas", {}):
        errors.append("missing creator license contract schema")
    for index, term in enumerate(contract.get("terms", [])):
        for key in (
            "term_id",
            "work_id",
            "creator_id",
            "content_hash",
            "policy_id",
            "allowed_uses",
            "prohibited_uses",
            "jurisdictions",
            "requires_attribution",
            "requires_royalty",
            "minimum_creator_pool_rate",
            "consent_status",
            "term_hash",
        ):
            if key not in term:
                errors.append(f"term {index} missing field: {key}")
    return errors


def verify_creator_license_contract_public(
    contract: dict[str, Any],
    *,
    signing_secret: str | None = None,
) -> list[str]:
    """Verify public hash/signature commitments without private source text."""

    errors = validate_creator_license_contract_shape(contract)
    if errors:
        return errors
    if hash_payload(_hashable_contract(contract)) != contract.get("contract_hash"):
        errors.append("creator license contract hash is not reproducible")

    creator_commitments = contract.get("creator_commitments", [])
    terms = contract.get("terms", [])
    commitments = contract.get("commitments", {})
    if commitments.get("creator_root") != hash_payload(creator_commitments):
        errors.append("creator license creator root is not reproducible")
    if commitments.get("term_root") != hash_payload(terms):
        errors.append("creator license term root is not reproducible")
    if commitments.get("content_hash_root") != hash_payload(
        [term.get("content_hash", "") for term in terms]
    ):
        errors.append("creator license content hash root is not reproducible")
    expected_policy_root = hash_payload(
        [
            {
                "work_id": term.get("work_id", ""),
                "policy_id": term.get("policy_id", ""),
                "allowed_uses": term.get("allowed_uses", []),
                "prohibited_uses": term.get("prohibited_uses", []),
                "jurisdictions": term.get("jurisdictions", []),
                "revoked": term.get("revoked", False),
                "minimum_creator_pool_rate": term.get("minimum_creator_pool_rate"),
            }
            for term in terms
        ]
    )
    if commitments.get("policy_root") != expected_policy_root:
        errors.append("creator license policy root is not reproducible")

    for term in terms:
        term_copy = dict(term)
        term_hash = term_copy.pop("term_hash", "")
        if hash_payload(term_copy) != term_hash:
            errors.append(
                f"creator license term hash is not reproducible: {term.get('work_id', '')}"
            )
        duties = term.get("duties", {})
        if term.get("requires_royalty") and duties.get("royalty_required") is not True:
            errors.append(
                f"creator license term missing royalty duty: {term.get('work_id', '')}"
            )
        if (
            term.get("requires_attribution")
            and duties.get("attribution_required") is not True
        ):
            errors.append(
                f"creator license term missing attribution duty: {term.get('work_id', '')}"
            )
        odrl_policy = canonical_json(term.get("standards", {}).get("odrl_policy", {}))
        if term.get("requires_royalty") and "compensate" not in odrl_policy:
            errors.append(
                f"creator license term missing compensate duty: {term.get('work_id', '')}"
            )
        if term.get("requires_attribution") and "attribute" not in odrl_policy:
            errors.append(
                f"creator license term missing attribution duty: {term.get('work_id', '')}"
            )
        if term.get("work_text_disclosed") is not False:
            errors.append(
                f"creator license term discloses work text: {term.get('work_id', '')}"
            )
        if term.get("payout_account_disclosed") is not False:
            errors.append(
                f"creator license term discloses payout account: {term.get('work_id', '')}"
            )

    enforcement = contract.get("enforcement", {})
    for key in (
        "license_terms_must_precede_use",
        "policy_engine_must_enforce_allowed_uses",
        "minimum_creator_pool_rate_must_be_met",
        "revoked_works_denied_for_future_use",
        "unlicensed_traced_use_routes_to_rights_conflict_escrow",
        "proof_pack_required_for_public_answers",
    ):
        if enforcement.get(key) is not True:
            errors.append(f"creator license enforcement missing: {key}")
    privacy = contract.get("privacy", {})
    if privacy.get("work_text_disclosed") is not False:
        errors.append("creator license contract discloses work text")
    if privacy.get("payout_account_disclosed") is not False:
        errors.append("creator license contract discloses payout accounts")
    if privacy.get("contract_uses_content_hashes") is not True:
        errors.append("creator license contract must use content hashes")
    if privacy.get("contract_uses_payout_account_hashes") is not True:
        errors.append("creator license contract must use payout account hashes")

    signature = contract.get("signature", {})
    if signing_secret:
        if signature.get("algorithm") != "HMAC-SHA256":
            errors.append("creator license contract is not HMAC signed")
        expected_signature = sign_payload(_hashable_contract(contract), signing_secret)
        if signature.get("value") != expected_signature:
            errors.append("creator license contract signature is invalid")
    return errors


def verify_creator_license_contract(
    contract: dict[str, Any],
    *,
    creators: dict[str, Creator],
    works: dict[str, Work],
    signing_secret: str | None = None,
) -> list[str]:
    """Verify a creator license contract against the private registered corpus."""

    errors = validate_creator_license_contract_shape(contract)
    if errors:
        return errors
    errors = verify_creator_license_contract_public(
        contract,
        signing_secret=signing_secret,
    )

    expected = make_creator_license_contract(
        creators=creators,
        works=works,
        issuer=contract.get("issuer", DEFAULT_ISSUER),
        provider=str(contract.get("provider", "provider:unspecified")),
        effective_at=contract.get("effective_at"),
        created_at=contract.get("created_at"),
        signing_secret=signing_secret,
    )
    comparable_fields = (
        "creator_commitments",
        "terms",
        "commitments",
        "enforcement",
        "summary",
        "privacy",
    )
    for key in comparable_fields:
        if contract.get(key) != expected.get(key):
            errors.append(f"creator license contract {key} does not match corpus")
    if contract.get("contract_hash") != expected.get("contract_hash"):
        errors.append("creator license contract hash does not match corpus")

    contract_text = canonical_json(contract)
    for work in works.values():
        if work.content and work.content in contract_text:
            errors.append(f"creator license contract discloses work text: {work.work_id}")
    for creator in creators.values():
        if creator.payout_account and creator.payout_account in contract_text:
            errors.append(
                f"creator license contract discloses payout account: {creator.creator_id}"
            )
    return errors
