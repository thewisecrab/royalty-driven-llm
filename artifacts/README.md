# Reference Artifacts

Everything in this directory is a deterministic **synthetic reference fixture**.
The files exist for tests, schema examples, documentation, and reproducible local
verification. They are not evidence that a real operator, model provider,
auditor, payment processor, creator, or deployment completed the represented
action.

In particular:

- `rdllm-local-demo` is a fixture issuer, not a trusted production authority.
- `HMAC-SHA256` signatures use a published demo secret and are not publicly
  verifiable production signatures.
- payment, remittance, settlement, and production-readiness artifacts simulate
  protocol states; they do not attest that money moved.
- URLs under `rdllm.local`, `registered://`, and `example.*` are test locators.

Production operators must create new artifacts from their own runtime. Public
receipts must use Ed25519 and publish the verification key. Deployment readiness
requires externally signed evidence whose key is present in an independently
managed RDLLM trust store. Direct settlement additionally requires a verified
payment-processor attestation.

Regenerate fixtures with:

```bash
PYTHONPATH=src python3 tools/regenerate_reference_artifacts.py
```

Never copy a fixture into a production trust store or represent a fixture status
as an external certification.
