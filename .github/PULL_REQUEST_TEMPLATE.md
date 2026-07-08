## Summary

- What changed:
- Why it is needed:
- RDLLM levels or public artifacts affected:

## Verification

- [ ] `PYTHONPATH=src python tools/ship_check.py`
- [ ] `PYTHONPATH=src python tools/public_surface_privacy_audit.py`
- [ ] New or changed JSON artifacts validate against schemas
- [ ] Hosted `docs/.well-known/rdllm*` exports are current and resolve artifact/schema paths
- [ ] New or changed documentation links resolve for static hosting
- [ ] Built package installs cleanly and the installed `rdllm` CLI still works
- [ ] Provider/source-footer/settlement gates still fail closed for negative cases
- [ ] README/docs updated for new commands, artifacts, or provider mappings
- [ ] References added for new research, standards, policy, or provider API claims

## Safety And Privacy

- [ ] Public artifacts do not expose prompts, source text, private reasoning, secrets, customer data, or payout account data
- [ ] Hosted public artifacts and schema mirrors pass the privacy audit
- [ ] Unknown provider states fail closed
- [ ] Creator settlement remains gated by attribution, rights, meter, and response-state proofs

## Provider Impact

- Provider families affected:
- Native API surfaces affected:
- Backward compatibility notes:
